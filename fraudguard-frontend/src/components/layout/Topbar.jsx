import { useState, useRef, useEffect } from 'react'
import { Menu, Search, Bell, ChevronDown, LogOut, Settings, UserCircle, CheckCheck } from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { useAuth } from '../../context/AuthContext'
import { useNotifications, typeMeta } from '../../context/NotificationsContext'
import { timeAgo } from '../../lib/transform'

export default function Topbar({ onMenuClick }) {
  const [notifOpen, setNotifOpen] = useState(false)
  const [profileOpen, setProfileOpen] = useState(false)
  const { user, logout } = useAuth()
  const { notifications, unreadCount, connected, markRead, markAllRead } = useNotifications()
  const navigate = useNavigate()
  const notifRef = useRef(null)
  const profileRef = useRef(null)

  useEffect(() => {
    function handleClickOutside(e) {
      if (notifRef.current && !notifRef.current.contains(e.target)) setNotifOpen(false)
      if (profileRef.current && !profileRef.current.contains(e.target)) setProfileOpen(false)
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  return (
    <header className="sticky top-0 z-20 flex h-16 items-center gap-4 border-b border-white/10 bg-bg/70 px-4 backdrop-blur-xl sm:px-6">
      <button onClick={onMenuClick} className="text-white/60 hover:text-white lg:hidden">
        <Menu size={22} />
      </button>

      <div className="hidden flex-1 max-w-md items-center gap-2 rounded-xl border border-white/10 bg-white/[0.03] px-3.5 py-2 sm:flex">
        <Search size={16} className="text-white/30" />
        <input
          placeholder="Search transactions, alerts, customers..."
          className="w-full bg-transparent text-sm text-white placeholder:text-white/30 outline-none"
        />
        <kbd className="rounded border border-white/10 bg-white/5 px-1.5 py-0.5 text-[10px] text-white/30">⌘K</kbd>
      </div>

      <div className="ml-auto flex items-center gap-2 sm:gap-3">
        <div
          title={connected ? 'Live notifications connected' : 'Reconnecting…'}
          className={`hidden items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium sm:flex ${
            connected ? 'border-success/30 bg-success/10 text-success' : 'border-warning/30 bg-warning/10 text-warning'
          }`}
        >
          <span className="relative flex h-1.5 w-1.5">
            {connected && <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-success opacity-75" />}
            <span className={`relative inline-flex h-1.5 w-1.5 rounded-full ${connected ? 'bg-success' : 'bg-warning'}`} />
          </span>
          {connected ? 'System Live' : 'Reconnecting'}
        </div>

        <div className="relative" ref={notifRef}>
          <button
            onClick={() => { setNotifOpen((v) => !v); setProfileOpen(false) }}
            className="relative flex h-10 w-10 items-center justify-center rounded-xl border border-white/10 bg-white/[0.03] text-white/60 transition hover:text-white hover:bg-white/[0.08]"
          >
            <Bell size={18} />
            {unreadCount > 0 && (
              <span className="absolute right-2 top-2 h-2 w-2 rounded-full bg-danger ring-2 ring-bg" />
            )}
          </button>
          <AnimatePresence>
            {notifOpen && (
              <motion.div
                initial={{ opacity: 0, y: -8, scale: 0.97 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: -8, scale: 0.97 }}
                transition={{ duration: 0.15 }}
                className="glass-card absolute right-0 mt-2 w-80 overflow-hidden p-0"
              >
                <div className="flex items-center justify-between border-b border-white/10 px-4 py-3">
                  <p className="text-sm font-semibold text-white">Notifications</p>
                  {unreadCount > 0 && (
                    <button
                      onClick={markAllRead}
                      className="flex items-center gap-1 text-[11px] text-white/40 hover:text-white"
                    >
                      <CheckCheck size={12} /> Mark all read
                    </button>
                  )}
                </div>
                <div className="max-h-80 overflow-y-auto">
                  {notifications.length === 0 ? (
                    <p className="px-4 py-8 text-center text-xs text-white/30">No notifications yet.</p>
                  ) : (
                    notifications.map((n) => (
                      <button
                        key={n.id}
                        onClick={() => !n.is_read && markRead(n.id)}
                        className={`flex w-full gap-3 border-b border-white/5 px-4 py-3 text-left last:border-0 hover:bg-white/[0.03] ${!n.is_read ? 'bg-white/[0.02]' : ''}`}
                      >
                        <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${typeMeta(n.type).dotClass}`} />
                        <div>
                          <p className={`text-sm font-medium ${n.is_read ? 'text-white/60' : 'text-white/90'}`}>{n.title}</p>
                          <p className="mt-0.5 text-xs text-white/40">{n.message}</p>
                          <p className="mt-1 text-[11px] text-white/25">{timeAgo(n.created_at)}</p>
                        </div>
                      </button>
                    ))
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        <div className="relative" ref={profileRef}>
          <button
            onClick={() => { setProfileOpen((v) => !v); setNotifOpen(false) }}
            className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/[0.03] py-1.5 pl-1.5 pr-2.5 hover:bg-white/[0.08]"
          >
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-primary to-accent text-xs font-semibold">
              {user?.avatar || 'AM'}
            </div>
            <span className="hidden text-sm text-white/80 sm:block">{user?.name?.split(' ')[0] || 'Analyst'}</span>
            <ChevronDown size={14} className="hidden text-white/40 sm:block" />
          </button>
          <AnimatePresence>
            {profileOpen && (
              <motion.div
                initial={{ opacity: 0, y: -8, scale: 0.97 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: -8, scale: 0.97 }}
                transition={{ duration: 0.15 }}
                className="glass-card absolute right-0 mt-2 w-56 overflow-hidden p-1.5"
              >
                <Link to="/profile" onClick={() => setProfileOpen(false)} className="flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm text-white/70 hover:bg-white/[0.06] hover:text-white">
                  <UserCircle size={16} /> Profile
                </Link>
                <Link to="/settings" onClick={() => setProfileOpen(false)} className="flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm text-white/70 hover:bg-white/[0.06] hover:text-white">
                  <Settings size={16} /> Settings
                </Link>
                <button
                  onClick={() => { logout(); navigate('/login') }}
                  className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-sm text-danger hover:bg-danger/10"
                >
                  <LogOut size={16} /> Log out
                </button>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </header>
  )
}
