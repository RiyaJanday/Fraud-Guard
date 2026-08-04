import { useEffect, useState } from 'react'
import { Receipt, ShieldAlert, ShieldCheck, Target, Gauge, Download } from 'lucide-react'
import toast from 'react-hot-toast'
import PageHeader from '../components/ui/PageHeader'
import StatCard from '../components/ui/StatCard'
import GlassCard from '../components/ui/GlassCard'
import RiskGauge from '../components/ui/RiskGauge'
import VolumeLineChart from '../components/charts/VolumeLineChart'
import FraudDoughnutChart from '../components/charts/FraudDoughnutChart'
import RiskAreaChart from '../components/charts/RiskAreaChart'
import PerformanceRadarChart from '../components/charts/PerformanceRadarChart'
import FraudHeatmap from '../components/charts/FraudHeatmap'
import RiskTimelineChart from '../components/charts/RiskTimelineChart'
import TransactionTable from '../components/transactions/TransactionTable'
import TransactionDrawer from '../components/transactions/TransactionDrawer'
import AlertsPanel from '../components/dashboard/AlertsPanel'
import NotificationsPanel from '../components/dashboard/NotificationsPanel'
import { fraudApi } from '../lib/api'
import { downloadBlobResponse } from '../lib/utils'
import { mapDashboardStats, mapDashboardCharts, mapAlerts, mapTransactionListItem, mapTransactionDetail } from '../lib/transform'
import { useNotifications } from '../context/NotificationsContext'

const EMPTY_STATS = {
  totalTransactions: 0,
  fraudDetected: 0,
  fraudBlocked: 0,
  detectionAccuracy: 0,
  avgRiskScore: 0,
  deltas: { totalTransactions: 0, fraudDetected: 0, fraudBlocked: 0, detectionAccuracy: 0, avgRiskScore: 0 },
}

