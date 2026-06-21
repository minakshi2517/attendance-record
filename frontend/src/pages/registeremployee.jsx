import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import useCamera from '../hooks/usecamera'
import api from '../api'

const SAMPLE_STEPS = [
  'Look straight at the camera',
  'Turn your head slightly LEFT',
  'Turn your head slightly RIGHT',
]

const s = {
  page:  { maxWidth:560, margin:'40px auto', padding:'24px 16px' },
  card:  { background:'#1e293b', borderRadius:16, padding:24 },
  title: { fontSize:22, fontWeight:700, color:'#818cf8', marginBottom:20 },
  videoWrap: { width:'100%', maxWidth:360, margin:'8px auto 0' },
  video: { width:'100%', borderRadius:14, border:'2px solid #6366f1', background:'#000', transform:'scaleX(-1)', aspectRatio:'4 / 3', objectFit:'cover' },
  step:  { textAlign:'center', color:'#e2e8f0', fontSize:15, margin:'12px 0', fontWeight:600 },
  thumbs:{ display:'flex', gap:8, justifyContent:'center', margin:'12px 0' },
  thumb: { width:56, height:56, borderRadius:8, objectFit:'cover', border:'2px solid #10b981', transform:'scaleX(-1)' },
  slot:  { width:56, height:56, borderRadius:8, border:'2px dashed #334155', display:'flex', alignItems:'center', justifyContent:'center', color:'#475569', fontSize:12 },
  capBtn:{ background:'#6366f1', color:'#fff', width:'100%', padding:13, marginTop:6 },
  btn:   { background:'#10b981', color:'#fff', width:'100%', padding:14, fontSize:15, marginTop:10 },
  reset: { background:'#334155', color:'#fff', width:'100%', padding:11, marginTop:8, fontSize:13 },
  msg:   { marginTop:16, padding:14, borderRadius:8, textAlign:'center' },
  hint:  { color:'#64748b', fontSize:13, textAlign:'center', marginTop:6 },
}

export default function RegisterEmployee() {
  const { videoRef, ready, error, start, capture } = useCamera()
  const [form, setForm]       = useState({ name:'', employee_id:'', department:'' })
  const [samples, setSamples] = useState([])
  const [loading, setLoading] = useState(false)
  const [msg,     setMsg]     = useState(null)
  const nav = useNavigate()

  useEffect(() => { start() }, [start])

  const grab = () => {
    if (!ready) { setMsg({ ok:false, text:'Camera is still starting. Please wait.' }); return }
    const img = capture()
    if (img) setSamples(prev => [...prev, img])
  }

  const handleRegister = async () => {
    if (!form.name.trim() || !form.employee_id.trim()) { setMsg({ ok:false, text:'Name and Employee ID are required.' }); return }
    if (samples.length === 0) { setMsg({ ok:false, text:'Please capture at least one face sample.' }); return }
    setLoading(true); setMsg(null)
    try {
      const { data } = await api.post('/api/employees/register', {
        name: form.name.trim(),
        employee_id: form.employee_id.trim(),
        department: form.department.trim(),
        face_images: samples,
      })
      setMsg({ ok:true, text:`${data.message} - ${data.name} added.` })
      setTimeout(() => nav('/admin/dashboard'), 1500)
    } catch (err) {
      setMsg({ ok:false, text: err.response?.data?.detail || 'Registration failed.' })
    } finally { setLoading(false) }
  }

  const nextHint = SAMPLE_STEPS[samples.length] || 'Great! You can capture more or register now.'

  return (
    <div style={s.page}>
      <div style={s.card}>
        <h2 style={s.title}>Register New Employee</h2>
        <input placeholder="Full Name *"   value={form.name}        onChange={e => setForm({...form, name:e.target.value})} />
        <input placeholder="Employee ID *" value={form.employee_id} onChange={e => setForm({...form, employee_id:e.target.value})} />
        <input placeholder="Department"    value={form.department}  onChange={e => setForm({...form, department:e.target.value})} />

        <div style={s.videoWrap}>
          <video ref={videoRef} style={s.video} muted playsInline autoPlay />
        </div>

        {error
          ? <p style={{...s.step, color:'#ef4444'}}>{error}</p>
          : <p style={s.step}>{nextHint}</p>}

        <div style={s.thumbs}>
          {[0,1,2].map(i => (
            samples[i]
              ? <img key={i} src={samples[i]} style={s.thumb} alt={`sample ${i+1}`} />
              : <div key={i} style={s.slot}>{i+1}</div>
          ))}
        </div>

        <button style={s.capBtn} onClick={grab} disabled={!ready}>
          Capture Sample ({samples.length} captured)
        </button>
        <p style={s.hint}>Tip: capture 3 samples (front, left, right) for best accuracy.</p>

        <button style={s.btn} onClick={handleRegister} disabled={loading}>
          {loading ? 'Registering...' : 'Register Employee'}
        </button>
        {samples.length > 0 &&
          <button style={s.reset} onClick={() => setSamples([])} disabled={loading}>Clear Samples</button>}

        {msg && <div style={{...s.msg, background: msg.ok ? '#064e3b' : '#450a0a', color: msg.ok ? '#10b981' : '#ef4444'}}>{msg.text}</div>}
      </div>
    </div>
  )
}
