import axios from 'axios'
import useAuthStore from './store/authstore'
import { parseApiError } from './utils/apiError'

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 120000, // face scan on server can take up to 2 min on first run
})

api.interceptors.request.use(config => {
  const token = localStorage.getItem('admin_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  // Let the browser set multipart boundary for FormData uploads.
  if (config.data instanceof FormData) {
    delete config.headers['Content-Type']
  }
  return config
})

api.interceptors.response.use(
  res => res,
  err => {
    const status = err.response?.status
    const url = err.config?.url || ''
    const detail = parseApiError(err, '')

    // Face check-in/out errors must NOT trigger logout (they also used to return 401).
    if (url.includes('/api/attendance/')) {
      return Promise.reject(err)
    }

    // Only treat auth failures as session expiry — not face/validation errors.
    if (status === 401 && !url.includes('/api/auth/login')) {
      const isSession =
        detail.toLowerCase().includes('session') ||
        detail.toLowerCase().includes('log in') ||
        detail.toLowerCase().includes('credentials')
      if (isSession) {
        useAuthStore.getState().logout()
        if (!window.location.pathname.includes('/admin/login')) {
          window.location.href = '/admin/login?expired=1'
        }
      }
    }
    return Promise.reject(err)
  }
)

export { parseApiError }
export default api
