import { useEffect, useState } from 'react'
import { NavLink } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  LayoutDashboard,
  Receipt,
  Radar,
  BarChart3,
  BrainCircuit,
  Activity,
  FileText,
  Settings,
  UserCircle,
  ShieldCheck,
  ClipboardList,
  ShieldAlert,
  Sliders,
  Database,
  X,
} from 'lucide-react'
import { cn } from '../../lib/utils'
import { useAuth } from '../../context/AuthContext'
import { fraudApi } from '../../lib/api'

const NAV_ITEMS = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/transactions', label: 'Transactions', icon: Receipt },
  { to: '/review-queue', label: 'Review Queue', icon: ShieldAlert },
  { to: '/rules', label: 'Business Rules', icon: Sliders },
  { to: '/model-registry', label: 'Model Registry', icon: Database },
  { to: '/live-monitoring', label: 'Live Monitoring', icon: Radar },
  { to: '/fraud-analytics', label: 'Fraud Analytics', icon: BarChart3 },
  { to: '/explainability', label: 'Explainability', icon: BrainCircuit },
  { to: '/drift', label: 'Drift Monitoring', icon: Activity },
  { to: '/reports', label: 'Reports', icon: FileText },
  { to: '/audit-log', label: 'Audit Trail', icon: ClipboardList, adminOnly: true },
]

const BOTTOM_ITEMS = [
  { to: '/settings', label: 'Settings', icon: Settings },
  { to: '/profile', label: 'Profile', icon: UserCircle },
]

export default function Sidebar({ open, onClose }) {
  const { user } = useAuth()
  const isAdmin = user?.role === 'admin'
  const navItems = NAV_ITEMS.filter((item) => !item.adminOnly || isAdmin)

  // Real active-model status for the footer badge below — this used to be a
  // hardcoded "Model v4.2.1 Live / 99.98% uptime" string that didn't match
  // whatever model was actually registered as active.
  const [modelStatus, setModelStatus] = useState(null)
  useEffect(() => {
    fraudApi
      .getModelStatus()
      .then(({ data }) => setModelStatus(data))
      .catch(() => setModelStatus(null))
  }, [])
  const activeModel = modelStatus?.active_model

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
          'fixed inset-y-0 left-0 z-40 flex w-64 shrink-0 transform flex-col border-r border-white/10 bg-bg-soft/95 backdrop-blur-xl transition-transform duration-300 lg:static lg:translate-x-0 lg:bg-bg-soft/40',
          open ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        <div className="flex h-16 shrink-0 items-center justify-between px-5">
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

        <nav className="mt-4 flex min-h-0 flex-1 flex-col gap-1 overflow-y-auto px-3 pb-2">
          <p className="px-3.5 pb-1.5 pt-3 text-[11px] font-semibold uppercase tracking-wider text-white/25">
            Monitor
          </p>
          {navItems.map((item) => (
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

        <div className="shrink-0 px-3 pb-4 pt-2">
          <div className="glass-panel flex items-center gap-2 rounded-xl p-3">
            <span className="relative flex h-2 w-2">
              <span className={cn('absolute inline-flex h-full w-full rounded-full opacity-75', activeModel ? 'animate-ping bg-success' : 'bg-white/20')} />
              <span className={cn('relative inline-flex h-2 w-2 rounded-full', activeModel ? 'bg-success' : 'bg-white/20')} />
            </span>
            <div className="text-xs">
              <p className="font-medium text-white/80">
                {activeModel ? `${activeModel.version} Live` : 'No active model'}
              </p>
              <p className="text-white/35">
                {activeModel ? `${(activeModel.accuracy * 100).toFixed(1)}% accuracy` : 'Trigger a retrain to get started'}
              </p>
            </div>
          </div>
        </div>
      </motion.aside>
    </>
  )
}
