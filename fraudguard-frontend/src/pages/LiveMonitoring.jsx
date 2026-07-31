import { useEffect, useRef, useState } from 'react'
import toast from 'react-hot-toast'
import { motion, AnimatePresence } from 'framer-motion'
import { Activity, Pause, Play, ShieldAlert, ShieldCheck, ShieldQuestion } from 'lucide-react'
import PageHeader from '../components/ui/PageHeader'
import GlassCard from '../components/ui/GlassCard'
import StatusBadge from '../components/transactions/StatusBadge'
import TransactionDrawer from '../components/transactions/TransactionDrawer'
import { randomLiveTransaction, generateTransactions } from '../data/mockData'
import { formatCurrency, formatTime, cn } from '../lib/utils'

const STATUS_ICON = { approved: ShieldCheck, mfa: ShieldQuestion, blocked: ShieldAlert }

export default function LiveMonitoring() {
  const [feed, setFeed] = useState(() => generateTransactions(10))
  const [running, setRunning] = useState(true)
  const [selected, setSelected] = useState(null)
  const intervalRef = useRef(null)

  useEffect(() => {
    if (!running) {
      clearInterval(intervalRef.current)
      return
    }
    intervalRef.current = setInterval(() => {
      const base = randomLiveTransaction()
      const full = { ...generateTransactions(1)[0], ...base }
      setFeed((prev) => [full, ...prev].slice(0, 30))

      if (full.status === 'blocked') {
        toast.custom((t) => (
          <div className={cn('glass-card flex items-start gap-3 border-danger/40 bg-danger/10 p-4 shadow-glow-danger', t.visible ? 'animate-fade-up' : 'opacity-0')}>
            <ShieldAlert size={20} className="mt-0.5 shrink-0 text-danger" />
            <div>
              <p className="text-sm font-semibold text-white">Transaction Blocked</p>
              <p className="text-xs text-white/60">{full.merchant} · {formatCurrency(full.amount)} · Risk {full.risk}</p>
            </div>
          </div>
        ))
      } else if (full.status === 'mfa') {
        toast(`${full.merchant} flagged for step-up verification`, { icon: '🛡️' })
      }
    }, 4500)
    return () => clearInterval(intervalRef.current)
  }, [running])

  return (
    <div>
      <PageHeader
        eyebrow="Real-Time"
        title="Live Monitoring"
        subtitle="Watch transactions being scored by the fraud engine as they happen."
        actions={
          <button onClick={() => setRunning((r) => !r)} className={running ? 'btn-primary text-sm' : 'btn-ghost text-sm'}>
            {running ? <Pause size={15} /> : <Play size={15} />}
            {running ? 'Pause Stream' : 'Resume Stream'}
          </button>
        }
      />

      <div className="mb-5 flex items-center gap-2 text-sm text-white/50">
        <span className="relative flex h-2.5 w-2.5">
          {running && <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-success opacity-75" />}
          <span className={cn('relative inline-flex h-2.5 w-2.5 rounded-full', running ? 'bg-success' : 'bg-white/30')} />
        </span>
        {running ? 'Streaming live transaction data' : 'Stream paused'}
        <Activity size={14} className="ml-2 text-white/30" />
      </div>

      <GlassCard hover={false} className="p-0 overflow-hidden">
        <div className="max-h-[640px] overflow-y-auto">
          <AnimatePresence initial={false}>
            {feed.map((t) => {
              const Icon = STATUS_ICON[t.status]
              return (
                <motion.div
                  key={t.id}
                  layout
                  initial={{ opacity: 0, x: -20, height: 0 }}
                  animate={{ opacity: 1, x: 0, height: 'auto' }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.35 }}
                  onClick={() => setSelected(t)}
                  className="flex cursor-pointer items-center gap-4 border-b border-white/5 px-5 py-3.5 transition hover:bg-white/[0.03]"
                >
                  <div
                    className={cn(
                      'flex h-9 w-9 shrink-0 items-center justify-center rounded-xl',
                      t.status === 'blocked' && 'bg-danger/10 text-danger',
                      t.status === 'mfa' && 'bg-warning/10 text-warning',
                      t.status === 'approved' && 'bg-success/10 text-success'
                    )}
                  >
                    <Icon size={16} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-white/90">{t.merchant}</p>
                    <p className="font-mono text-[11px] text-white/30">{t.id}</p>
                  </div>
                  <div className="hidden text-right sm:block">
                    <p className="text-sm text-white/70">{formatCurrency(t.amount)}</p>
                    <p className="text-[11px] text-white/30">{formatTime(t.timestamp)}</p>
                  </div>
                  <div className="hidden w-20 md:block">
                    <div className="h-1.5 w-full overflow-hidden rounded-full bg-white/10">
                      <div
                        className={cn(
                          'h-full rounded-full',
                          t.risk >= 75 ? 'bg-danger' : t.risk >= 40 ? 'bg-warning' : 'bg-success'
                        )}
                        style={{ width: `${t.risk}%` }}
                      />
                    </div>
                  </div>
                  <StatusBadge status={t.status} />
                </motion.div>
              )
            })}
          </AnimatePresence>
        </div>
      </GlassCard>

      <TransactionDrawer transaction={selected} onClose={() => setSelected(null)} />
    </div>
  )
}
