import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import useAuthStore from '../store/authstore'
import api from '../api'

export default function AdminLogin() {
  const [form, setForm] = useState({ username:'', password:'' })
  const [err,  setErr]  = useState('')
  const [loading, setLoading] = useState(false)
  const { login } = useAuthStore()
  const nav = useNavigate()

  const handleSubmit = async () => {
    setErr(''); setLoading(true)
    try {
      const body = new URLSearchParams({ username: form.username, password: form.password })
      const { data } = await api.post('/api/auth/login', body, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
      })
      login(data.access_token, data.admin_name)
      nav('/admin/dashboard')
    } catch {
      setErr('Incorrect username or password.')
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
      </div>
    </div>
  )
}
