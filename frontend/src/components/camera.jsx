import React, { useRef, useState, useEffect } from 'react'

const s = {
  wrap:   { display:'flex', flexDirection:'column', alignItems:'center', gap:12 },
  video:  { width:320, height:240, borderRadius:12, border:'2px solid #6366f1', background:'#000', transform:'scaleX(-1)', objectFit:'cover' },
  canvas: { display:'none' },
  btns:   { display:'flex', gap:10 },
  start:  { background:'#6366f1', color:'#fff' },
  cap:    { background:'#10b981', color:'#fff' },
  retake: { background:'#f59e0b', color:'#fff' },
  preview:{ width:320, height:240, borderRadius:12, border:'2px solid #10b981', objectFit:'cover', transform:'scaleX(-1)' },
  hint:   { color:'#94a3b8', fontSize:13, textAlign:'center', maxWidth:320 },
}

export default function Camera({ onCapture }) {
  const videoRef  = useRef(null)
  const canvasRef = useRef(null)
  const streamRef = useRef(null)
  const [streaming, setStreaming] = useState(false)
  const [captured,  setCaptured]  = useState(null)

  const stopStream = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop())
      streamRef.current = null
    }
  }

  const startCamera = async () => {
    try {
      const st = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'user', width: { ideal: 640 }, height: { ideal: 480 } },
        audio: false,
      })
      streamRef.current = st
      setCaptured(null)
      setStreaming(true)
      const video = videoRef.current
      if (video) {
        video.srcObject = st
        await video.play().catch(() => {})
      }
    } catch (err) {
      alert('Could not open the camera. Please allow camera permission in your browser and try again.')
    }
  }

  const capture = () => {
    const video  = videoRef.current
    const canvas = canvasRef.current
    if (!video || !canvas) return

    const w = video.videoWidth  || 640
    const h = video.videoHeight || 480

    canvas.width  = w
    canvas.height = h
    const ctx = canvas.getContext('2d')
    // Mirror so the saved image matches what the user sees
    ctx.save()
    ctx.translate(w, 0)
    ctx.scale(-1, 1)
    ctx.drawImage(video, 0, 0, w, h)
    ctx.restore()

    const b64 = canvas.toDataURL('image/jpeg', 0.92)
    setCaptured(b64)
    onCapture(b64)
    stopStream()
    setStreaming(false)
  }

  const retake = () => {
    setCaptured(null)
    onCapture(null)
    startCamera()
  }

  useEffect(() => () => stopStream(), [])

  return (
    <div style={s.wrap}>
      {!captured ? (
        <>
          <video
            ref={videoRef}
            style={{ ...s.video, display: streaming ? 'block' : 'none' }}
            muted
            playsInline
            autoPlay
          />
          <canvas ref={canvasRef} style={s.canvas} />
          {streaming && <p style={s.hint}>Look straight at the camera in good lighting, then capture.</p>}
          <div style={s.btns}>
            {!streaming && <button type="button" style={s.start} onClick={startCamera}>Open Camera</button>}
            {streaming  && <button type="button" style={s.cap} onClick={capture}>Capture Photo</button>}
          </div>
        </>
      ) : (
        <>
          <img src={captured} style={s.preview} alt="captured" />
          <button type="button" style={s.retake} onClick={retake}>Retake</button>
        </>
      )}
    </div>
  )
}
