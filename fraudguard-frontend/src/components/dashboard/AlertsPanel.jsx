import { AlertTriangle, ShieldAlert } from 'lucide-react'
import GlassCard from '../ui/GlassCard'

export default function AlertsPanel({ alerts }) {
  return (
    <GlassCard className="p-5">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="flex items-center gap-2 font-display text-base font-semibold">
          <ShieldAlert size={17} className="text-danger" /> Recent Alerts
        </h3>
        <span className="badge-danger">{alerts.length} active</span>
      </div>
      <div className="space-y-3">
        {alerts.map((a) => (
          <div
            key={a.id}
            className="flex items-start gap-3 rounded-xl border border-white/5 bg-white/[0.02] p-3 transition hover:border-white/10 hover:bg-white/[0.04]"
          >
            <div className={`mt-0.5 rounded-lg p-1.5 ${a.severity === 'danger' ? 'bg-danger/10 text-danger' : 'bg-warning/10 text-warning'}`}>
              <AlertTriangle size={14} />
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-white/85">{a.title}</p>
              <p className="text-xs text-white/35">{a.merchant} · Risk {a.risk}</p>
            </div>
            <span className="shrink-0 text-[11px] text-white/30">{a.time}</span>
          </div>
        ))}
      </div>
    </GlassCard>
  )
}
