import { useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import { BrainCircuit, Sparkles } from 'lucide-react'
import PageHeader from '../components/ui/PageHeader'
import GlassCard from '../components/ui/GlassCard'
import PerformanceRadarChart from '../components/charts/PerformanceRadarChart'
import { TRANSACTIONS, getModelPerformance, SHAP_FEATURE_POOL } from '../data/mockData'
import { formatCurrency, riskLevel } from '../lib/utils'

const GLOBAL_IMPORTANCE = SHAP_FEATURE_POOL.map((f, i) => ({
  ...f,
  importance: +(0.28 - i * 0.022).toFixed(3),
}))

const RISK_TEXT_CLASS = { danger: 'text-danger', warning: 'text-warning', success: 'text-success' }

export default function Explainability() {
  const performance = useMemo(() => getModelPerformance(), [])
  const [selectedId, setSelectedId] = useState(TRANSACTIONS[0].id)
  const txn = TRANSACTIONS.find((t) => t.id === selectedId) || TRANSACTIONS[0]
  const level = riskLevel(txn.risk)

  return (
    <div>
      <PageHeader
        eyebrow="Model Interpretability"
        title="Explainability (SHAP)"
        subtitle="Understand exactly why the model made each fraud decision — no black boxes."
      />

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
        <GlassCard className="lg:col-span-2">
          <h3 className="mb-4 flex items-center gap-2 font-display text-base font-semibold">
            <BrainCircuit size={17} className="text-primary" /> Global Feature Importance
          </h3>
          <div className="space-y-3.5">
            {GLOBAL_IMPORTANCE.map((f, i) => (
              <div key={f.key}>
                <div className="mb-1 flex items-center justify-between text-sm">
                  <span className="text-white/75">{f.label}</span>
                  <span className="text-white/40">{f.importance}</span>
                </div>
                <div className="h-2 w-full overflow-hidden rounded-full bg-white/10">
                  <motion.div
                    initial={{ width: 0 }}
                    whileInView={{ width: `${f.importance * 320}%` }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.7, delay: i * 0.05 }}
                    className="h-full rounded-full bg-gradient-to-r from-primary to-accent"
                  />
                </div>
              </div>
            ))}
          </div>
        </GlassCard>

        <GlassCard>
          <h3 className="mb-2 font-display text-base font-semibold">Model Performance</h3>
          <PerformanceRadarChart data={performance} />
        </GlassCard>
      </div>

      <GlassCard className="mt-5">
        <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <h3 className="flex items-center gap-2 font-display text-base font-semibold">
            <Sparkles size={17} className="text-accent" /> Per-Transaction Explanation
          </h3>
          <select
            value={selectedId}
            onChange={(e) => setSelectedId(e.target.value)}
            className="input-glass max-w-xs"
          >
            {TRANSACTIONS.slice(0, 20).map((t) => (
              <option key={t.id} value={t.id} className="bg-bg-soft">
                {t.id} · {t.merchant}
              </option>
            ))}
          </select>
        </div>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <div>
            <div className="mb-4 flex items-center justify-between rounded-xl border border-white/10 bg-white/[0.02] p-4">
              <div>
                <p className="text-xs text-white/40">Transaction</p>
                <p className="font-medium">{txn.merchant} · {formatCurrency(txn.amount)}</p>
              </div>
              <div className="text-right">
                <p className="text-xs text-white/40">Risk Score</p>
                <p className={`font-display text-xl font-semibold ${RISK_TEXT_CLASS[level.color]}`}>
                  {txn.risk}
                </p>
              </div>
            </div>
            <p className="text-sm leading-relaxed text-white/60">
              The model evaluated {txn.shap.length} key signals for this transaction. Features pushing the score
              toward fraud are shown in red; features supporting legitimacy are shown in green. The magnitude of
              each bar reflects that feature's contribution to the final probability.
            </p>
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
                      animate={{ width: `${Math.min(Math.abs(f.impact) * 220, 100)}%` }}
                      transition={{ duration: 0.6 }}
                      className={`h-full rounded-full ${positive ? 'bg-danger' : 'bg-success'}`}
                    />
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </GlassCard>
    </div>
  )
}
