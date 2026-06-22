import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import useCamera from '../hooks/usecamera'
import api, { parseApiError } from '../api'

export default function RegisterEmployee() {
  const { videoRef, ready, error, start, captureBlob } = useCamera()
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
    setStatus('Scan 1 of 2 — look straight at the camera...')
    try {
      const blob1 = await captureBlob()
      if (!blob1) {
        setMsg({ ok:false, text:'Could not capture face. Please try again.' }); return
      }
      setStatus('Scan 2 of 2 — hold still...')
      await new Promise(r => setTimeout(r, 800))
      const blob2 = await captureBlob()

      setStatus('Saving face geometry — please wait 30-90 sec, do not close...')
      const body = new FormData()
      body.append('name', form.name.trim())
      body.append('employee_id', form.employee_id.trim())
      if (form.department.trim()) body.append('department', form.department.trim())
      body.append('face_image', blob1, 'face1.jpg')
      if (blob2) body.append('face_image_2', blob2, 'face2.jpg')

      const { data } = await api.post('/api/employees/register', body)
      setMsg({ ok:true, text:`${data.name} registered successfully!` })
      setTimeout(() => nav('/admin/dashboard'), 1200)
    } catch (err) {
      if (err.code === 'ECONNABORTED') {
        setMsg({ ok:false, text:'Server took too long. Please try again — first scan is always slowest.' })
      } else if (!err.response) {
        setMsg({ ok:false, text:'Network error. Check your internet and try again.' })
      } else {
        setMsg({ ok:false, text: parseApiError(err, 'Registration failed. Please try again.') })
      }
    } finally {
      setLoading(false)
      setStatus('')
    }
  }

  return (
    <div className="page">
      {loading && (
        <div style={{
          position:'fixed', inset:0, background:'rgba(15,23,42,0.92)',
          display:'flex', flexDirection:'column', alignItems:'center',
          justifyContent:'center', zIndex:300, padding:24, textAlign:'center',
        }}>
          <div style={{fontSize:40, marginBottom:16}}>⏳</div>
          <p style={{color:'#e2e8f0', fontSize:16, fontWeight:600, marginBottom:8}}>{status}</p>
          <p style={{color:'#64748b', fontSize:13}}>
            Like phone face unlock — only your facial points are saved, not the photo.
            First scan may take up to 90 seconds.
          </p>
        </div>
      )}

      <div className="register-card">
        <h2 className="page-title" style={{fontSize:20, marginBottom:8}}>Register Employee</h2>
        <p style={{color:'#64748b', fontSize:13, marginBottom:16}}>
          Fill details, face the camera, tap Register. Two quick scans build a stronger face profile.
        </p>

        <label className="field-label">Full Name *</label>
        <input placeholder="Full Name" value={form.name} onChange={e => setForm({...form, name:e.target.value})} disabled={loading} />
        <label className="field-label">Employee ID *</label>
        <input placeholder="Employee ID" value={form.employee_id} onChange={e => setForm({...form, employee_id:e.target.value})} disabled={loading} />
        <label className="field-label">Department</label>
        <input placeholder="Department" value={form.department} onChange={e => setForm({...form, department:e.target.value})} disabled={loading} />

        <div className={`camera-wrap ${loading ? 'scanning' : ''}`} style={{marginTop:12}}>
          <video ref={videoRef} className="camera-video" muted playsInline autoPlay />
        </div>

        <p className="camera-status">
          {error ? <span style={{color:'#ef4444'}}>{error}</span>
            : ready ? 'Camera ready — one person only, good light, hold still on Register'
            : 'Starting camera...'}
        </p>

        <button
          className="btn-success"
          style={{width:'100%', padding:16, marginTop:8, fontSize:16}}
          onClick={handleRegister}
          disabled={loading || !ready}
        >
          Register Employee
        </button>

        {msg && <div className={`alert ${msg.ok ? 'alert-success' : 'alert-error'}`} style={{marginTop:14}}>{msg.text}</div>}
      </div>
    </div>
  )
}
