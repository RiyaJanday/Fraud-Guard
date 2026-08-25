import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import {
  Inbox, ChevronLeft, ChevronRight, ShieldAlert, UserCheck, X,
  CheckCircle2, XCircle, Loader2, Sliders,
} from 'lucide-react'
import PageHeader from '../components/ui/PageHeader'
import GlassCard from '../components/ui/GlassCard'
import { fraudApi, getApiErrorMessage } from '../lib/api'
import { formatCurrency, formatDateTime, cn, riskLevel } from '../lib/utils'
import { useAuth } from '../context/AuthContext'

const STATUS_TABS = [
  { id: 'pending', label: 'Pending' },
  { id: 'in_review', label: 'In Review' },
  { id: 'resolved', label: 'Resolved' },
]

const ORIGIN_LABEL = { blocked: 'Auto-Blocked', mfa_required: 'MFA Required', approve: 'Approved' }

export default function ReviewQueue() {
  const { user } = useAuth()
  const canAct = user?.role === 'admin' || user?.role === 'analyst'

  const [status, setStatus] = useState('pending')
  const [page, setPage] = useState(1)
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [selectedId, setSelectedId] = useState(null)
  const [detail, setDetail] = useState(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [actingId, setActingId] = useState(null)

  function load() {
    setLoading(true)
    fraudApi
      .listReviewQueue({ page, page_size: 15, status })
      .then(({ data: res }) => setData(res))
      .catch((err) => toast.error(getApiErrorMessage(err, 'Could not load the review queue')))
      .finally(() => setLoading(false))
  }

  useEffect(load, [page, status]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!selectedId) {
      setDetail(null)
      return
    }
    let cancelled = false
    setDetailLoading(true)
    fraudApi
      .getReview(selectedId)
      .then(({ data: res }) => !cancelled && setDetail(res))
      .catch((err) => !cancelled && toast.error(getApiErrorMessage(err, 'Could not load review detail')))
      .finally(() => !cancelled && setDetailLoading(false))
    return () => { cancelled = true }
  }, [selectedId])

  async function handleClaim(id) {
    setActingId(id)
    try {
      await fraudApi.claimReview(id)
      toast.success('Claimed — now assigned to you')
      load()
      if (selectedId === id) fraudApi.getReview(id).then(({ data: res }) => setDetail(res))
    } catch (err) {
      toast.error(getApiErrorMessage(err, 'Could not claim this review'))
    } finally {
      setActingId(null)
    }
  }

  async function handleResolve(id, decision) {
    setActingId(id)
    try {
      await fraudApi.resolveReview(id, { decision, notes: detail?.notes || undefined })
      toast.success(decision === 'fraud' ? 'Marked as confirmed fraud' : 'Marked as legitimate')
      setSelectedId(null)
      load()
    } catch (err) {
      toast.error(getApiErrorMessage(err, 'Could not resolve this review'))
    } finally {
      setActingId(null)
    }
  }

  return (
    <div>
      <PageHeader
        eyebrow="Investigate"
        title="Review Queue"
        subtitle="Transactions the model flagged as high-risk, waiting on an analyst's fraud / legitimate call — the ground truth that feeds future retraining."
      />

      <div className="mb-5 flex items-center gap-2">
        {STATUS_TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => { setStatus(t.id); setPage(1) }}
            className={cn(
              'rounded-lg px-3.5 py-1.5 text-xs font-medium transition',
              status === t.id
                ? 'border border-primary/40 bg-primary/20 text-white'
                : 'border border-white/10 bg-white/[0.02] text-white/50 hover:text-white'
            )}
          >
            {t.label}
          </button>
        ))}
      </div>

      <GlassCard hover={false}>
        {loading ? (
          <p className="py-10 text-center text-sm text-white/40">Loading…</p>
        ) : !data || data.items.length === 0 ? (
          <div className="flex flex-col items-center gap-3 py-10 text-center">
            <Inbox size={28} className="text-white/25" />
            <p className="text-sm text-white/40">
              {status === 'pending' ? 'Nothing waiting on review right now.' : `No ${status.replace('_', ' ')} cases.`}
            </p>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-white/10 text-left text-xs uppercase tracking-wide text-white/35">
                    <th className="pb-3 pr-4 font-medium">Transaction</th>
                    <th className="pb-3 pr-4 font-medium">Merchant / Amount</th>
                    <th className="pb-3 pr-4 font-medium">Risk</th>
                    <th className="pb-3 pr-4 font-medium">System Flag</th>
                    <th className="pb-3 pr-4 font-medium">Assigned To</th>
                    <th className="pb-3 pr-4 font-medium">Flagged</th>
                    <th className="pb-3 font-medium" />
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((r) => {
                    const risk = riskLevel(r.risk_score)
                    return (
                      <tr
                        key={r.id}
                        onClick={() => setSelectedId(r.id)}
                        className="cursor-pointer border-b border-white/5 last:border-0 hover:bg-white/[0.02]"
                      >
                        <td className="py-3 pr-4 font-mono text-xs text-white/50">{r.transaction_id.slice(0, 8)}…</td>
                        <td className="py-3 pr-4">
                          <p className="text-white/80">{r.merchant || '—'}</p>
                          <p className="text-xs text-white/35">{formatCurrency(r.amount)}</p>
                        </td>
                        <td className="py-3 pr-4">
                          <span className={cn('badge text-[10px]', `badge-${risk.color}`)}>
                            {risk.label} · {Math.round(r.risk_score)}
                          </span>
                        </td>
                        <td className="py-3 pr-4">
                          <span className="badge border border-white/10 bg-white/5 text-white/50 text-[10px]">
                            {ORIGIN_LABEL[r.decision] || r.decision}
                          </span>
                        </td>
                        <td className="py-3 pr-4 text-white/60">
                          {r.assigned_analyst_name || <span className="text-white/25">Unclaimed</span>}
                        </td>
                        <td className="py-3 pr-4 text-xs text-white/40">{formatDateTime(r.created_at)}</td>
                        <td className="py-3 text-right">
                          {status === 'pending' && canAct && (
                            <button
                              onClick={(e) => { e.stopPropagation(); handleClaim(r.id) }}
                              disabled={actingId === r.id}
                              className="btn-ghost px-2.5 py-1 text-xs disabled:opacity-50"
                            >
                              {actingId === r.id ? <Loader2 size={13} className="animate-spin" /> : <UserCheck size={13} />}
                              Claim
                            </button>
                          )}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>

            <div className="mt-5 flex items-center justify-between text-xs text-white/40">
              <span>Page {data.page} of {data.total_pages} · {data.total} total</span>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={data.page <= 1}
                  className="btn-ghost px-3 py-1.5 disabled:opacity-40"
                >
                  <ChevronLeft size={14} />
                </button>
                <button
                  onClick={() => setPage((p) => Math.min(data.total_pages, p + 1))}
                  disabled={data.page >= data.total_pages}
                  className="btn-ghost px-3 py-1.5 disabled:opacity-40"
                >
                  <ChevronRight size={14} />
                </button>
              </div>
            </div>
          </>
        )}
      </GlassCard>

      {selectedId && (
        <div className="fixed inset-0 z-50 flex items-center justify-end bg-black/60 backdrop-blur-sm" onClick={() => setSelectedId(null)}>
          <div
            className="glass-card h-full w-full max-w-lg overflow-y-auto rounded-none border-l border-white/10 p-6 sm:rounded-l-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mb-5 flex items-center justify-between">
              <h2 className="font-display text-lg font-semibold">Review Case</h2>
              <button onClick={() => setSelectedId(null)} className="text-white/40 hover:text-white">
                <X size={20} />
              </button>
            </div>

            {detailLoading || !detail ? (
              <p className="py-10 text-center text-sm text-white/40">Loading…</p>
            ) : (
              <>
                <div className="mb-5 flex items-center gap-3 rounded-xl border border-white/10 bg-white/[0.03] p-4">
                  <ShieldAlert size={20} className="shrink-0 text-warning" />
                  <div>
                    <p className="text-sm text-white/80">{detail.merchant || 'Unknown merchant'} · {formatCurrency(detail.amount, detail.currency)}</p>
                    <p className="text-xs text-white/40">Flagged {formatDateTime(detail.created_at)} · Risk score {Math.round(detail.risk_score)}</p>
                  </div>
                </div>

                <div className="mb-5">
                  <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-white/35">Model Explanation</p>
                  <p className="text-sm text-white/70">{detail.explanation}</p>
                </div>

                {detail.triggered_rules?.length > 0 && (
                  <div className="mb-5">
                    <p className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-white/35">
                      <Sliders size={12} /> Business Rules Also Triggered
                    </p>
                    <div className="space-y-1.5">
                      {detail.triggered_rules.map((t) => (
                        <div key={t.rule_id} className="rounded-lg border border-warning/20 bg-warning/5 px-3 py-2 text-xs">
                          <p className="text-white/80">{t.name}</p>
                          <p className="mt-0.5 font-mono text-white/40">{t.field} {t.operator} "{t.value}" → {t.action}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <div className="mb-5">
                  <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-white/35">Top Contributing Features</p>
                  <div className="space-y-1.5">
                    {detail.top_shap_features?.slice(0, 5).map((f) => (
                      <div key={f.feature} className="flex items-center justify-between rounded-lg border border-white/5 bg-white/[0.02] px-3 py-2 text-xs">
                        <span className="font-mono text-white/60">{f.feature}</span>
                        <span className={f.impact >= 0 ? 'text-danger' : 'text-success'}>
                          {f.impact >= 0 ? '+' : ''}{f.impact.toFixed(3)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="mb-6">
                  <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-white/35">Assigned To</p>
                  <p className="text-sm text-white/70">{detail.assigned_analyst_name || 'Unclaimed'}</p>
                </div>

                {detail.status === 'resolved' ? (
                  <div className="rounded-xl border border-white/10 bg-white/[0.03] p-4 text-sm text-white/60">
                    Resolved {formatDateTime(detail.resolved_at)} as{' '}
                    <span className={detail.analyst_decision === 'fraud' ? 'text-danger' : 'text-success'}>
                      {detail.analyst_decision === 'fraud' ? 'Confirmed Fraud' : 'Legitimate'}
                    </span>
                    {detail.notes && <p className="mt-2 text-white/50">"{detail.notes}"</p>}
                  </div>
                ) : canAct ? (
                  <div className="space-y-3">
                    <textarea
                      value={detail.notes || ''}
                      onChange={(e) => setDetail((d) => ({ ...d, notes: e.target.value }))}
                      placeholder="Add notes for the record (optional)..."
                      rows={3}
                      className="input-glass w-full resize-none text-sm"
                    />
                    <div className="flex gap-3">
                      <button
                        onClick={() => handleResolve(detail.id, 'legitimate')}
                        disabled={actingId === detail.id}
                        className="btn-ghost flex-1 justify-center border-success/30 text-success hover:bg-success/10 disabled:opacity-50"
                      >
                        <CheckCircle2 size={16} /> Legitimate
                      </button>
                      <button
                        onClick={() => handleResolve(detail.id, 'fraud')}
                        disabled={actingId === detail.id}
                        className="btn-ghost flex-1 justify-center border-danger/30 text-danger hover:bg-danger/10 disabled:opacity-50"
                      >
                        <XCircle size={16} /> Confirm Fraud
                      </button>
                    </div>
                  </div>
                ) : (
                  <p className="text-sm text-white/40">Read-only access — only Admins and Analysts can resolve cases.</p>
                )}
              </>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
