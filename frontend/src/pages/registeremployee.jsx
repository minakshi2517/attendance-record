import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import useCamera from '../hooks/usecamera'
import api from '../api'

const HINTS = ['Look straight at the camera', 'Turn slightly LEFT', 'Turn slightly RIGHT']

export default function RegisterEmployee() {
  const { videoRef, ready, error, start, capture } = useCamera()
  const [form, setForm]       = useState({ name:'', employee_id:'', department:'' })
  const [samples, setSamples] = useState([])
  const [loading, setLoading] = useState(false)
  const [msg,     setMsg]     = useState(null)
  const nav = useNavigate()

  useEffect(() => { start() }, [start])

  const grab = () => {
    if (!ready) return
    const img = capture()
    if (img) setSamples(prev => prev.length < 3 ? [...prev, img] : prev)
  }

  const handleRegister = async () => {
    if (!form.name.trim() || !form.employee_id.trim()) {
      setMsg({ ok:false, text:'Name and Employee ID are required.' }); return
    }
    if (samples.length === 0) {
      setMsg({ ok:false, text:'Capture at least one face sample first.' }); return
    }
    setLoading(true); setMsg(null)
    try {
      const { data } = await api.post('/api/employees/register', {
        name: form.name.trim(),
        employee_id: form.employee_id.trim(),
        department: form.department.trim(),
        face_images: samples,
      })
      setMsg({ ok:true, text:`${data.name} registered successfully.` })
      setTimeout(() => nav('/admin/dashboard'), 1500)
    } catch (err) {
      setMsg({ ok:false, text: err.response?.data?.detail || 'Registration failed.' })
    } finally { setLoading(false) }
  }

  return (
    <div className="page">
      <div className="register-card">
        <h2 className="page-title" style={{fontSize:20, marginBottom:16}}>Register Employee</h2>

        <label className="field-label">Full Name *</label>
        <input placeholder="Full Name" value={form.name} onChange={e => setForm({...form, name:e.target.value})} />
        <label className="field-label">Employee ID *</label>
        <input placeholder="Employee ID" value={form.employee_id} onChange={e => setForm({...form, employee_id:e.target.value})} />
        <label className="field-label">Department</label>
        <input placeholder="Department" value={form.department} onChange={e => setForm({...form, department:e.target.value})} />

        <div className="camera-wrap" style={{marginTop:8}}>
          <video ref={videoRef} className="camera-video" muted playsInline autoPlay />
        </div>

        <p className="camera-status">
          {error ? <span style={{color:'#ef4444'}}>{error}</span>
            : HINTS[samples.length] || '3 samples captured — ready to register!'}
        </p>

        <div style={{display:'flex', gap:8, justifyContent:'center', margin:'10px 0'}}>
          {[0,1,2].map(i => (
            samples[i]
              ? <img key={i} src={samples[i]} alt="" style={{width:56,height:56,borderRadius:8,objectFit:'cover',border:'2px solid #10b981',transform:'scaleX(-1)'}} />
              : <div key={i} style={{width:56,height:56,borderRadius:8,border:'2px dashed #334155',display:'flex',alignItems:'center',justifyContent:'center',color:'#475569',fontSize:13}}>{i+1}</div>
          ))}
        </div>

        <button className="btn-primary" style={{width:'100%', padding:13}} onClick={grab} disabled={!ready || samples.length >= 3}>
          Capture Sample ({samples.length}/3)
        </button>
        <p style={{color:'#64748b', fontSize:12, textAlign:'center', margin:'8px 0'}}>
          3 samples (front, left, right) give the best recognition accuracy.
        </p>

        <button className="btn-success" style={{width:'100%', padding:14, marginTop:4}} onClick={handleRegister} disabled={loading || samples.length === 0}>
          {loading ? 'Registering...' : 'Register Employee'}
        </button>
        {samples.length > 0 &&
          <button className="btn-secondary" style={{width:'100%', padding:11, marginTop:8, fontSize:13}} onClick={() => setSamples([])} disabled={loading}>
            Clear Samples
          </button>}

        {msg && <div className={`alert ${msg.ok ? 'alert-success' : 'alert-error'}`} style={{marginTop:14}}>{msg.text}</div>}
      </div>
    </div>
  )
}
