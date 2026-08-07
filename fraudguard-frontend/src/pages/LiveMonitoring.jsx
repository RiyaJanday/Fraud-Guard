import { useEffect, useRef, useState } from 'react'
import toast from 'react-hot-toast'
import { motion, AnimatePresence } from 'framer-motion'
import { Activity, Pause, Play, ShieldAlert, ShieldCheck, ShieldQuestion } from 'lucide-react'
import PageHeader from '../components/ui/PageHeader'
import GlassCard from '../components/ui/GlassCard'
import StatusBadge from '../components/transactions/StatusBadge'
import TransactionDrawer from '../components/transactions/TransactionDrawer'
import { fraudApi, getAccessToken, getNotificationsWebSocketUrl } from '../lib/api'
import { mapTransactionListItem, mapTransactionDetail } from '../lib/transform'
import { formatCurrency, formatTime, cn } from '../lib/utils'

const STATUS_ICON = { approved: ShieldCheck, mfa: ShieldQuestion, blocked: ShieldAlert }
const DECISION_TO_STATUS = { approve: 'approved', mfa_required: 'mfa', blocked: 'blocked' }

export default function LiveMonitoring() {
  const [feed, setFeed] = useState([])
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState(true)
  const [connected, setConnected] = useState(false)
  const [selectedId, setSelectedId] = useState(null)
  const [selected, setSelected] = useState(null)
  const runningRef = useRef(running)
  const wsRef = useRef(null)

  useEffect(() => { runningRef.current = running }, [running])

  // Seed the feed with real recent transactions so the page isn't empty on
  // first load — live events then prepend on top of this as they arrive.
  useEffect(() => {
    fraudApi
      .getTransactions({ page: 1, page_size: 15 })
      .then(({ data }) => setFeed(data.items.map(mapTransactionListItem)))
      .catch(() => toast.error('Could not load recent transactions'))
      .finally(() => setLoading(false))
  }, [])

  // Dedicated WebSocket connection for this page's live feed — the SAME
  // channel notifications use (every "transaction_scored" broadcast from
  // transaction_service.py reaches every connected client), just consumed
  // here for a different event type than NotificationsContext listens for.
  useEffect(() => {
    let cancelled = false
    let reconnectTimer

    function connect() {
      const token = getAccessToken()
      if (!token || cancelled) return
      const ws = new WebSocket(getNotificationsWebSocketUrl(token))
      wsRef.current = ws

      ws.onopen = () => setConnected(true)
      ws.onclose = () => {
        setConnected(false)
        if (!cancelled) reconnectTimer = setTimeout(connect, 3000)
      }
      ws.onerror = () => ws.close()
      ws.onmessage = (event) => {
        if (!runningRef.current) return
        try {
          const payload = JSON.parse(event.data)
          if (payload.event === 'transaction_scored' && payload.transaction) {
            const t = payload.transaction
            const mapped = {
              id: t.id,
              merchant: t.merchant || 'Unknown Merchant',
              amount: t.amount,
              currency: t.currency,
              timestamp: t.created_at,
              risk: Math.round(t.risk_score),
              status: DECISION_TO_STATUS[t.decision] || 'approved',
              customer: '—',
            }
            setFeed((prev) => [mapped, ...prev].slice(0, 40))

            if (mapped.status === 'blocked') {
              toast.custom((tst) => (
                <div className={cn('glass-card flex items-start gap-3 border-danger/40 bg-danger/10 p-4 shadow-glow-danger', tst.visible ? 'animate-fade-up' : 'opacity-0')}>
                  <ShieldAlert size={20} className="mt-0.5 shrink-0 text-danger" />
                  <div>
                    <p className="text-sm font-semibold text-white">Transaction Blocked</p>
                    <p className="text-xs text-white/60">{mapped.merchant} · {formatCurrency(mapped.amount, mapped.currency)} · Risk {mapped.risk}</p>
                  </div>
                </div>
              ))
            } else if (mapped.status === 'mfa') {
              toast(`${mapped.merchant} flagged for step-up verification`, { icon: '🛡️' })
            }
          }
        } catch {
          // ignore malformed frames
        }
      }
    }

    connect()
    return () => {
      cancelled = true
      clearTimeout(reconnectTimer)
      wsRef.current?.close()
    }
  }, [])

  useEffect(() => {
    if (!selectedId) { setSelected(null); return }
    let cancelled = false
    fraudApi.getTransaction(selectedId)
      .then(({ data }) => !cancelled && setSelected(mapTransactionDetail(data)))
      .catch(() => !cancelled && toast.error('Could not load transaction detail'))
    return () => { cancelled = true }
  }, [selectedId])

  return (
    <div>
      <PageHeader
        eyebrow="Real-Time"
        title="Live Monitoring"
        subtitle="Watch real transactions being scored by the fraud engine as they happen."
        actions={
          <button onClick={() => setRunning((r) => !r)} className={running ? 'btn-primary text-sm' : 'btn-ghost text-sm'}>
            {running ? <Pause size={15} /> : <Play size={15} />}
            {running ? 'Pause Stream' : 'Resume Stream'}
          </button>
        }
      />

      <div className="mb-5 flex items-center gap-2 text-sm text-white/50">
        <span className="relative flex h-2.5 w-2.5">
          {running && connected && <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-success opacity-75" />}
          <span className={cn('relative inline-flex h-2.5 w-2.5 rounded-full', running && connected ? 'bg-success' : 'bg-white/30')} />
        </span>
        {!connected ? 'Reconnecting…' : running ? 'Streaming live transaction data' : 'Stream paused'}
        <Activity size={14} className="ml-2 text-white/30" />
      </div>

      <GlassCard hover={false} className="p-0 overflow-hidden">
        {loading ? (
          <div className="flex justify-center py-10">
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-white/10 border-t-primary" />
          </div>
        ) : feed.length === 0 ? (
          <p className="py-10 text-center text-sm text-white/40">No transactions scored yet.</p>
        ) : (
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
                    onClick={() => setSelectedId(t.id)}
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
                      <p className="font-mono text-[11px] text-white/30">{t.id.slice(0, 8)}…</p>
                    </div>
                    <div className="hidden text-right sm:block">
                      <p className="text-sm text-white/70">{formatCurrency(t.amount, t.currency)}</p>
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
        )}
      </GlassCard>

      <TransactionDrawer transaction={selected} onClose={() => setSelectedId(null)} />
    </div>
  )
}
