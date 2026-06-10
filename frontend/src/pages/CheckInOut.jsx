import React, { useState } from 'react'
import Camera from '../components/Camera'
import api    from '../api'

const s = {
  page:   { maxWidth:500, margin:'60px auto', padding:24 },
  title:  { fontSize:28, fontWeight:700, textAlign:'center', marginBottom:8, color:'#818cf8' },
  sub:    { textAlign:'center', color:'#64748b', marginBottom:32 },
  btns:   { display:'flex', gap:12, marginBottom:24, justifyContent:'center' },
  active: { background:'#6366f1', color:'#fff' },
  idle:   { background:'#1e293b', color:'#94a3b8', border:'1px solid #334155' },
  result: { background:'#1e293b', borderRadius:12, padding:20, marginTop:24, textAlign:'center' },
  success:{ color:'#10b981', fontSize:18, fontWeight:700 },
  error:  { color:'#ef4444', fontSize:16 },
  info:   { color:'#94a3b8', fontSize:14, marginTop:8 },
}

export default function CheckInOut() {
  const [mode,    setMode]    = useState('checkin')   // 'checkin' | 'checkout'
  const [image,   setImage]   = useState(null)
  const [loading, setLoading] = useState(false)
  const [result,  setResult]  = useState(null)

  const handleSubmit = async () => {
    if (!image) { alert('Pehle photo lo!'); return }
    setLoading(true); setResult(null)
    try {
      const endpoint = mode === 'checkin' ? '/api/attendance/checkin' : '/api/attendance/checkout'
      const { data } = await api.post(endpoint, { image })
      setResult({ ok: true, data })
    } catch (err) {
      setResult({ ok: false, msg: err.response?.data?.detail || 'Kuch problem aayi' })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={s.page}>
      <h1 style={s.title}>Face Attendance</h1>
      <p style={s.sub}>Apna chehra dikhao — baaki system karta hai</p>

      {/* Toggle: Check In / Check Out */}
      <div style={s.btns}>
        <button style={mode==='checkin'  ? s.active : s.idle} onClick={() => { setMode('checkin');  setResult(null) }}>
          ✅ Check In
        </button>
        <button style={mode==='checkout' ? s.active : s.idle} onClick={() => { setMode('checkout'); setResult(null) }}>
          🚪 Check Out
        </button>
      </div>

      <Camera onCapture={setImage} />

      <button
        style={{ background:'#6366f1', color:'#fff', width:'100%', marginTop:16, padding:14, fontSize:16 }}
        onClick={handleSubmit}
        disabled={loading}
      >
        {loading ? '⏳ Processing...' : mode==='checkin' ? '✅ Mark Attendance' : '🚪 Check Out'}
      </button>

      {result && (
        <div style={s.result}>
          {result.ok ? (
            <>
              <div style={s.success}>{result.data.message}</div>
              {result.data.employee && (
                <div style={s.info}>
                  <div>👤 {result.data.employee.name}</div>
                  <div>🏢 {result.data.employee.department || 'N/A'}</div>
                  <div>🎯 Confidence: {result.data.confidence}%</div>
                </div>
              )}
              {result.data.duration && <div style={s.info}>⏱ Kaam kiya: {result.data.duration}</div>}
            </>
          ) : (
            <div style={s.error}>❌ {result.msg}</div>
          )}
        </div>
      )}
    </div>
  )
}
