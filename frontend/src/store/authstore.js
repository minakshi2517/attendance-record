import { create } from 'zustand'

const useAuthStore = create((set) => ({
  token:     localStorage.getItem('admin_token') || null,
  adminName: localStorage.getItem('admin_name')  || null,

  login: (token, name) => {
    localStorage.setItem('admin_token', token)
    localStorage.setItem('admin_name',  name)
    set({ token, adminName: name })
  },

  logout: () => {
    localStorage.removeItem('admin_token')
    localStorage.removeItem('admin_name')
    set({ token: null, adminName: null })
  },
}))

export default useAuthStore