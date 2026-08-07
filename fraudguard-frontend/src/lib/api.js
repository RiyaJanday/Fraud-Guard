import axios from 'axios'

// Central Axios instance, pointed at the real FraudGuard FastAPI backend.
// VITE_API_BASE_URL should include the /api/v1 prefix, e.g.
//   http://localhost:8000/api/v1
//
// Auth: Bearer token in localStorage + Authorization header. An httpOnly-
// cookie based approach was tried and reverted — cross-site (Vercel <->
// Render, different registrable domains) cookies get silently dropped by
// Chrome's third-party-cookie blocking regardless of correct SameSite=None;
// Secure config, which breaks login in a way that's invisible in the
// network tab response itself. localStorage + header is less defensible
// against XSS in theory, but it's the option that actually works reliably
// across browsers for a split-domain deployment like this one without a
// same-origin proxy in front of the API.
export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1',
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
})

const ACCESS_TOKEN_KEY = 'fraudguard_access_token'
const REFRESH_TOKEN_KEY = 'fraudguard_refresh_token'

export function getAccessToken() {
  return localStorage.getItem(ACCESS_TOKEN_KEY)
}

export function getRefreshToken() {
  return localStorage.getItem(REFRESH_TOKEN_KEY)
}

export function setTokens({ access_token, refresh_token }) {
  if (access_token) localStorage.setItem(ACCESS_TOKEN_KEY, access_token)
  if (refresh_token) localStorage.setItem(REFRESH_TOKEN_KEY, refresh_token)
}

export function clearTokens() {
  localStorage.removeItem(ACCESS_TOKEN_KEY)
  localStorage.removeItem(REFRESH_TOKEN_KEY)
}

api.interceptors.request.use((config) => {
  const token = getAccessToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Queue concurrent 401s while a single refresh request is in flight, so we
// don't fire multiple /auth/refresh calls (which rotates/invalidates the
// refresh token) for one batch of parallel dashboard requests.
let isRefreshing = false
let pendingQueue = []

function resolvePending(error, token) {
  pendingQueue.forEach(({ resolve, reject }) => (error ? reject(error) : resolve(token)))
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
      }).then((token) => {
        originalRequest._retry = true
        originalRequest.headers.Authorization = `Bearer ${token}`
        return api(originalRequest)
      })
    }

    originalRequest._retry = true
    isRefreshing = true
    const refreshToken = getRefreshToken()

    if (!refreshToken) {
      clearTokens()
      window.location.href = '/login'
      return Promise.reject(error)
    }

    try {
      const { data } = await api.post('/auth/refresh', { refresh_token: refreshToken })
      setTokens(data)
      resolvePending(null, data.access_token)
      originalRequest.headers.Authorization = `Bearer ${data.access_token}`
      return api(originalRequest)
    } catch (refreshError) {
      resolvePending(refreshError, null)
      clearTokens()
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
  logout: (refreshToken) => api.post('/auth/logout', refreshToken ? { refresh_token: refreshToken } : {}),

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
// refuse a plain ws:// connection from an https:// page). The access token
// is passed as a query param since the browser WebSocket API can't attach
// custom headers, and (per the cookie revert above) there's no cookie for
// the backend to read instead. See backend app/api/v1/ws.py.
export function getNotificationsWebSocketUrl(token) {
  const httpBase = api.defaults.baseURL
  const wsBase = httpBase.replace(/^http/, 'ws')
  return `${wsBase}/ws/notifications?token=${encodeURIComponent(token)}`
}
