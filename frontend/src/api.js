import axios from 'axios'
import useAuthStore from './store/authstore'

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({ baseURL: BASE_URL })

api.interceptors.request.use(config => {
  const token = localStorage.getItem('admin_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Old/invalid token → clear session and send user back to login.
api.interceptors.response.use(
  res => res,
  err => {
    if (err.response?.status === 401 && !err.config?.url?.includes('/api/auth/login')) {
      useAuthStore.getState().logout()
      if (!window.location.pathname.includes('/admin/login')) {
        window.location.href = '/admin/login?expired=1'
      }
    }
    return Promise.reject(err)
  }
)

export default api
