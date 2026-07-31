import { NavLink } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  LayoutDashboard,
  Receipt,
  Radar,
  BarChart3,
  BrainCircuit,
  FileText,
  Settings,
  UserCircle,
  ShieldCheck,
  X,
} from 'lucide-react'
import { cn } from '../../lib/utils'

const NAV_ITEMS = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/transactions', label: 'Transactions', icon: Receipt },
  { to: '/live-monitoring', label: 'Live Monitoring', icon: Radar },
  { to: '/fraud-analytics', label: 'Fraud Analytics', icon: BarChart3 },
  { to: '/explainability', label: 'Explainability', icon: BrainCircuit },
  { to: '/reports', label: 'Reports', icon: FileText },
]

const BOTTOM_ITEMS = [
  { to: '/settings', label: 'Settings', icon: Settings },
  { to: '/profile', label: 'Profile', icon: UserCircle },
]

export default function Sidebar({ open, onClose }) {
  return (
    <>
      {open && (
        <div className="fixed inset-0 z-30 bg-black/60 backdrop-blur-sm lg:hidden" onClick={onClose} />
      )}
      <motion.aside
        initial={{ x: -20, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        transition={{ duration: 0.4 }}
        className={cn(
          'fixed inset-y-0 left-0 z-40 w-64 shrink-0 transform border-r border-white/10 bg-bg-soft/95 backdrop-blur-xl transition-transform duration-300 lg:static lg:translate-x-0 lg:bg-bg-soft/40',
          open ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        <div className="flex h-16 items-center justify-between px-5">
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-secondary shadow-glow">
              <ShieldCheck size={18} className="text-white" />
            </div>
            <span className="font-display text-lg font-semibold tracking-tight">FraudGuard</span>
          </div>
          <button onClick={onClose} className="text-white/40 hover:text-white lg:hidden">
            <X size={20} />
          </button>
        </div>

        <nav className="mt-4 flex flex-col gap-1 px-3">
          <p className="px-3.5 pb-1.5 pt-3 text-[11px] font-semibold uppercase tracking-wider text-white/25">
            Monitor
          </p>
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              onClick={onClose}
              className={({ isActive }) => (isActive ? 'nav-link-active' : 'nav-link')}
            >
              <item.icon size={18} strokeWidth={2} />
              {item.label}
            </NavLink>
          ))}

          <p className="px-3.5 pb-1.5 pt-5 text-[11px] font-semibold uppercase tracking-wider text-white/25">
            Account
          </p>
          {BOTTOM_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              onClick={onClose}
              className={({ isActive }) => (isActive ? 'nav-link-active' : 'nav-link')}
            >
              <item.icon size={18} strokeWidth={2} />
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="absolute bottom-4 left-3 right-3">
          <div className="glass-panel flex items-center gap-2 rounded-xl p-3">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-success opacity-75" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-success" />
            </span>
            <div className="text-xs">
              <p className="font-medium text-white/80">Model v4.2.1 Live</p>
              <p className="text-white/35">99.98% uptime</p>
            </div>
          </div>
        </div>
      </motion.aside>
    </>
  )
}
