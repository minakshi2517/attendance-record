import React, { useRef, useState, useEffect } from 'react'

const s = {
  wrap:   { display:'flex', flexDirection:'column', alignItems:'center', gap:12 },
  video:  { width:320, height:240, borderRadius:12, border:'2px solid #6366f1', background:'#000' },
  canvas: { display:'none' },
  btns:   { display:'flex', gap:10 },
  start:  { background:'#6366f1', color:'#fff' },
  cap:    { background:'#10b981', color:'#fff' },
  retake: { background:'#f59e0b', color:'#fff' },
  preview:{ width:320, height:240, borderRadius:12, border:'2px solid #10b981', objectFit:'cover' },
}

export default function Camera({ onCapture }) {
  const videoRef  = useRef(null)
  const canvasRef = useRef(null)
  const [stream,   setStream]   = useState(null)
  const [captured, setCaptured] = useState(null)  // base64 image

  const startCamera = async () => {
    try {
      const st = await navigator.mediaDevices.getUserMedia({ video: true })
      videoRef.current.srcObject = st
      videoRef.current.play()
      setStream(st)
      setCaptured(null)
    } catch {
      alert('Camera open nahi hua. Permission do.')
    }
  }

  const capture = () => {
    const canvas = canvasRef.current
    const video  = videoRef.current
    canvas.width  = 640
    canvas.height = 480
    canvas.getContext('2d').drawImage(video, 0, 0, 640, 480)
    const b64 = canvas.toDataURL('image/jpeg', 1.0)
    setCaptured(b64)
    onCapture(b64)        // parent ko bhejna
    stream?.getTracks().forEach(t => t.stop())
    setStream(null)
  }

  const retake = () => { setCaptured(null); startCamera() }

  useEffect(() => () => stream?.getTracks().forEach(t => t.stop()), [stream])

  return (
    <div style={s.wrap}>
      {!captured ? (
        <>
          <video ref={videoRef} style={s.video} muted />
          <canvas ref={canvasRef} style={s.canvas} />
          <div style={s.btns}>
            {!stream  && <button style={s.start} onClick={startCamera}>📷 Camera Kholo</button>}
            {stream   && <button style={s.cap}   onClick={capture}>✅ Photo Lo</button>}
          </div>
        </>
      ) : (
        <>
          <img src={captured} style={s.preview} alt="captured" />
          <button style={s.retake} onClick={retake}>🔄 Dobara Lo</button>
        </>
      )}
    </div>
  )
}