export default function Dashboard() {
  const { notifications, unreadCount, markRead, markAllRead } = useNotifications()
  const [selectedId, setSelectedId] = useState(null)
  const [selected, setSelected] = useState(null)
  const [loading, setLoading] = useState(true)
  const [exporting, setExporting] = useState(false)
  const [stats, setStats] = useState(EMPTY_STATS)
  const [charts, setCharts] = useState(null)
  const [alerts, setAlerts] = useState([])
  const [recent, setRecent] = useState([])

  async function handleExportReport() {
    setExporting(true)
    try {
      const response = await fraudApi.exportSummaryPdf()
      downloadBlobResponse(response, 'fraudguard-summary.pdf')
      toast.success('Report downloaded')
    } catch (err) {
      toast.error('Could not generate report')
    } finally {
      setExporting(false)
    }
  }

  useEffect(() => {
    let cancelled = false

    async function load() {
      setLoading(true)
      try {
        const [statsRes, chartsRes, alertsRes, txnRes] = await Promise.all([
          fraudApi.getDashboardStats(),
          fraudApi.getDashboardCharts(),
          fraudApi.getDashboardAlerts(4),
          fraudApi.getTransactions({ page: 1, page_size: 8 }),
        ])
        if (cancelled) return
        setStats(mapDashboardStats(statsRes.data))
        setCharts(mapDashboardCharts(chartsRes.data))
        setAlerts(mapAlerts(alertsRes.data))
        setRecent(txnRes.data.items.map(mapTransactionListItem))
      } catch (err) {
        if (!cancelled) toast.error('Could not load dashboard data from the backend')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    load()
    return () => { cancelled = true }
  }, [])

  useEffect(() => {
    if (!selectedId) {
      setSelected(null)
      return
    }
    let cancelled = false
    fraudApi.getTransaction(selectedId).then(({ data }) => {
      if (!cancelled) setSelected(mapTransactionDetail(data))
    }).catch(() => {
      if (!cancelled) toast.error('Could not load transaction detail')
    })
    return () => { cancelled = true }
  }, [selectedId])

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-white/10 border-t-primary" />
      </div>
    )
  }

  return (
    <div>
      <PageHeader
        eyebrow="Overview"
        title="Fraud Detection Dashboard"
        subtitle="Real-time visibility into transaction risk across your entire payments network."
        actions={
          <button onClick={handleExportReport} disabled={exporting} className="btn-ghost text-sm disabled:opacity-50">
            <Download size={15} /> {exporting ? 'Generating…' : 'Export Report'}
          </button>
        }
      />

      {/* Top statistics */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <StatCard
          label="Total Transactions"
          value={stats.totalTransactions}
          delta={stats.deltas.totalTransactions}
          icon={Receipt}
          iconColor="text-accent"
          delay={0}
        />
        <StatCard
          label="Fraud Detected"
          value={stats.fraudDetected}
          delta={stats.deltas.fraudDetected}
          icon={ShieldAlert}
          iconColor="text-danger"
          delay={0.05}
        />
        <StatCard
          label="Fraud Blocked"
          value={stats.fraudBlocked}
          delta={stats.deltas.fraudBlocked}
          icon={ShieldCheck}
          iconColor="text-success"
          delay={0.1}
        />
        <StatCard
          label="Detection Accuracy"
          value={stats.detectionAccuracy}
          suffix="%"
          decimals={1}
          delta={stats.deltas.detectionAccuracy}
          icon={Target}
          iconColor="text-primary"
          delay={0.15}
        />
        <StatCard
          label="Avg. Risk Score"
          value={stats.avgRiskScore}
          decimals={1}
          delta={stats.deltas.avgRiskScore}
          icon={Gauge}
          iconColor="text-warning"
          delay={0.2}
        />
      </div>

      {/* Charts row 1 */}
      <div className="mt-6 grid grid-cols-1 gap-5 lg:grid-cols-3">
        <GlassCard className="lg:col-span-2" delay={0.05}>
          <div className="mb-2 flex items-center justify-between">
            <h3 className="font-display text-base font-semibold">Transaction Volume</h3>
            <span className="text-xs text-white/35">Last 24 hours</span>
          </div>
          <VolumeLineChart data={charts.volume} />
        </GlassCard>
        <GlassCard delay={0.1}>
          <h3 className="mb-2 font-display text-base font-semibold">Fraud Distribution</h3>
          <FraudDoughnutChart data={charts.distribution} />
        </GlassCard>
      </div>

      {/* Charts row 2 */}
      <div className="mt-5 grid grid-cols-1 gap-5 lg:grid-cols-3">
        <GlassCard delay={0.05}>
          <h3 className="mb-2 font-display text-base font-semibold">Risk Trend</h3>
          <RiskAreaChart data={charts.trend} />
        </GlassCard>
        <GlassCard delay={0.1}>
          <h3 className="mb-2 font-display text-base font-semibold">Model Performance</h3>
          <PerformanceRadarChart data={charts.performance} />
        </GlassCard>
        <GlassCard delay={0.15} className="flex flex-col items-center justify-center">
          <h3 className="mb-1 self-start font-display text-base font-semibold">Live Risk Gauge</h3>
          <RiskGauge value={Math.round(stats.avgRiskScore)} />
        </GlassCard>
      </div>

      {/* Heatmap */}
      <GlassCard className="mt-5" delay={0.05}>
        <h3 className="mb-4 font-display text-base font-semibold">Fraud Heatmap · Activity by Day & Hour</h3>
        <FraudHeatmap data={charts.heatmap} hours={charts.heatmapHours} />
      </GlassCard>

      {/* Transactions + side panels */}
      <div className="mt-5 grid grid-cols-1 gap-5 lg:grid-cols-3">
        <GlassCard className="lg:col-span-2" delay={0.05}>
          <div className="mb-4 flex items-center justify-between">
            <h3 className="font-display text-base font-semibold">Recent Transactions</h3>
          </div>
          {recent.length ? (
            <TransactionTable data={recent} onSelect={(t) => setSelectedId(t.id)} pageSize={5} />
          ) : (
            <p className="py-6 text-center text-sm text-white/40">No transactions scored yet.</p>
          )}
        </GlassCard>
        <div className="space-y-5">
          <AlertsPanel alerts={alerts} />
        </div>
      </div>

      {/* SHAP + timeline + notifications */}
      <div className="mt-5 grid grid-cols-1 gap-5 lg:grid-cols-3">
        <GlassCard delay={0.05}>
          <h3 className="mb-2 font-display text-base font-semibold">Risk Score Timeline</h3>
          <p className="mb-2 text-xs text-white/35">Rolling average across recent transactions</p>
          <RiskTimelineChart data={charts.trend} />
        </GlassCard>
        <GlassCard delay={0.1}>
          <h3 className="mb-3 font-display text-base font-semibold">Model Performance Snapshot</h3>
          <div className="space-y-3">
            {charts.performance.labels.map((label, i) => (
              <div key={label}>
                <div className="flex justify-between text-xs">
                  <span className="text-white/60">{label}</span>
                  <span className="text-success">{charts.performance.values[i]}</span>
                </div>
                <div className="mt-1 h-1.5 w-full rounded-full bg-white/10">
                  <div
                    className="h-full rounded-full bg-primary"
                    style={{ width: `${Math.min(charts.performance.values[i], 100)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </GlassCard>
        <NotificationsPanel
          notifications={notifications}
          unreadCount={unreadCount}
          onMarkRead={markRead}
          onMarkAllRead={markAllRead}
        />
      </div>

      <TransactionDrawer transaction={selected} onClose={() => setSelectedId(null)} />
    </div>
  )
}
