import axios from 'axios'

// Central Axios instance, now pointed at the real FraudGuard FastAPI backend.
// VITE_API_BASE_URL should include the /api/v1 prefix, e.g.
//   http://localhost:8000/api/v1
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

    const refreshToken = getRefreshToken()
    if (!refreshToken) {
      clearTokens()
      return Promise.reject(error)
    }

    if (isRefreshing) {
      return new Promise((resolve, reject) => {
        pendingQueue.push({ resolve, reject })
      }).then((token) => {
        originalRequest.headers.Authorization = `Bearer ${token}`
        originalRequest._retry = true
        return api(originalRequest)
      })
    }

    originalRequest._retry = true
    isRefreshing = true

    try {
      const { data } = await axios.post(
        `${api.defaults.baseURL}/auth/refresh`,
        { refresh_token: refreshToken }
      )
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

export const fraudApi = {
  // --- Auth ---------------------------------------------------------
  login: (payload) => api.post('/auth/login', payload),
  register: (payload) => api.post('/auth/register', payload),
  me: () => api.get('/auth/me'),
  logout: (refresh_token) => api.post('/auth/logout', refresh_token ? { refresh_token } : {}),

  // --- Dashboard ------------------------------------------------------
  getDashboardStats: () => api.get('/dashboard/stats'),
  getDashboardCharts: () => api.get('/dashboard/charts'),
  getDashboardAlerts: (limit = 5) => api.get('/dashboard/alerts', { params: { limit } }),

  // --- Transactions ---------------------------------------------------
  getTransactions: (params) => api.get('/transactions', { params }),
  getTransaction: (id) => api.get(`/transactions/${id}`),

  // --- Prediction -------------------------------------------------------
  predict: (payload) => api.post('/predict', payload),

  // --- Reports ----------------------------------------------------------
  // responseType: 'blob' is essential here — these responses are binary
  // (PDF) / raw text-as-file (CSV), not JSON, so Axios must not try to
  // JSON.parse() the body.
  exportSummaryPdf: () => api.get('/reports/summary.pdf', { responseType: 'blob' }),
  exportTransactionsCsv: (params) => api.get('/reports/transactions.csv', { params, responseType: 'blob' }),
}
