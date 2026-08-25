import { useEffect, useRef, useState } from 'react'
import toast from 'react-hot-toast'
import { CreditCard, Coins, Radio } from 'lucide-react'
import PageHeader from '../components/ui/PageHeader'
import GlassCard from '../components/ui/GlassCard'
import VolumeLineChart from '../components/charts/VolumeLineChart'
import FraudDoughnutChart from '../components/charts/FraudDoughnutChart'
import RiskAreaChart from '../components/charts/RiskAreaChart'
import FraudHeatmap from '../components/charts/FraudHeatmap'
import { fraudApi, getAccessToken, getNotificationsWebSocketUrl } from '../lib/api'
import { mapAnalytics } from '../lib/transform'
import { cn } from '../lib/utils'

export default function FraudAnalytics() {
  const [loading, setLoading] = useState(true)
  const [data, setData] = useState(null)
  const [connected, setConnected] = useState(false)
  const refreshTimer = useRef(null)

  function loadAnalytics({ silent = false } = {}) {
    if (!silent) setLoading(true)
    return fraudApi
      .getAnalytics()
      .then(({ data: res }) => {
        const mapped = mapAnalytics(res)
        const currencyTotal = mapped.currencyBreakdown.reduce((sum, c) => sum + c.total, 0)
        mapped.currencyBreakdown = mapped.currencyBreakdown.map((c) => ({
          ...c,
          share: currencyTotal ? Math.round((c.total / currencyTotal) * 100) : 0,
        }))
        setData(mapped)
      })
      .catch(() => !silent && toast.error('Could not load analytics from the backend'))
      .finally(() => !silent && setLoading(false))
  }

  useEffect(() => {
    loadAnalytics()
  }, [])

  // Live updates: every scored transaction is broadcast over the same
  // WebSocket channel Live Monitoring listens on. A fraud-relevant event
  // (is_fraud, or anything the model/rules didn't outright approve) means
  // the heatmap/volume/distribution charts are now stale, so we debounce a
  // real refetch rather than trying to hand-patch every chart's aggregate
  // math on the client for one new data point.
  useEffect(() => {
    let cancelled = false
    let reconnectTimer
    let ws

    function scheduleRefresh() {
      clearTimeout(refreshTimer.current)
      refreshTimer.current = setTimeout(() => loadAnalytics({ silent: true }), 1500)
    }

    function connect() {
      const token = getAccessToken()
      if (!token || cancelled) return
      ws = new WebSocket(getNotificationsWebSocketUrl(token))

      ws.onopen = () => setConnected(true)
      ws.onclose = () => {
        setConnected(false)
        if (!cancelled) reconnectTimer = setTimeout(connect, 3000)
      }
      ws.onerror = () => ws.close()
      ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data)
          if (payload.event === 'transaction_scored' && payload.transaction) {
            scheduleRefresh()
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
      clearTimeout(refreshTimer.current)
      ws?.close()
    }
  }, [])

  if (loading || !data) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-white/10 border-t-primary" />
      </div>
    )
  }

  return (
    <div>
      <PageHeader
        eyebrow="Insights"
        title="Fraud Analytics"
        subtitle="Deep-dive into real decision patterns, merchant risk, and currency exposure."
        actions={
          <span className="flex items-center gap-2 text-xs text-white/40">
            <span className="relative flex h-2 w-2">
              {connected && <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-success opacity-75" />}
              <span className={cn('relative inline-flex h-2 w-2 rounded-full', connected ? 'bg-success' : 'bg-white/30')} />
            </span>
            <Radio size={13} className={connected ? 'text-success' : 'text-white/30'} />
            {connected ? 'Live' : 'Reconnecting\u2026'}
          </span>
        }
      />

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
        <GlassCard className="lg:col-span-2">
          <h3 className="mb-2 font-display text-base font-semibold">Volume vs Flagged Transactions</h3>
          <span className="mb-2 block text-xs text-white/35">Last 24 hours</span>
          <VolumeLineChart data={data.volume} />
        </GlassCard>
        <GlassCard>
          <h3 className="mb-2 font-display text-base font-semibold">Decision Distribution</h3>
          <FraudDoughnutChart data={data.distribution} />
        </GlassCard>
      </div>

      <div className="mt-5 grid grid-cols-1 gap-5 lg:grid-cols-2">
        <GlassCard>
          <h3 className="mb-2 font-display text-base font-semibold">14-Day Risk Trend</h3>
          <RiskAreaChart data={data.trend} />
        </GlassCard>
        <GlassCard>
          <h3 className="mb-4 font-display text-base font-semibold">Fraud Activity Heatmap</h3>
          <FraudHeatmap data={data.heatmap} hours={data.heatmapHours} />
        </GlassCard>
      </div>

      <div className="mt-5 grid grid-cols-1 gap-5 lg:grid-cols-2">
        <GlassCard>
          <h3 className="mb-4 flex items-center gap-2 font-display text-base font-semibold">
            <CreditCard size={16} className="text-primary" /> Highest-Risk Merchants
          </h3>
          {data.topMerchants.length === 0 ? (
            <p className="py-6 text-center text-sm text-white/40">No merchant data yet.</p>
          ) : (
            <div className="space-y-1">
              {data.topMerchants.map((m, i) => (
                <div key={m.name} className="flex items-center justify-between border-b border-white/5 py-3 last:border-0">
                  <div className="flex items-center gap-3">
                    <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-white/5 text-xs font-medium text-white/50">
                      {i + 1}
                    </span>
                    <span className="text-sm text-white/85">{m.name}</span>
                  </div>
                  <div className="flex items-center gap-4">
                    <span className="text-sm text-white/60">{m.flagged} / {m.total} flagged</span>
                    <span className={`text-xs font-medium ${m.flagRate >= 30 ? 'text-danger' : m.flagRate > 0 ? 'text-warning' : 'text-success'}`}>
                      {m.flagRate}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </GlassCard>

        <GlassCard>
          <h3 className="mb-4 flex items-center gap-2 font-display text-base font-semibold">
            <Coins size={16} className="text-accent" /> Volume by Currency
          </h3>
          {data.currencyBreakdown.length === 0 ? (
            <p className="py-6 text-center text-sm text-white/40">No transaction data yet.</p>
          ) : (
            <div className="space-y-4">
              {data.currencyBreakdown.map((c) => (
                <div key={c.currency}>
                  <div className="mb-1.5 flex justify-between text-sm">
                    <span className="text-white/75">{c.currency}</span>
                    <span className="text-white/40">{c.total} txns · {c.flagged} flagged · {c.share}%</span>
                  </div>
                  <div className="h-2 w-full overflow-hidden rounded-full bg-white/10">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-primary to-accent"
                      style={{ width: `${c.share}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </GlassCard>
      </div>
    </div>
  )
}
