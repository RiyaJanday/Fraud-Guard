import { Bell, CheckCheck } from 'lucide-react'
import GlassCard from '../ui/GlassCard'
import { typeMeta } from '../../context/NotificationsContext'
import { timeAgo } from '../../lib/transform'

export default function NotificationsPanel({ notifications, unreadCount, onMarkRead, onMarkAllRead }) {
  return (
    <GlassCard className="p-5">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="flex items-center gap-2 font-display text-base font-semibold">
          <Bell size={17} className="text-accent" /> Notifications
        </h3>
        {unreadCount > 0 && (
          <button onClick={onMarkAllRead} className="flex items-center gap-1 text-[11px] text-white/40 hover:text-white">
            <CheckCheck size={12} /> Mark all read
          </button>
        )}
      </div>
      <div className="space-y-4">
        {notifications.length === 0 ? (
          <p className="py-4 text-center text-xs text-white/30">No notifications yet.</p>
        ) : (
          notifications.slice(0, 6).map((n) => (
            <button
              key={n.id}
              onClick={() => !n.is_read && onMarkRead(n.id)}
              className="flex w-full gap-3 text-left"
            >
              <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${typeMeta(n.type).dotClass}`} />
              <div>
                <p className={`text-sm font-medium ${n.is_read ? 'text-white/60' : 'text-white/85'}`}>{n.title}</p>
                <p className="mt-0.5 text-xs text-white/40">{n.message}</p>
                <p className="mt-1 text-[11px] text-white/25">{timeAgo(n.created_at)}</p>
              </div>
            </button>
          ))
        )}
      </div>
    </GlassCard>
  )
}
