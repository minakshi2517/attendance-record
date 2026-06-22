import React, { useState, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import useAuthStore from '../store/authstore'
import api from '../api'

export default function AdminLogin() {
  const [form, setForm] = useState({ username:'admin', password:'' })
  const [err,  setErr]  = useState('')
  const [loading, setLoading] = useState(false)
  const { login, logout } = useAuthStore()
  const nav = useNavigate()
  const [params] = useSearchParams()

  useEffect(() => {
    logout()
    if (params.get('expired') === '1') {
      setErr('Your session expired (server was updated). Please log in again.')
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const handleSubmit = async () => {
    setErr(''); setLoading(true)
    try {
      const body = new URLSearchParams({ username: form.username, password: form.password })
      const { data } = await api.post('/api/auth/login', body, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
      })
      login(data.access_token, data.admin_name)
      nav('/admin/dashboard')
    } catch (e) {
      setErr(e.response?.data?.detail || 'Incorrect username or password.')
    } finally { setLoading(false) }
  }

  return (
    <div className="page" style={{maxWidth:400, marginTop:40}}>
      <div className="register-card">
        <h2 className="page-title" style={{fontSize:22, marginBottom:20}}>Admin Login</h2>
        <label className="field-label">Username</label>
        <input placeholder="Username" value={form.username}
          onChange={e => setForm({...form, username: e.target.value})} />
        <label className="field-label">Password</label>
        <input placeholder="Password" type="password" value={form.password}
          onChange={e => setForm({...form, password: e.target.value})}
          onKeyDown={e => e.key === 'Enter' && handleSubmit()} />
        <button className="btn-primary" style={{width:'100%', padding:14, marginTop:4}} onClick={handleSubmit} disabled={loading}>
          {loading ? 'Signing in...' : 'Login'}
        </button>
        {err && <div className="alert alert-error" style={{marginTop:12}}>{err}</div>}
        <p style={{color:'#64748b', fontSize:12, marginTop:12, textAlign:'center'}}>
          Default: admin / admin123
        </p>
      </div>
    </div>
  )
}
