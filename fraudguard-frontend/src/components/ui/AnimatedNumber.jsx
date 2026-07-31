import { useEffect, useRef } from 'react'
import { animate, useInView } from 'framer-motion'

function formatNumber(n, decimals, prefix, suffix) {
  const fixed = Number(n.toFixed(decimals))
  const formatted = fixed.toLocaleString('en-IN', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })
  return `${prefix}${formatted}${suffix}`
}

// Lightweight drop-in replacement for react-countup, built directly on
// Framer Motion (already a core dependency) to avoid third-party bundling
// issues. Animates from 0 -> value once the element scrolls into view.
export default function AnimatedNumber({
  value,
  duration = 1.6,
  decimals = 0,
  prefix = '',
  suffix = '',
}) {
  const spanRef = useRef(null)
  const inView = useInView(spanRef, { once: true, margin: '-40px' })

  useEffect(() => {
    const node = spanRef.current
    if (!node) return
    if (!inView) {
      node.textContent = formatNumber(0, decimals, prefix, suffix)
      return
    }
    const controls = animate(0, value, {
      duration,
      ease: [0.16, 1, 0.3, 1],
      onUpdate(latest) {
        node.textContent = formatNumber(latest, decimals, prefix, suffix)
      },
    })
    return () => controls.stop()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [inView, value, duration, decimals, prefix, suffix])

  return <span ref={spanRef}>{formatNumber(0, decimals, prefix, suffix)}</span>
}
