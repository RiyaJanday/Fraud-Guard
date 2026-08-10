import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import toast from 'react-hot-toast'
import { Activity, AlertTriangle, CheckCircle2, RefreshCw } from 'lucide-react'
import PageHeader from '../components/ui/PageHeader'
import GlassCard from '../components/ui/GlassCard'
import { fraudApi, getApiErrorMessage } from '../lib/api'
import { cn } from '../lib/utils'

export default function Drift() {
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [report, setReport] = useState(null)

  const load = (isRefresh = false) => {
    if (isRefresh) setRefreshing(true)
    fraudApi
      .getDriftReport()
      .then(({ data }) => setReport(data))
      .catch((err) => toast.error(getApiErrorMessage(err, 'Could not load the drift report')))
      .finally(() => {
        setLoading(false)
        setRefreshing(false)
      })
  }

  useEffect(() => {
    load()
  }, [])

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
        eyebrow="Model Monitoring"
        title="Drift Monitoring"
        subtitle="A real Kolmogorov-Smirnov test comparing today's live traffic against the distribution the model was trained on — not a simulated metric."
      />

      <div className="mb-5 flex justify-end">
        <button
          onClick={() => load(true)}
          disabled={refreshing}
          className="btn-ghost flex items-center gap-2 text-sm disabled:opacity-50"
        >
          <RefreshCw size={14} className={refreshing ? 'animate-spin' : ''} /> Refresh
        </button>
      </div>

      {report?.status === 'insufficient_data' ? (
        <GlassCard hover={false}>
          <div className="flex flex-col items-center gap-3 py-10 text-center">
            <Activity size={28} className="text-white/25" />
            <p className="font-display text-base font-semibold text-white/80">Not enough data yet</p>
            <p className="max-w-md text-sm text-white/45">
              {report.message ||
                `Drift detection needs at least ${report.minimum_required ?? 'a minimum number of'} scored transactions today. Currently: ${report.sample_size}.`}
            </p>
          </div>
        </GlassCard>
      ) : (
        <>
          <div className="mb-5 grid grid-cols-1 gap-5 sm:grid-cols-3">
            <GlassCard>
              <p className="text-xs text-white/40">Overall Verdict</p>
              <div className="mt-2 flex items-center gap-2">
                {report.drift_detected ? (
                  <AlertTriangle size={20} className="text-danger" />
                ) : (
                  <CheckCircle2 size={20} className="text-success" />
                )}
                <span className={cn('font-display text-lg font-semibold', report.drift_detected ? 'text-danger' : 'text-success')}>
                  {report.drift_detected ? 'Drift Detected' : 'No Drift Detected'}
                </span>
              </div>
              <p className="mt-1 text-xs text-white/35">
                {report.drifted_feature_count} of {report.total_feature_count} features drifted
              </p>
            </GlassCard>

            <GlassCard>
              <p className="text-xs text-white/40">Sample Size</p>
              <p className="mt-2 font-display text-2xl font-semibold">{report.sample_size.toLocaleString()}</p>
              <p className="mt-1 text-xs text-white/35">transactions scored today</p>
            </GlassCard>

            <GlassCard>
              <p className="text-xs text-white/40">Drift Ratio</p>
              <p className="mt-2 font-display text-2xl font-semibold">
                {(report.drift_ratio * 100).toFixed(1)}%
              </p>
              <p className="mt-1 text-xs text-white/35">threshold: {(report.threshold * 100).toFixed(0)}%</p>
            </GlassCard>
          </div>

          <GlassCard hover={false}>
            <h3 className="mb-1 font-display text-base font-semibold">Per-Feature KS Test</h3>
            <p className="mb-4 text-xs text-white/35">
              A low p-value (below 0.05) means today's distribution for that feature is statistically
              unlikely to have come from the same distribution as the training set.
            </p>
            <div className="space-y-2">
              {report.features
                .slice()
                .sort((a, b) => a.p_value - b.p_value)
                .map((f, i) => (
                  <motion.div
                    key={f.feature}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.3, delay: i * 0.02 }}
                    className={cn(
                      'flex items-center justify-between rounded-lg border px-3.5 py-2.5 text-sm',
                      f.drifted ? 'border-danger/25 bg-danger/5' : 'border-white/10 bg-white/[0.02]'
                    )}
                  >
                    <span className="font-mono text-white/75">{f.feature}</span>
                    <div className="flex items-center gap-4 text-xs">
                      <span className="text-white/40">KS = {f.ks_statistic.toFixed(4)}</span>
                      <span className="text-white/40">p = {f.p_value.toFixed(4)}</span>
                      <span className={cn('badge text-[10px]', f.drifted ? 'badge-danger' : 'border border-white/10 bg-white/5 text-white/40')}>
                        {f.drifted ? 'Drifted' : 'Stable'}
                      </span>
                    </div>
                  </motion.div>
                ))}
            </div>
          </GlassCard>
        </>
      )}
    </div>
  )
}
