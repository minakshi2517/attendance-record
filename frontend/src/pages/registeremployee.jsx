import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Camera from '../components/camera'
import api from '../api'

const s = {
  page:  { maxWidth:560, margin:'40px auto', padding:24, background:'#1e293b', borderRadius:16 },
  title: { fontSize:22, fontWeight:700, color:'#818cf8', marginBottom:20 },
  btn:   { background:'#10b981', color:'#fff', width:'100%', padding:14, fontSize:15, marginTop:8 },
  msg:   { marginTop:16, padding:14, borderRadius:8, textAlign:'center' },
}

export default function RegisterEmployee() {
  const [form, setForm] = useState({ name:'', employee_id:'', department:'' })
  const [image,   setImage]   = useState(null)
  const [loading, setLoading] = useState(false)
  const [msg,     setMsg]     = useState(null)
  const nav = useNavigate()

  const handleRegister = async () => {
    if (!form.name.trim() || !form.employee_id.trim()) { alert('Name and Employee ID are required.'); return }
    if (!image) { alert('Please capture a photo first.'); return }
    setLoading(true); setMsg(null)
    try {
      const { data } = await api.post('/api/employees/register', {
        name: form.name.trim(),
        employee_id: form.employee_id.trim(),
        department: form.department.trim(),
        face_image: image,
      })
      setMsg({ ok:true, text:`${data.message} - ${data.name} added.` })
      setTimeout(() => nav('/admin/dashboard'), 1500)
    } catch (err) {
      setMsg({ ok:false, text: err.response?.data?.detail || 'Registration failed.' })
    } finally { setLoading(false) }
  }

  return (
    <div style={s.page}>
      <h2 style={s.title}>Register New Employee</h2>
      <input placeholder="Full Name *"   value={form.name}        onChange={e => setForm({...form, name:e.target.value})} />
      <input placeholder="Employee ID *" value={form.employee_id} onChange={e => setForm({...form, employee_id:e.target.value})} />
      <input placeholder="Department"    value={form.department}  onChange={e => setForm({...form, department:e.target.value})} />
      <p style={{color:'#64748b', marginBottom:12, fontSize:13}}>Capture the employee's photo (face the camera directly).</p>
      <Camera onCapture={setImage} />
      <button style={s.btn} onClick={handleRegister} disabled={loading}>
        {loading ? 'Registering...' : 'Register Employee'}
      </button>
      {msg && <div style={{...s.msg, background: msg.ok ? '#064e3b' : '#450a0a', color: msg.ok ? '#10b981' : '#ef4444'}}>{msg.text}</div>}
    </div>
  )
}
