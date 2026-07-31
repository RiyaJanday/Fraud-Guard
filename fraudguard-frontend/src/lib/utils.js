export function cn(...classes) {
  return classes.filter(Boolean).join(' ')
}

export function formatCurrency(amount, currency = 'INR') {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency,
    maximumFractionDigits: 2,
  }).format(amount)
}

export function formatCompactNumber(num) {
  return new Intl.NumberFormat('en-IN', { notation: 'compact', maximumFractionDigits: 1 }).format(num)
}

export function formatTime(isoString) {
  const date = new Date(isoString)
  return date.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: true })
}

export function formatDateTime(isoString) {
  const date = new Date(isoString)
  return date.toLocaleString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: true,
  })
}

export function riskLevel(risk) {
  if (risk >= 75) return { label: 'Critical', color: 'danger' }
  if (risk >= 40) return { label: 'Elevated', color: 'warning' }
  return { label: 'Low', color: 'success' }
}

export const STATUS_META = {
  approved: { label: 'Approved', color: 'success' },
  mfa: { label: 'MFA Required', color: 'warning' },
  blocked: { label: 'Blocked', color: 'danger' },
}

/**
 * Triggers a browser download for an Axios blob response. Reads the
 * filename from the Content-Disposition header the backend already sets
 * (report_service.py) rather than hardcoding one here, so the two stay in
 * sync automatically instead of silently drifting apart.
 */
export function downloadBlobResponse(response, fallbackFilename) {
  const disposition = response.headers?.['content-disposition'] || ''
  const match = disposition.match(/filename="?([^";]+)"?/)
  const filename = match ? match[1] : fallbackFilename

  const url = window.URL.createObjectURL(new Blob([response.data]))
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(url)
}
