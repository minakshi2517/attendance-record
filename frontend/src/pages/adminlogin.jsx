import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import useAuthStore from '../store/authstore'
import api from '../api'

const s = {
  page:  { maxWidth:400, margin:'80px auto', padding:32, background:'#1e293b', borderRadius:16 },
  title: { fontSize:24, fontWeight:700, marginBottom:24, color:'#818cf8' },
  btn:   { background:'#6366f1', color:'#fff', width:'100%', padding:14, fontSize:16, marginTop:8 },
  err:   { color:'#ef4444', marginTop:12, fontSize:14 },
}

export default function AdminLogin() {
  const [form, setForm] = useState({ username:'', password:'' })
  const [err,  setErr]  = useState('')
  const { login } = useAuthStore()
  const nav = useNavigate()

  const handleSubmit = async () => {
    setErr('')
    try {
      // OAuth2 form format chahiye FastAPI ko
      const body = new URLSearchParams({ username: form.username, password: form.password })
      const { data } = await api.post('/api/auth/login', body, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
      })
      login(data.access_token, data.admin_name)
      nav('/admin/dashboard')
    } catch {
      setErr('Wrong username ya password')
    }
  }

  return (
    <div style={s.page}>
      <h2 style={s.title}>🔐 Admin Login</h2>
      <input placeholder="Username" value={form.username}
        onChange={e => setForm({...form, username: e.target.value})} />
      <input placeholder="Password" type="password" value={form.password}
        onChange={e => setForm({...form, password: e.target.value})}
        onKeyDown={e => e.key === 'Enter' && handleSubmit()} />
      <button style={s.btn} onClick={handleSubmit}>Login</button>
      {err && <div style={s.err}>{err}</div>}
    </div>
  )
}
