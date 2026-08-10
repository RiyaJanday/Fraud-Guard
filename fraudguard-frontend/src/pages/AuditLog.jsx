import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { ClipboardList, ChevronLeft, ChevronRight, CheckCircle2, XCircle } from 'lucide-react'
import PageHeader from '../components/ui/PageHeader'
import GlassCard from '../components/ui/GlassCard'
import { fraudApi, getApiErrorMessage } from '../lib/api'
import { formatCurrency, formatDateTime, cn } from '../lib/utils'

const DECISION_META = {
  fraud: { label: 'Confirmed Fraud', icon: XCircle, className: 'text-danger' },
  legitimate: { label: 'Marked Legitimate', icon: CheckCircle2, className: 'text-success' },
}

const ORIGIN_LABEL = { blocked: 'Auto-Blocked', mfa_required: 'MFA Required' }

export default function AuditLog() {
  const [loading, setLoading] = useState(true)
  const [data, setData] = useState(null)
  const [page, setPage] = useState(1)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    fraudApi
      .getAuditLog({ page, page_size: 20 })
      .then(({ data: res }) => !cancelled && setData(res))
      .catch((err) => !cancelled && toast.error(getApiErrorMessage(err, 'Could not load the audit log')))
      .finally(() => !cancelled && setLoading(false))
    return () => { cancelled = true }
  }, [page])

  return (
    <div>
      <PageHeader
        eyebrow="Compliance"
        title="Audit Trail"
        subtitle="Every resolved manual review, across every analyst — the forensic record for predictions, risk scores, and the human decisions made on top of them."
      />

      <GlassCard hover={false}>
        {loading ? (
          <p className="py-10 text-center text-sm text-white/40">Loading…</p>
        ) : !data || data.items.length === 0 ? (
          <div className="flex flex-col items-center gap-3 py-10 text-center">
            <ClipboardList size={28} className="text-white/25" />
            <p className="text-sm text-white/40">No resolved reviews yet.</p>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-white/10 text-left text-xs uppercase tracking-wide text-white/35">
                    <th className="pb-3 pr-4 font-medium">Transaction</th>
                    <th className="pb-3 pr-4 font-medium">Merchant / Amount</th>
                    <th className="pb-3 pr-4 font-medium">System Flag</th>
                    <th className="pb-3 pr-4 font-medium">Analyst Decision</th>
                    <th className="pb-3 pr-4 font-medium">Reviewed By</th>
                    <th className="pb-3 font-medium">Resolved</th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((r) => {
                    const meta = DECISION_META[r.analyst_decision] || { label: r.analyst_decision, icon: ClipboardList, className: 'text-white/50' }
                    const Icon = meta.icon
                    return (
                      <tr key={r.id} className="border-b border-white/5 last:border-0">
                        <td className="py-3 pr-4 font-mono text-xs text-white/50">{r.transaction_id.slice(0, 8)}…</td>
                        <td className="py-3 pr-4">
                          <p className="text-white/80">{r.merchant || '—'}</p>
                          <p className="text-xs text-white/35">{formatCurrency(r.amount)}</p>
                        </td>
                        <td className="py-3 pr-4">
                          <span className="badge border border-white/10 bg-white/5 text-white/50 text-[10px]">
                            {ORIGIN_LABEL[r.decision] || r.decision}
                          </span>
                        </td>
                        <td className="py-3 pr-4">
                          <span className={cn('flex items-center gap-1.5', meta.className)}>
                            <Icon size={14} /> {meta.label}
                          </span>
                        </td>
                        <td className="py-3 pr-4 text-white/60">{r.assigned_analyst_name || '—'}</td>
                        <td className="py-3 text-xs text-white/40">{r.resolved_at ? formatDateTime(r.resolved_at) : '—'}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>

            <div className="mt-5 flex items-center justify-between text-xs text-white/40">
              <span>
                Page {data.page} of {data.total_pages} · {data.total} total
              </span>
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
    </div>
  )
}
