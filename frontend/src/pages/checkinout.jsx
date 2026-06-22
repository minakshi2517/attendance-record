import React, { useState, useEffect } from 'react'
import useCamera from '../hooks/usecamera'
import api, { parseApiError } from '../api'

export default function CheckInOut() {
  const { videoRef, ready, error, start, captureBlob } = useCamera()
  const [loading, setLoading] = useState(false)
  const [status,  setStatus]  = useState('')
  const [result,  setResult]  = useState(null)

  useEffect(() => { start() }, [start])

  const submit = async (mode) => {
    if (!ready) { setResult({ ok:false, msg:'Camera is starting, please wait...' }); return }
    setLoading(true); setResult(null)
    setStatus('Scan 1 of 2 — look at the camera...')
    try {
      const blob1 = await captureBlob()
      if (!blob1) { setResult({ ok:false, msg:'Could not capture. Please try again.' }); return }
      setStatus('Scan 2 of 2 — hold still...')
      await new Promise(r => setTimeout(r, 700))
      const blob2 = await captureBlob()

      const body = new FormData()
      body.append('face_image', blob1, 'face1.jpg')
      if (blob2) body.append('face_image_2', blob2, 'face2.jpg')

      setStatus('Matching your face...')
      const endpoint = mode === 'checkin' ? '/api/attendance/checkin' : '/api/attendance/checkout'
      const { data } = await api.post(endpoint, body)
      setResult({ ok:true, data })
      setStatus('')
    } catch (err) {
      setResult({ ok:false, msg: parseApiError(err) })
      setStatus('')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="checkin-page">
      {loading && (
        <div style={{
          position:'fixed', inset:0, background:'rgba(15,23,42,0.92)',
          display:'flex', flexDirection:'column', alignItems:'center',
          justifyContent:'center', zIndex:300, padding:24, textAlign:'center',
        }}>
          <div style={{fontSize:40, marginBottom:16}}>⏳</div>
          <p style={{color:'#e2e8f0', fontSize:16, fontWeight:600, marginBottom:8}}>{status}</p>
          <p style={{color:'#64748b', fontSize:13}}>First scan can take up to 60 seconds — please wait.</p>
        </div>
      )}

      <h1 className="checkin-title">Face Attendance</h1>
      <p className="checkin-sub">Look at the camera — same person who registered will be matched</p>

      <div className={`camera-wrap ${loading ? 'scanning' : ''}`}>
        <video ref={videoRef} className="camera-video" muted playsInline autoPlay />
      </div>

      <p className="camera-status">
        {error ? <span style={{color:'#ef4444'}}>{error}</span> : ready ? 'Camera ready — one person, good light, face the camera' : 'Starting camera...'}
      </p>

      <div className="checkin-btns">
        <button className="btn-success" onClick={() => submit('checkin')} disabled={loading || !ready}>
          {loading ? 'Scanning...' : 'Check In'}
        </button>
        <button className="btn-primary" onClick={() => submit('checkout')} disabled={loading || !ready}>
          {loading ? 'Scanning...' : 'Check Out'}
        </button>
      </div>

      {result && (
        <div className="result-box">
          {result.ok ? (
            <>
              <div className="result-success">{result.data.message}</div>
              {result.data.employee && (
                <div className="result-info">
                  <div>{result.data.employee.name} · {result.data.employee.department || 'N/A'}</div>
                  <div>Match: {result.data.confidence}%</div>
                </div>
              )}
              {result.data.duration && <div className="result-info">Worked: {result.data.duration}</div>}
            </>
          ) : (
            <div className="result-error">{result.msg}</div>
          )}
        </div>
      )}
    </div>
  )
}
