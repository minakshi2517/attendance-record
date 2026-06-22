import React, { useState, useEffect, useCallback } from 'react'
import useCamera from '../hooks/usecamera'
import api, { parseApiError } from '../api'
import {
  formatCountdown,
  saveCheckoutLock,
  loadCheckoutLock,
  clearCheckoutLock,
} from '../utils/datetime'

const SCAN_COUNT = 2
const SCAN_GAP_MS = 650

export default function CheckInOut() {
  const { videoRef, ready, error, start, captureBlob } = useCamera()
  const [loading, setLoading] = useState(false)
  const [status,  setStatus]  = useState('')
  const [result,  setResult]  = useState(null)
  const [checkoutWait, setCheckoutWait] = useState(null)
  const [checkoutReady, setCheckoutReady] = useState(true)

  useEffect(() => { start() }, [start])

  const refreshCheckoutTimer = useCallback(() => {
    const lock = loadCheckoutLock()
    if (!lock?.checkout_available_at) {
      setCheckoutWait(null)
      setCheckoutReady(true)
      return
    }
    const remaining = new Date(lock.checkout_available_at).getTime() - Date.now()
    if (remaining <= 0) {
      setCheckoutWait(null)
      setCheckoutReady(true)
      return
    }
    setCheckoutReady(false)
    setCheckoutWait(formatCountdown(remaining))
  }, [])

  useEffect(() => {
    refreshCheckoutTimer()
    const id = setInterval(refreshCheckoutTimer, 1000)
    return () => clearInterval(id)
  }, [refreshCheckoutTimer])

  const captureScans = async () => {
    const blobs = []
    for (let i = 0; i < SCAN_COUNT; i += 1) {
      setStatus(`Scan ${i + 1} of ${SCAN_COUNT} — look at the camera...`)
      const blob = await captureBlob()
      if (blob) blobs.push(blob)
      if (i < SCAN_COUNT - 1) await new Promise(r => setTimeout(r, SCAN_GAP_MS))
    }
    return blobs
  }

  const buildForm = (blobs) => {
    const body = new FormData()
    if (blobs[0]) body.append('face_image', blobs[0], 'face1.jpg')
    if (blobs[1]) body.append('face_image_2', blobs[1], 'face2.jpg')
    if (blobs[2]) body.append('face_image_3', blobs[2], 'face3.jpg')
    return body
  }

  const applyCheckoutLock = (data) => {
    if (data?.checkout_available_at) {
      saveCheckoutLock({
        checkout_available_at: data.checkout_available_at,
        check_in_time: data.check_in_time,
        employee_name: data.employee?.name,
      })
      refreshCheckoutTimer()
    }
  }

  const handleCheckoutError = (msg) => {
    const lower = msg.toLowerCase()
    if (lower.includes('check in') || lower.includes('no check-in')) {
      clearCheckoutLock()
      refreshCheckoutTimer()
    }
  }

  const submit = async (mode) => {
    if (!ready) { setResult({ ok:false, msg:'Camera is starting, please wait...' }); return }
    if (mode === 'checkout' && !checkoutReady) {
      setResult({ ok:false, msg:`Checkout available in ${checkoutWait}. Please wait.` })
      return
    }

    setLoading(true); setResult(null)
    try {
      const blobs = await captureScans()
      if (!blobs.length) { setResult({ ok:false, msg:'Could not capture. Please try again.' }); return }

      setStatus('Matching your face...')
      const endpoint = mode === 'checkin' ? '/api/attendance/checkin' : '/api/attendance/checkout'
      const { data } = await api.post(endpoint, buildForm(blobs))

      if (mode === 'checkin') {
        applyCheckoutLock(data)
      } else {
        clearCheckoutLock()
        refreshCheckoutTimer()
      }
      setResult({ ok:true, data })
      setStatus('')
    } catch (err) {
      let msg
      if (err.code === 'ECONNABORTED') {
        msg = 'Server took too long. Please try again — first face scan is slowest.'
      } else if (!err.response) {
        msg = 'Network error. Check your internet and try again.'
      } else {
        msg = parseApiError(err, `Server error (${err.response.status}). Please try again.`)
      }
      handleCheckoutError(msg)
      if (msg.toLowerCase().includes('too early to check out')) {
        const lock = loadCheckoutLock()
        if (lock?.checkout_available_at) refreshCheckoutTimer()
      }
      setResult({ ok:false, msg })
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
      <p className="checkin-sub">Check-in → wait 2 min → check-out. Face geometry only — not photo.</p>

      {!checkoutReady && checkoutWait && (
        <div className="alert alert-error" style={{ marginBottom:12, textAlign:'center' }}>
          Checkout available in <strong>{checkoutWait}</strong> (2 min after check-in)
          {loadCheckoutLock()?.employee_name ? (
            <div style={{ fontSize:12, marginTop:6, color:'#94a3b8' }}>
              Checked in as {loadCheckoutLock().employee_name} — if checkout fails, tap Check In again.
            </div>
          ) : null}
        </div>
      )}

      <div className={`camera-wrap ${loading ? 'scanning' : ''}`}>
        <video ref={videoRef} className="camera-video" muted playsInline autoPlay />
      </div>

      <p className="camera-status">
        {error ? <span style={{color:'#ef4444'}}>{error}</span> : ready ? 'Camera ready — one person, face the camera' : 'Starting camera...'}
      </p>

      <div className="checkin-btns">
        <button className="btn-success" onClick={() => submit('checkin')} disabled={loading || !ready}>
          {loading ? 'Scanning...' : 'Check In'}
        </button>
        <button
          className="btn-primary"
          onClick={() => submit('checkout')}
          disabled={loading || !ready || !checkoutReady}
          title={!checkoutReady ? `Checkout available in ${checkoutWait}` : 'Check out'}
        >
          {loading ? 'Scanning...' : checkoutReady ? 'Check Out' : `Wait ${checkoutWait}`}
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
              {result.data.checkout_available_at && !checkoutReady && (
                <div className="result-info">Checkout available in {checkoutWait}</div>
              )}
            </>
          ) : (
            <div className="result-error">{result.msg}</div>
          )}
        </div>
      )}
    </div>
  )
}
