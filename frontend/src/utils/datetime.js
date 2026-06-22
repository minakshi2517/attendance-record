export const OFFICE_TZ = 'Asia/Kolkata'

export function formatTime(iso) {
  if (!iso) return '-'
  return new Date(iso).toLocaleTimeString('en-IN', {
    timeZone: OFFICE_TZ,
    hour: '2-digit',
    minute: '2-digit',
    hour12: true,
  })
}

export function formatDate(iso) {
  if (!iso) return '-'
  return new Date(iso).toLocaleDateString('en-IN', {
    timeZone: OFFICE_TZ,
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  })
}

export function formatDateTime(iso) {
  if (!iso) return '-'
  return new Date(iso).toLocaleString('en-IN', {
    timeZone: OFFICE_TZ,
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: true,
  })
}

export function formatCountdown(ms) {
  const total = Math.max(0, Math.ceil(ms / 1000))
  const m = Math.floor(total / 60)
  const s = total % 60
  return `${m}m ${String(s).padStart(2, '0')}s`
}

export const CHECKOUT_LOCK_KEY = 'attendance_checkout_lock'

export function saveCheckoutLock(data) {
  localStorage.setItem(CHECKOUT_LOCK_KEY, JSON.stringify(data))
}

export function loadCheckoutLock() {
  try {
    const raw = localStorage.getItem(CHECKOUT_LOCK_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

export function clearCheckoutLock() {
  localStorage.removeItem(CHECKOUT_LOCK_KEY)
}
