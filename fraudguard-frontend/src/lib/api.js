import axios from 'axios'

// Central Axios instance, pointed at the real FraudGuard FastAPI backend.
// VITE_API_BASE_URL should include the /api/v1 prefix, e.g.
//   http://localhost:8000/api/v1
//
// Auth: this app authenticates via httpOnly cookies set by the backend on
// /auth/login and /auth/refresh (see backend app/core/cookies.py), NOT by
// storing a token in localStorage/JS. `withCredentials: true` is what
// makes the browser actually attach those cookies to cross-origin requests
// (the deployed frontend and backend are on different domains — Vercel and
// Render). There is deliberately no token-storage helper in this file
// anymore, and no Authorization header is ever set from the client side —
// the cookie does that job invisibly.
export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1',
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
  withCredentials: true,
})

// Reads the (deliberately non-httpOnly) csrf_token cookie the backend sets
// alongside the httpOnly auth cookies, so it can be echoed back as a
// header. This is the frontend half of the double-submit CSRF defense —
// see backend app/core/security.py:verify_csrf for the other half.
function getCsrfTokenFromCookie() {
  const match = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]+)/)
  return match ? decodeURIComponent(match[1]) : null
}

const MUTATING_METHODS = new Set(['post', 'put', 'patch', 'delete'])

api.interceptors.request.use((config) => {
  if (MUTATING_METHODS.has((config.method || '').toLowerCase())) {
    const csrfToken = getCsrfTokenFromCookie()
    if (csrfToken) config.headers['X-CSRF-Token'] = csrfToken
  }
  return config
})

// Queue concurrent 401s while a single refresh request is in flight, so we
// don't fire multiple /auth/refresh calls (which rotates/invalidates the
// refresh token) for one batch of parallel dashboard requests. Nothing here
// needs to carry a token value anymore — the refreshed cookies are set
// directly by the browser from the /auth/refresh response, and the request
// interceptor above re-reads the (now-rotated) csrf_token cookie fresh on
// every retried request.
let isRefreshing = false
let pendingQueue = []

function resolvePending(error) {
  pendingQueue.forEach(({ resolve, reject }) => (error ? reject(error) : resolve()))
  pendingQueue = []
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config
    const status = error.response?.status
    const isAuthEndpoint = originalRequest?.url?.includes('/auth/login') || originalRequest?.url?.includes('/auth/refresh')

    if (status !== 401 || isAuthEndpoint || originalRequest._retry) {
      return Promise.reject(error)
    }

    if (isRefreshing) {
      return new Promise((resolve, reject) => {
        pendingQueue.push({ resolve, reject })
      }).then(() => {
        originalRequest._retry = true
        return api(originalRequest)
      })
    }

    originalRequest._retry = true
    isRefreshing = true

    try {
      // No body needed — the refresh_token httpOnly cookie carries it, and
      // the CSRF header is attached automatically by the request interceptor.
      await api.post('/auth/refresh')
      resolvePending(null)
      return api(originalRequest)
    } catch (refreshError) {
      resolvePending(refreshError)
      window.location.href = '/login'
      return Promise.reject(refreshError)
    } finally {
      isRefreshing = false
    }
  }
)

// Backend error responses are shaped { success: false, error: { code, message, details } },
// NOT FastAPI's default { detail }. Every catch block across the app should
// use this instead of reaching into err.response.data.detail directly.
export function getApiErrorMessage(err, fallback = 'Something went wrong. Please try again.') {
  const message = err?.response?.data?.error?.message
  return typeof message === 'string' && message.length > 0 ? message : fallback
}

export const fraudApi = {
  // --- Auth ---------------------------------------------------------
  login: (payload) => api.post('/auth/login', payload),
  register: (payload) => api.post('/auth/register', payload),
  me: () => api.get('/auth/me'),
  updateProfile: (payload) => api.patch('/auth/me', payload),
  changePassword: (payload) => api.post('/auth/change-password', payload),
  getNotificationPreferences: () => api.get('/auth/notification-preferences'),
  updateNotificationPreferences: (preferences) => api.patch('/auth/notification-preferences', { preferences }),
  getMyStats: () => api.get('/auth/me/stats'),
  getMyActivity: () => api.get('/auth/me/activity'),
  // No body needed — the backend reads + clears the httpOnly cookies directly.
  logout: () => api.post('/auth/logout'),

  // --- User management (admin) -------------------------------------------
  listUsers: (params) => api.get('/users', { params }),
  createUser: (payload) => api.post('/users', payload),
  deactivateUser: (id) => api.patch(`/users/${id}/deactivate`),
  activateUser: (id) => api.patch(`/users/${id}/activate`),

  // --- Dashboard ------------------------------------------------------
  getDashboardStats: () => api.get('/dashboard/stats'),
  getDashboardCharts: () => api.get('/dashboard/charts'),
  getDashboardAlerts: (limit = 5) => api.get('/dashboard/alerts', { params: { limit } }),
  getAnalytics: () => api.get('/analytics'),
  getExplainability: () => api.get('/explainability'),

  // --- Transactions ---------------------------------------------------
  getTransactions: (params) => api.get('/transactions', { params }),
  getTransaction: (id) => api.get(`/transactions/${id}`),

  // --- Prediction -------------------------------------------------------
  predict: (payload) => api.post('/predict', payload),

  // --- Reports ----------------------------------------------------------
  // responseType: 'blob' is essential here — these responses are binary
  // (PDF) / raw text-as-file (CSV), not JSON, so Axios must not try to
  // JSON.parse() the body.
  exportSummaryPdf: (params) => api.get('/reports/summary.pdf', { params, responseType: 'blob' }),
  exportTransactionsCsv: (params) => api.get('/reports/transactions.csv', { params, responseType: 'blob' }),

  // --- Manual review queue ----------------------------------------------
  claimReview: (reviewId) => api.post(`/review-queue/${reviewId}/claim`),
  resolveReview: (reviewId, payload) => api.post(`/review-queue/${reviewId}/resolve`, payload),

  // --- Notifications ------------------------------------------------------
  listNotifications: (params) => api.get('/notifications', { params }),
  markNotificationRead: (id) => api.patch(`/notifications/${id}/read`),
  markAllNotificationsRead: () => api.patch('/notifications/read-all'),
}

// Derives the WebSocket URL for the live notifications channel from the
// same VITE_API_BASE_URL used for regular REST calls, so there's only one
// place (the .env file) that needs to know the backend's real address —
// http://… becomes ws://…, https://… becomes wss://… (required: browsers
// refuse a plain ws:// connection from an https:// page).
//
// No token is passed here anymore — the access_token httpOnly cookie is
// attached automatically by the browser during the WebSocket handshake
// (it's still just an HTTP GET under the hood), exactly like any other
// cookie-authenticated request. See backend app/api/v1/ws.py.
export function getNotificationsWebSocketUrl() {
  const httpBase = api.defaults.baseURL
  const wsBase = httpBase.replace(/^http/, 'ws')
  return `${wsBase}/ws/notifications`
}
