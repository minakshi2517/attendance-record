import React, { useState, useEffect } from 'react'
import useCamera from '../hooks/usecamera'
import api from '../api'

const s = {
  page:   { maxWidth:500, margin:'40px auto', padding:'0 16px' },
  title:  { fontSize:28, fontWeight:700, textAlign:'center', marginBottom:8, color:'#818cf8' },
  sub:    { textAlign:'center', color:'#64748b', marginBottom:24, fontSize:14 },
  videoWrap: { width:'100%', maxWidth:380, margin:'0 auto' },
  video:  { width:'100%', borderRadius:16, border:'2px solid #6366f1', background:'#000', transform:'scaleX(-1)', aspectRatio:'4 / 3', objectFit:'cover' },
  btns:   { display:'flex', gap:12, marginTop:20 },
  inBtn:  { flex:1, background:'#10b981', color:'#fff', padding:16, fontSize:16 },
  outBtn: { flex:1, background:'#6366f1', color:'#fff', padding:16, fontSize:16 },
  result: { background:'#1e293b', borderRadius:12, padding:20, marginTop:20, textAlign:'center' },
  success:{ color:'#10b981', fontSize:18, fontWeight:700 },
  error:  { color:'#ef4444', fontSize:16 },
  info:   { color:'#94a3b8', fontSize:14, marginTop:8 },
  hint:   { color:'#94a3b8', fontSize:13, textAlign:'center', marginTop:12 },
}

export default function CheckInOut() {
  const { videoRef, ready, error, start, capture } = useCamera()
  const [loading, setLoading] = useState(false)
  const [result,  setResult]  = useState(null)

  useEffect(() => { start() }, [start])

  const submit = async (mode) => {
    if (!ready) { setResult({ ok:false, msg:'Camera is starting, please wait a moment.' }); return }
    setLoading(true); setResult(null)
    try {
      const image = capture()
      if (!image) { setResult({ ok:false, msg:'Could not capture the photo. Try again.' }); return }
      const endpoint = mode === 'checkin' ? '/api/attendance/checkin' : '/api/attendance/checkout'
      const { data } = await api.post(endpoint, { image })
      setResult({ ok:true, data })
    } catch (err) {
      setResult({ ok:false, msg: err.response?.data?.detail || 'Something went wrong. Please try again.' })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={s.page}>
      <h1 style={s.title}>Face Attendance</h1>
      <p style={s.sub}>Look at the camera and tap a button. That's it.</p>

      <div style={s.videoWrap}>
        <video ref={videoRef} style={s.video} muted playsInline autoPlay />
      </div>

      {error
        ? <p style={s.error}>{error}</p>
        : <p style={s.hint}>{ready ? 'Camera ready' : 'Starting camera...'}</p>}

      <div style={s.btns}>
        <button style={s.inBtn} onClick={() => submit('checkin')} disabled={loading || !ready}>
          {loading ? 'Please wait...' : 'Check In'}
        </button>
        <button style={s.outBtn} onClick={() => submit('checkout')} disabled={loading || !ready}>
          {loading ? 'Please wait...' : 'Check Out'}
        </button>
      </div>

      {result && (
        <div style={s.result}>
          {result.ok ? (
            <>
              <div style={s.success}>{result.data.message}</div>
              {result.data.employee && (
                <div style={s.info}>
                  <div>Name: {result.data.employee.name}</div>
                  <div>Department: {result.data.employee.department || 'N/A'}</div>
                  <div>Match confidence: {result.data.confidence}%</div>
                </div>
              )}
              {result.data.duration && <div style={s.info}>Time worked: {result.data.duration}</div>}
            </>
          ) : (
            <div style={s.error}>{result.msg}</div>
          )}
        </div>
      )}
    </div>
  )
}
