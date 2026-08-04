import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { CreditCard, Coins } from 'lucide-react'
import PageHeader from '../components/ui/PageHeader'
import GlassCard from '../components/ui/GlassCard'
import VolumeLineChart from '../components/charts/VolumeLineChart'
import FraudDoughnutChart from '../components/charts/FraudDoughnutChart'
import RiskAreaChart from '../components/charts/RiskAreaChart'
import FraudHeatmap from '../components/charts/FraudHeatmap'
import { fraudApi } from '../lib/api'
import { mapAnalytics } from '../lib/transform'

export default function FraudAnalytics() {
  const [loading, setLoading] = useState(true)
  const [data, setData] = useState(null)

  useEffect(() => {
    let cancelled = false
    fraudApi
      .getAnalytics()
      .then(({ data: res }) => {
        if (cancelled) return
        const mapped = mapAnalytics(res)
        const currencyTotal = mapped.currencyBreakdown.reduce((sum, c) => sum + c.total, 0)
        mapped.currencyBreakdown = mapped.currencyBreakdown.map((c) => ({
          ...c,
          share: currencyTotal ? Math.round((c.total / currencyTotal) * 100) : 0,
        }))
        setData(mapped)
      })
      .catch(() => !cancelled && toast.error('Could not load analytics from the backend'))
      .finally(() => !cancelled && setLoading(false))
    return () => { cancelled = true }
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
