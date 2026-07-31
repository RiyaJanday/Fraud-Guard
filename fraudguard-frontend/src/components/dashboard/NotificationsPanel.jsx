import { Bell } from 'lucide-react'
import GlassCard from '../ui/GlassCard'

const DOT = { success: 'bg-success', danger: 'bg-danger', info: 'bg-accent' }

export default function NotificationsPanel({ notifications }) {
  return (
    <GlassCard className="p-5">
      <h3 className="mb-4 flex items-center gap-2 font-display text-base font-semibold">
        <Bell size={17} className="text-accent" /> Notifications
      </h3>
      <div className="space-y-4">
        {notifications.map((n) => (
          <div key={n.id} className="flex gap-3">
            <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${DOT[n.type]}`} />
            <div>
              <p className="text-sm font-medium text-white/85">{n.title}</p>
              <p className="mt-0.5 text-xs text-white/40">{n.desc}</p>
              <p className="mt-1 text-[11px] text-white/25">{n.time}</p>
            </div>
          </div>
        ))}
      </div>
    </GlassCard>
  )
}
