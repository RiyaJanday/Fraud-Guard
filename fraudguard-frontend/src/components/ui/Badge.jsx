import { cn } from '../../lib/utils'

const COLOR_MAP = {
  success: 'badge-success',
  warning: 'badge-warning',
  danger: 'badge-danger',
  info: 'badge bg-accent/10 text-accent border-accent/30',
  neutral: 'badge bg-white/5 text-white/60 border-white/10',
}

export default function Badge({ color = 'neutral', children, dot = true, className }) {
  return (
    <span className={cn(COLOR_MAP[color], className)}>
      {dot && <span className="h-1.5 w-1.5 rounded-full bg-current" />}
      {children}
    </span>
  )
}
