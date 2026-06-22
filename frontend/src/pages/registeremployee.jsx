import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import useCamera from '../hooks/usecamera'
import api from '../api'

export default function RegisterEmployee() {
  const { videoRef, ready, error, start, capture } = useCamera()
  const [form, setForm]       = useState({ name:'', employee_id:'', department:'' })
  const [loading, setLoading] = useState(false)
  const [status,  setStatus]  = useState('')
  const [msg,     setMsg]     = useState(null)
  const nav = useNavigate()

  useEffect(() => { start() }, [start])

  const handleRegister = async () => {
    if (!form.name.trim() || !form.employee_id.trim()) {
      setMsg({ ok:false, text:'Name and Employee ID are required.' }); return
    }
    if (!ready) {
      setMsg({ ok:false, text:'Camera is still starting. Please wait a moment.' }); return
    }

    setLoading(true); setMsg(null)
    setStatus('Capturing face...')
    try {
      const image = capture()
      if (!image) {
        setMsg({ ok:false, text:'Could not capture photo. Please try again.' }); return
      }

      setStatus('Scanning facial features...')
      const { data } = await api.post('/api/employees/register', {
        name: form.name.trim(),
        employee_id: form.employee_id.trim(),
        department: form.department.trim(),
        face_image: image,
      })
      setMsg({ ok:true, text:`${data.name} registered successfully.` })
      setTimeout(() => nav('/admin/dashboard'), 1500)
    } catch (err) {
      setMsg({ ok:false, text: err.response?.data?.detail || 'Registration failed. Please try again.' })
    } finally {
      setLoading(false); setStatus('')
    }
  }

  return (
    <div className="page">
      <div className="register-card">
        <h2 className="page-title" style={{fontSize:20, marginBottom:8}}>Register Employee</h2>
        <p style={{color:'#64748b', fontSize:13, marginBottom:16}}>
          Fill in the details, then tap Register. The system will capture the face
          and store its unique facial geometry automatically.
        </p>

        <label className="field-label">Full Name *</label>
        <input placeholder="Full Name" value={form.name} onChange={e => setForm({...form, name:e.target.value})} />
        <label className="field-label">Employee ID *</label>
        <input placeholder="Employee ID" value={form.employee_id} onChange={e => setForm({...form, employee_id:e.target.value})} />
        <label className="field-label">Department</label>
        <input placeholder="Department" value={form.department} onChange={e => setForm({...form, department:e.target.value})} />

        <div className={`camera-wrap ${loading ? 'scanning' : ''}`} style={{marginTop:12}}>
          <video ref={videoRef} className="camera-video" muted playsInline autoPlay />
        </div>

        <p className="camera-status">
          {loading ? status
            : error ? <span style={{color:'#ef4444'}}>{error}</span>
            : ready ? 'Camera ready — face the camera and tap Register'
            : 'Starting camera...'}
        </p>

        <button
          className="btn-success"
          style={{width:'100%', padding:16, marginTop:8, fontSize:16}}
          onClick={handleRegister}
          disabled={loading || !ready}
        >
          {loading ? status || 'Registering...' : 'Register Employee'}
        </button>

        {msg && <div className={`alert ${msg.ok ? 'alert-success' : 'alert-error'}`} style={{marginTop:14}}>{msg.text}</div>}
      </div>
    </div>
  )
}
