import { useMemo } from 'react'
import { TrendingDown, TrendingUp, Globe2, CreditCard } from 'lucide-react'
import PageHeader from '../components/ui/PageHeader'
import GlassCard from '../components/ui/GlassCard'
import VolumeLineChart from '../components/charts/VolumeLineChart'
import FraudDoughnutChart from '../components/charts/FraudDoughnutChart'
import RiskAreaChart from '../components/charts/RiskAreaChart'
import FraudHeatmap from '../components/charts/FraudHeatmap'
import {
  getVolumeSeries, getFraudDistribution, getRiskTrend, getHeatmapData,
} from '../data/mockData'

const TOP_MERCHANTS = [
  { name: 'Amazon.in', fraud: 214, trend: -4.2 },
  { name: 'Steam', fraud: 187, trend: 12.1 },
  { name: 'PayPal Transfer', fraud: 165, trend: 6.4 },
  { name: 'Dubai Duty Free', fraud: 142, trend: 3.8 },
  { name: 'Flipkart', fraud: 98, trend: -8.9 },
]

const TOP_GEOS = [
  { name: 'Lagos, NG', share: 22 },
  { name: 'Moscow, RU', share: 18 },
  { name: 'Jakarta, ID', share: 15 },
  { name: 'São Paulo, BR', share: 12 },
  { name: 'Dubai, AE', share: 9 },
]

export default function FraudAnalytics() {
  const volume = useMemo(() => getVolumeSeries(), [])
  const distribution = useMemo(() => getFraudDistribution(), [])
  const trend = useMemo(() => getRiskTrend(), [])
  const heatmap = useMemo(() => getHeatmapData(), [])

  return (
    <div>
      <PageHeader
        eyebrow="Insights"
        title="Fraud Analytics"
        subtitle="Deep-dive into fraud patterns, merchant risk and geographic exposure."
      />

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
        <GlassCard className="lg:col-span-2">
          <h3 className="mb-2 font-display text-base font-semibold">Volume vs Flagged Transactions</h3>
          <VolumeLineChart data={volume} />
        </GlassCard>
        <GlassCard>
          <h3 className="mb-2 font-display text-base font-semibold">Fraud Type Breakdown</h3>
          <FraudDoughnutChart data={distribution} />
        </GlassCard>
      </div>

      <div className="mt-5 grid grid-cols-1 gap-5 lg:grid-cols-2">
        <GlassCard>
          <h3 className="mb-2 font-display text-base font-semibold">14-Day Risk Trend</h3>
          <RiskAreaChart data={trend} />
        </GlassCard>
        <GlassCard>
          <h3 className="mb-4 font-display text-base font-semibold">Activity Heatmap</h3>
          <FraudHeatmap data={heatmap} />
        </GlassCard>
      </div>

      <div className="mt-5 grid grid-cols-1 gap-5 lg:grid-cols-2">
        <GlassCard>
          <h3 className="mb-4 flex items-center gap-2 font-display text-base font-semibold">
            <CreditCard size={16} className="text-primary" /> Highest-Risk Merchants
          </h3>
          <div className="space-y-1">
            {TOP_MERCHANTS.map((m, i) => (
              <div key={m.name} className="flex items-center justify-between border-b border-white/5 py-3 last:border-0">
                <div className="flex items-center gap-3">
                  <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-white/5 text-xs font-medium text-white/50">
                    {i + 1}
                  </span>
                  <span className="text-sm text-white/85">{m.name}</span>
                </div>
                <div className="flex items-center gap-4">
                  <span className="text-sm text-white/60">{m.fraud} flags</span>
                  <span className={`flex items-center gap-1 text-xs font-medium ${m.trend >= 0 ? 'text-danger' : 'text-success'}`}>
                    {m.trend >= 0 ? <TrendingUp size={13} /> : <TrendingDown size={13} />}
                    {Math.abs(m.trend)}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        </GlassCard>

        <GlassCard>
          <h3 className="mb-4 flex items-center gap-2 font-display text-base font-semibold">
            <Globe2 size={16} className="text-accent" /> Fraud by Geography
          </h3>
          <div className="space-y-4">
            {TOP_GEOS.map((g) => (
              <div key={g.name}>
                <div className="mb-1.5 flex justify-between text-sm">
                  <span className="text-white/75">{g.name}</span>
                  <span className="text-white/40">{g.share}%</span>
                </div>
                <div className="h-2 w-full overflow-hidden rounded-full bg-white/10">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-primary to-accent"
                    style={{ width: `${g.share * 3}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </GlassCard>
      </div>
    </div>
  )
}
