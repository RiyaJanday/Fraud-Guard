import { useEffect, useRef, useState } from 'react'
import toast from 'react-hot-toast'
import { BrainCircuit, RefreshCw, Database, Clock, History } from 'lucide-react'
import PageHeader from '../components/ui/PageHeader'
import GlassCard from '../components/ui/GlassCard'
import { fraudApi, getApiErrorMessage } from '../lib/api'
import { cn, formatDateTime } from '../lib/utils'
import { useAuth } from '../context/AuthContext'

const METRIC_FIELDS = [
  { key: 'accuracy', label: 'Accuracy' },
  { key: 'precision', label: 'Precision' },
  { key: 'recall', label: 'Recall' },
  { key: 'f1_score', label: 'F1 Score' },
  { key: 'roc_auc', label: 'ROC-AUC' },
  { key: 'pr_auc', label: 'PR-AUC' },
]

const STATUS_META = {
  active: { label: 'Active', className: 'badge-success' },
  training: { label: 'Training', className: 'badge-warning' },
  inactive: { label: 'Inactive', className: 'border border-white/10 bg-white/5 text-white/40' },
  archived: { label: 'Archived', className: 'border border-white/10 bg-white/5 text-white/40' },
}

function pct(value) {
  return value == null ? '—' : `${(value * 100).toFixed(2)}%`
}

export default function ModelRegistry() {
  const { user } = useAuth()
  const isAdmin = user?.role === 'admin'

  const [status, setStatus] = useState(null)
  const [versions, setVersions] = useState([])
  const [loading, setLoading] = useState(true)
  const [retraining, setRetraining] = useState(false)
  const pollRef = useRef(null)

  function loadAll() {
    return Promise.all([fraudApi.getModelStatus(), fraudApi.getModelVersions()])
      .then(([statusRes, versionsRes]) => {
        setStatus(statusRes.data)
        setVersions(versionsRes.data)
        setRetraining(statusRes.data.training_in_progress)
        return statusRes.data
      })
      .catch((err) => {
        toast.error(getApiErrorMessage(err, 'Could not load model registry'))
        return null
      })
  }

  useEffect(() => {
    loadAll().finally(() => setLoading(false))
    return () => clearInterval(pollRef.current)
  }, [])

  useEffect(() => {
    if (retraining && !pollRef.current) {
      pollRef.current = setInterval(async () => {
        const data = await loadAll()
        if (data && !data.training_in_progress) {
          clearInterval(pollRef.current)
          pollRef.current = null
          toast.success(data.last_training_error ? 'Retraining finished with an error' : 'New model version is now active')
        }
      }, 4000)
    }
    if (!retraining && pollRef.current) {
      clearInterval(pollRef.current)
      pollRef.current = null
    }
  }, [retraining])

  async function handleRetrain() {
    try {
      const { data } = await fraudApi.triggerRetrain()
      if (data.training_in_progress) {
        setRetraining(true)
        toast.success(data.message)
      } else {
        toast(data.message)
      }
    } catch (err) {
      toast.error(getApiErrorMessage(err, 'Could not start retraining'))
    }
  }

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-white/10 border-t-primary" />
      </div>
    )
  }

  const active = status?.active_model

  return (
    <div>
      <PageHeader
        eyebrow="ML Operations"
        title="Model Registry"
        subtitle="The active model powering live inference, plus the full history of every version trained on this dataset."
        actions={
          isAdmin && (
            <button
              onClick={handleRetrain}
              disabled={retraining}
              className="btn-primary text-sm disabled:opacity-50"
            >
              <RefreshCw size={15} className={cn(retraining && 'animate-spin')} />
              {retraining ? 'Training…' : 'Retrain Model'}
            </button>
          )
        }
      />

      {status?.last_training_error && !retraining && (
        <div className="mb-6 rounded-xl border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-danger">
          Last training run failed: {status.last_training_error}
        </div>
      )}

      <GlassCard hover={false} className="mb-6">
        {!active ? (
          <div className="flex flex-col items-center gap-3 py-10 text-center">
            <BrainCircuit size={28} className="text-white/25" />
            <p className="text-sm text-white/40">No active model registered yet — trigger a training run to get started.</p>
          </div>
        ) : (
          <>
            <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-secondary shadow-glow">
                  <BrainCircuit size={18} className="text-white" />
                </div>
                <div>
                  <p className="font-display text-base font-semibold text-white">
                    {active.version} <span className="text-white/40">·</span> {active.algorithm}
                  </p>
                  <p className="flex items-center gap-1.5 text-xs text-white/40">
                    <Clock size={12} /> Trained {formatDateTime(active.training_date)}
                  </p>
                </div>
              </div>
              <span className="badge badge-success text-[10px]">Active — Live Inference</span>
            </div>

            <div className="mb-5 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
              {METRIC_FIELDS.map((m) => (
                <div key={m.key} className="rounded-xl border border-white/10 bg-white/[0.03] p-3 text-center">
                  <p className="text-lg font-semibold text-white">{pct(active[m.key])}</p>
                  <p className="mt-0.5 text-[11px] text-white/40">{m.label}</p>
                </div>
              ))}
            </div>

            <div className="flex items-center gap-1.5 text-xs text-white/35">
              <Database size={12} />
              {active.dataset_row_count?.toLocaleString('en-IN')} rows from the training dataset
            </div>
          </>
        )}
      </GlassCard>

      <GlassCard hover={false}>
        <h3 className="mb-4 flex items-center gap-2 font-display text-base font-semibold">
          <History size={16} className="text-primary" /> Version History
        </h3>
        {versions.length === 0 ? (
          <p className="py-6 text-center text-sm text-white/40">No trained versions yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/10 text-left text-xs uppercase tracking-wide text-white/35">
                  <th className="pb-3 pr-4 font-medium">Version</th>
                  <th className="pb-3 pr-4 font-medium">Algorithm</th>
                  <th className="pb-3 pr-4 font-medium">Accuracy</th>
                  <th className="pb-3 pr-4 font-medium">Recall</th>
                  <th className="pb-3 pr-4 font-medium">F1</th>
                  <th className="pb-3 pr-4 font-medium">Trained</th>
                  <th className="pb-3 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {versions.map((v) => (
                  <tr key={v.id} className="border-b border-white/5 last:border-0">
                    <td className="py-3 pr-4 font-mono text-xs text-white/80">{v.version}</td>
                    <td className="py-3 pr-4 capitalize text-white/60">{v.algorithm.replace('_', ' ')}</td>
                    <td className="py-3 pr-4 text-white/70">{pct(v.accuracy)}</td>
                    <td className="py-3 pr-4 text-white/70">{pct(v.recall)}</td>
                    <td className="py-3 pr-4 text-white/70">{pct(v.f1_score)}</td>
                    <td className="py-3 pr-4 text-xs text-white/40">{v.training_date ? formatDateTime(v.training_date) : '—'}</td>
                    <td className="py-3">
                      <span className={cn('badge text-[10px]', STATUS_META[v.status]?.className)}>
                        {STATUS_META[v.status]?.label || v.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </GlassCard>
    </div>
  )
}
