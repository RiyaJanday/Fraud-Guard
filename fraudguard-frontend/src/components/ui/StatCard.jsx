import { ArrowUpRight, ArrowDownRight } from 'lucide-react'
import GlassCard from './GlassCard'
import AnimatedNumber from './AnimatedNumber'
import { cn } from '../../lib/utils'

export default function StatCard({ label, value, prefix = '', suffix = '', decimals = 0, delta, icon: Icon, iconColor = 'text-primary', delay = 0 }) {
  const positive = delta >= 0
  return (
    <GlassCard delay={delay} className="relative overflow-hidden group">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-medium text-white/50">{label}</p>
          <p className="mt-2 font-display text-3xl font-semibold tracking-tight text-white">
            <AnimatedNumber value={value} decimals={decimals} prefix={prefix} suffix={suffix} />
          </p>
        </div>
        {Icon && (
          <div className={cn('rounded-xl border border-white/10 bg-white/[0.04] p-2.5', iconColor)}>
            <Icon size={20} strokeWidth={2} />
          </div>
        )}
      </div>
      {delta !== undefined && (
        <div className="mt-4 flex items-center gap-1.5">
          <span
            className={cn(
              'flex items-center gap-0.5 rounded-full px-1.5 py-0.5 text-xs font-medium',
              positive ? 'bg-success/10 text-success' : 'bg-danger/10 text-danger'
            )}
          >
            {positive ? <ArrowUpRight size={13} /> : <ArrowDownRight size={13} />}
            {Math.abs(delta)}%
          </span>
          <span className="text-xs text-white/30">vs last week</span>
        </div>
      )}
      <div className="pointer-events-none absolute -right-8 -top-8 h-24 w-24 rounded-full bg-primary/10 blur-2xl transition-opacity duration-300 group-hover:opacity-100 opacity-0" />
    </GlassCard>
  )
}
