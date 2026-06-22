import { useRef, useState, useCallback, useEffect } from 'react'

const MAX_WIDTH = 420
const JPEG_QUALITY = 0.70

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

  const drawFrame = useCallback((ctx, v, w, h) => {
    ctx.translate(w, 0)
    ctx.scale(-1, 1)
    ctx.drawImage(v, 0, 0, w, h)
  }, [])

  const capture = useCallback(() => {
    const v = videoRef.current
    if (!v || !v.videoWidth) return null

    const srcW = v.videoWidth
    const srcH = v.videoHeight
    const scale = Math.min(1, MAX_WIDTH / srcW)
    const w = Math.round(srcW * scale)
    const h = Math.round(srcH * scale)

    const c = document.createElement('canvas')
    c.width = w
    c.height = h
    const ctx = c.getContext('2d')
    drawFrame(ctx, v, w, h)
    return c.toDataURL('image/jpeg', JPEG_QUALITY)
  }, [drawFrame])

  const captureBlob = useCallback(() => new Promise((resolve) => {
    const v = videoRef.current
    if (!v || !v.videoWidth) {
      resolve(null)
      return
    }

    const srcW = v.videoWidth
    const srcH = v.videoHeight
    const scale = Math.min(1, MAX_WIDTH / srcW)
    const w = Math.round(srcW * scale)
    const h = Math.round(srcH * scale)

    const c = document.createElement('canvas')
    c.width = w
    c.height = h
    const ctx = c.getContext('2d')
    drawFrame(ctx, v, w, h)
    c.toBlob(blob => resolve(blob), 'image/jpeg', JPEG_QUALITY)
  }), [drawFrame])

  const captureMultiple = useCallback(async (count = 3, gapMs = 700, onStep) => {
    const shots = []
    for (let i = 0; i < count; i += 1) {
      if (onStep) onStep(i + 1, count)
      const img = capture()
      if (img) shots.push(img)
      if (i < count - 1) {
        await new Promise(r => setTimeout(r, gapMs))
      }
    }
    return shots
  }, [capture])

  useEffect(() => () => stop(), [stop])

  return { videoRef, ready, error, start, stop, capture, captureBlob, captureMultiple }
}
