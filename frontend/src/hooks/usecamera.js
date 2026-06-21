import { useRef, useState, useCallback, useEffect } from 'react'

// Shared camera logic: live preview + capture a mirrored JPEG frame on demand.
export default function useCamera() {
  const videoRef  = useRef(null)
  const streamRef = useRef(null)
  const [ready, setReady] = useState(false)
  const [error, setError] = useState('')

  const start = useCallback(async () => {
    setError('')
    try {
      const st = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'user', width: { ideal: 640 }, height: { ideal: 480 } },
        audio: false,
      })
      streamRef.current = st
      const v = videoRef.current
      if (v) {
        v.srcObject = st
        await v.play().catch(() => {})
      }
      setReady(true)
    } catch {
      setError('Could not access the camera. Please allow camera permission and reload.')
      setReady(false)
    }
  }, [])

  const stop = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop())
      streamRef.current = null
    }
    setReady(false)
  }, [])

  const capture = useCallback(() => {
    const v = videoRef.current
    if (!v || !v.videoWidth) return null
    const w = v.videoWidth, h = v.videoHeight
    const c = document.createElement('canvas')
    c.width = w; c.height = h
    const ctx = c.getContext('2d')
    ctx.translate(w, 0)
    ctx.scale(-1, 1)
    ctx.drawImage(v, 0, 0, w, h)
    return c.toDataURL('image/jpeg', 0.92)
  }, [])

  useEffect(() => () => stop(), [stop])

  return { videoRef, ready, error, start, stop, capture }
}
