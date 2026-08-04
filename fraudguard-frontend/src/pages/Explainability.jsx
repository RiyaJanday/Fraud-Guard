import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import toast from 'react-hot-toast'
import { BrainCircuit, Sparkles, Calendar, Database } from 'lucide-react'
import PageHeader from '../components/ui/PageHeader'
import GlassCard from '../components/ui/GlassCard'
import PerformanceRadarChart from '../components/charts/PerformanceRadarChart'
import { fraudApi } from '../lib/api'
import { mapExplainability } from '../lib/transform'
import { formatCurrency, formatDateTime, riskLevel } from '../lib/utils'

const RISK_TEXT_CLASS = { danger: 'text-danger', warning: 'text-warning', success: 'text-success' }
const DECISION_LABEL = { approve: 'Approved', mfa_required: 'MFA Required', blocked: 'Blocked' }

export default function Explainability() {
  const [loading, setLoading] = useState(true)
  const [data, setData] = useState(null)
  const [selectedId, setSelectedId] = useState(null)

  useEffect(() => {
    let cancelled = false
    fraudApi
      .getExplainability()
      .then(({ data: res }) => {
        if (cancelled) return
        const mapped = mapExplainability(res)
        setData(mapped)
        if (mapped.recentExplanations.length) setSelectedId(mapped.recentExplanations[0].id)
      })
      .catch(() => !cancelled && toast.error('Could not load explainability data from the backend'))
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

  const txn = data.recentExplanations.find((t) => t.id === selectedId) || data.recentExplanations[0]
  const level = txn ? riskLevel(txn.risk) : null
  const maxImportance = Math.max(...data.globalImportance.map((f) => f.importance), 0.01)

  return (
    <div>
      <PageHeader
        eyebrow="Model Interpretability"
        title="Explainability (SHAP)"
        subtitle="Real model card and SHAP output from your actual scored transactions — no black boxes, no fabricated numbers."
      />

      {data.model && (
        <GlassCard className="mb-5">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="text-xs text-white/40">Active Model</p>
              <p className="font-display text-lg font-semibold text-white">
                {data.model.version} <span className="text-sm font-normal text-white/40">({data.model.algorithm})</span>
              </p>
            </div>
            <div className="flex flex-wrap gap-5 text-xs text-white/50">
              <span className="flex items-center gap-1.5"><Calendar size={13} /> Trained {data.model.training_date ? formatDateTime(data.model.training_date) : '—'}</span>
              <span className="flex items-center gap-1.5"><Database size={13} /> {data.model.dataset_name}{data.model.dataset_row_count ? ` · ${data.model.dataset_row_count.toLocaleString()} rows` : ''}</span>
            </div>
          </div>
          {data.model.confusion_matrix && (
            <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
              {[
                { label: 'True Positives', value: data.model.confusion_matrix.tp, colorClass: 'text-success' },
                { label: 'False Positives', value: data.model.confusion_matrix.fp, colorClass: 'text-warning' },
                { label: 'True Negatives', value: data.model.confusion_matrix.tn, colorClass: 'text-success' },
                { label: 'False Negatives', value: data.model.confusion_matrix.fn, colorClass: 'text-danger' },
              ].map(({ label, value, colorClass }) => (
                <div key={label} className="rounded-xl border border-white/10 bg-white/[0.02] p-3">
                  <p className="text-[11px] text-white/40">{label}</p>
                  <p className={`font-display text-lg font-semibold ${colorClass}`}>{value.toLocaleString()}</p>
                </div>
              ))}
            </div>
          )}
        </GlassCard>
      )}

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
        <GlassCard className="lg:col-span-2">
          <h3 className="mb-1 flex items-center gap-2 font-display text-base font-semibold">
            <BrainCircuit size={17} className="text-primary" /> Global Feature Importance
          </h3>
          <p className="mb-4 text-xs text-white/35">
            Averaged from real SHAP output across the last {data.sampleSize} scored transactions.
          </p>
          {data.globalImportance.length === 0 ? (
            <p className="py-6 text-center text-sm text-white/40">Not enough scored transactions yet.</p>
          ) : (
            <div className="space-y-3.5">
              {data.globalImportance.map((f, i) => (
                <div key={f.key}>
                  <div className="mb-1 flex items-center justify-between text-sm">
                    <span className="text-white/75">{f.label}</span>
                    <span className="text-white/40">{f.importance} · seen {f.sampleCount}×</span>
                  </div>
                  <div className="h-2 w-full overflow-hidden rounded-full bg-white/10">
                    <motion.div
                      initial={{ width: 0 }}
                      whileInView={{ width: `${(f.importance / maxImportance) * 100}%` }}
                      viewport={{ once: true }}
                      transition={{ duration: 0.7, delay: i * 0.05 }}
                      className="h-full rounded-full bg-gradient-to-r from-primary to-accent"
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </GlassCard>

        <GlassCard>
          <h3 className="mb-2 font-display text-base font-semibold">Model Performance</h3>
          <PerformanceRadarChart data={data.performance} />
        </GlassCard>
      </div>

      <GlassCard className="mt-5">
        <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <h3 className="flex items-center gap-2 font-display text-base font-semibold">
            <Sparkles size={17} className="text-accent" /> Per-Transaction Explanation
          </h3>
          {data.recentExplanations.length > 0 && (
            <select
              value={selectedId}
              onChange={(e) => setSelectedId(e.target.value)}
              className="input-glass max-w-xs"
            >
              {data.recentExplanations.map((t) => (
                <option key={t.id} value={t.id} className="bg-bg-soft">
                  {t.merchant} · {DECISION_LABEL[t.decision]}
                </option>
              ))}
            </select>
          )}
        </div>

        {!txn ? (
          <p className="py-8 text-center text-sm text-white/40">
            No flagged transactions yet — this fills in once a transaction is scored MFA-required or blocked.
          </p>
        ) : (
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <div>
              <div className="mb-4 flex items-center justify-between rounded-xl border border-white/10 bg-white/[0.02] p-4">
                <div>
                  <p className="text-xs text-white/40">Transaction</p>
                  <p className="font-medium">{txn.merchant} · {formatCurrency(txn.amount, txn.currency)}</p>
                </div>
                <div className="text-right">
                  <p className="text-xs text-white/40">Risk Score</p>
                  <p className={`font-display text-xl font-semibold ${RISK_TEXT_CLASS[level.color]}`}>
                    {txn.risk}
                  </p>
                </div>
              </div>
              <p className="text-sm leading-relaxed text-white/60">{txn.explanationText}</p>
            </div>
            <div className="space-y-3">
              {txn.shap.map((f) => {
                const positive = f.impact >= 0
                return (
                  <div key={f.key}>
                    <div className="flex justify-between text-xs">
                      <span className="text-white/70">{f.label}</span>
                      <span className={positive ? 'text-danger' : 'text-success'}>
                        {positive ? '+' : ''}{f.impact}
                      </span>
                    </div>
                    <div className="mt-1 h-2 w-full overflow-hidden rounded-full bg-white/10">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${Math.min(Math.abs(f.impact) * 12, 100)}%` }}
                        transition={{ duration: 0.6 }}
                        className={`h-full rounded-full ${positive ? 'bg-danger' : 'bg-success'}`}
                      />
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}
      </GlassCard>
    </div>
  )
}
