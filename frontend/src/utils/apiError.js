export function parseApiError(err, fallback = 'Something went wrong. Please try again.') {
  const detail = err?.response?.data?.detail
  if (detail == null || detail === '') return fallback
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    const parts = detail.map(item => {
      if (typeof item === 'string') return item
      if (item && typeof item === 'object') return item.msg || item.message || ''
      return String(item)
    }).filter(Boolean)
    return parts.length ? parts.join('. ') : fallback
  }
  if (typeof detail === 'object') {
    return detail.msg || detail.message || fallback
  }
  return String(detail)
}
