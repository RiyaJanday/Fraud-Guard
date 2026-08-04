import { useEffect, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import toast from 'react-hot-toast'
import {
  X, MapPin, CreditCard, Smartphone, User, Clock,
  ShieldAlert, ShieldCheck, ShieldQuestion, Sparkles, Loader2, CheckCircle2,
} from 'lucide-react'
import StatusBadge from './StatusBadge'
import RiskGauge from '../ui/RiskGauge'
import { fraudApi } from '../../lib/api'
import { formatCurrency, formatDateTime, riskLevel } from '../../lib/utils'

function suggestedAction(status) {
  if (status === 'blocked')
    return {
      icon: ShieldAlert,
      color: 'text-danger',
      text: 'Transaction was auto-blocked. Recommend confirming with cardholder before manual override.',
    }
  if (status === 'mfa')
    return {
      icon: ShieldQuestion,
      color: 'text-warning',
      text: 'Step-up authentication (OTP / biometric) required before settlement can proceed.',
    }
  return {
    icon: ShieldCheck,
    color: 'text-success',
    text: 'Transaction matches cardholder behavioral profile. No further action required.',
  }
}

function explanation(txn) {
  if (txn.explanationText) return txn.explanationText
  const top = txn.shap[0]
  const level = riskLevel(txn.risk).label.toLowerCase()
  return `This transaction was scored ${level} risk (${txn.risk}/100), primarily driven by ${top.label.toLowerCase()}. The model weighed ${txn.shap.length} behavioral and contextual signals before making a decision, cross-referencing this purchase against the cardholder's 90-day spending profile and device history.`
}

export default function TransactionDrawer({ transaction, onClose }) {
  // Local copy of review state so a Claim/Resolve action can update the UI
  // immediately without waiting on the parent to refetch the whole
  // transaction — re-synced whenever a different transaction is opened.
  const [review, setReview] = useState(transaction?.review || null)
  const [claiming, setClaiming] = useState(false)
  const [resolving, setResolving] = useState(false)

  useEffect(() => {
    setReview(transaction?.review || null)
  }, [transaction?.id])

  async function handleEscalate() {
    if (!review) return
    setClaiming(true)
    try {
      const { data } = await fraudApi.claimReview(review.id)
      setReview((r) => ({ ...r, status: data.status, assignedAnalystName: r.assignedAnalystName }))
      toast.success('Escalated — claimed for active review')
    } catch (err) {
      toast.error(err?.response?.data?.detail?.message || 'Could not escalate this review')
    } finally {
      setClaiming(false)
    }
  }

  async function handleConfirm() {
    if (!review) return
    setResolving(true)
    try {
      const { data } = await fraudApi.resolveReview(review.id, { decision: 'fraud' })
      setReview((r) => ({ ...r, status: data.status, analystDecision: data.analyst_decision, resolvedAt: data.resolved_at }))
      toast.success('Decision confirmed — recorded as fraud')
    } catch (err) {
      toast.error(err?.response?.data?.detail?.message || 'Could not confirm this decision')
    } finally {
      setResolving(false)
    }
  }

  return (
    <AnimatePresence>
      {transaction && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm"
          />
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 30, stiffness: 260 }}
            className="fixed right-0 top-0 z-50 h-full w-full max-w-lg overflow-y-auto border-l border-white/10 bg-bg-soft/98 backdrop-blur-2xl shadow-2xl"
          >
            <div className="sticky top-0 z-10 flex items-center justify-between border-b border-white/10 bg-bg-soft/95 px-6 py-4 backdrop-blur-xl">
              <div>
                <p className="font-mono text-xs text-white/40">{transaction.id}</p>
                <p className="mt-0.5 font-display text-lg font-semibold">{transaction.merchant}</p>
              </div>
              <button onClick={onClose} className="rounded-lg p-2 text-white/40 hover:bg-white/[0.06] hover:text-white">
                <X size={18} />
              </button>
            </div>

            <div className="space-y-6 p-6">
              {/* Amount + status */}
              <div className="glass-panel flex items-center justify-between p-5">
                <div>
                  <p className="text-xs text-white/40">Amount</p>
                  <p className="font-display text-2xl font-semibold">{formatCurrency(transaction.amount)}</p>
                </div>
                <StatusBadge status={transaction.status} />
              </div>

              {/* Risk gauge */}
              <div className="glass-panel flex flex-col items-center p-5">
                <p className="mb-1 text-xs font-medium uppercase tracking-wider text-white/40">Risk Probability</p>
                <RiskGauge value={transaction.risk} />
              </div>

              {/* Transaction info */}
              <div className="glass-panel p-5">
                <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-white/40">Transaction Details</p>
                <dl className="space-y-3 text-sm">
                  <Row icon={Clock} label="Timestamp" value={formatDateTime(transaction.timestamp)} />
                  <Row icon={User} label="Customer" value={transaction.customer} />
                  <Row icon={CreditCard} label="Card" value={transaction.card} />
                  <Row icon={MapPin} label="Location" value={transaction.city} />
                  <Row icon={Smartphone} label="Device" value={transaction.device} />
                </dl>
              </div>

              {/* SHAP features */}
              <div className="glass-panel p-5">
                <p className="mb-3 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-white/40">
                  <Sparkles size={13} className="text-primary" /> Top SHAP Features
                </p>
                <div className="space-y-2.5">
                  {transaction.shap.map((f) => {
                    const positive = f.impact >= 0
                    const width = Math.min(Math.abs(f.impact) * 220, 100)
                    return (
                      <div key={f.key}>
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-white/70">{f.label}</span>
                          <span className={positive ? 'text-danger' : 'text-success'}>
                            {positive ? '+' : ''}{f.impact}
                          </span>
                        </div>
                        <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-white/10">
                          <motion.div
                            initial={{ width: 0 }}
                            animate={{ width: `${width}%` }}
                            transition={{ duration: 0.7, ease: 'easeOut' }}
                            className={`h-full rounded-full ${positive ? 'bg-danger' : 'bg-success'}`}
                          />
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>

              {/* Natural language explanation */}
              <div className="glass-panel border-primary/20 bg-primary/[0.04] p-5">
                <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-primary/80">AI Explanation</p>
                <p className="text-sm leading-relaxed text-white/70">{explanation(transaction)}</p>
              </div>

              {/* Suggested action */}
              {(() => {
                const action = suggestedAction(transaction.status)
                const Icon = action.icon
                return (
                  <div className="glass-panel flex gap-3 p-5">
                    <Icon size={20} className={`shrink-0 ${action.color}`} />
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-wider text-white/40">Suggested Action</p>
                      <p className="mt-1 text-sm text-white/70">{action.text}</p>
                    </div>
                  </div>
                )
              })()}

              {/* Decision history */}
              <div className="glass-panel p-5">
                <p className="mb-4 text-xs font-semibold uppercase tracking-wider text-white/40">Decision History</p>
                <div className="space-y-4">
                  {transaction.history.map((h, i) => (
                    <div key={i} className="relative flex gap-3 pl-1">
                      <div className="flex flex-col items-center">
                        <span className="h-2.5 w-2.5 rounded-full bg-primary ring-4 ring-primary/15" />
                        {i < transaction.history.length - 1 && <span className="mt-1 h-8 w-px bg-white/10" />}
                      </div>
                      <div className="-mt-1">
                        <p className="text-sm text-white/85">{h.step}</p>
                        <p className="text-xs text-white/35">{h.actor} · {h.time}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="flex gap-3 pb-4">
                {!review ? (
                  // Only BLOCKED transactions ever enter the review queue
                  // (see ReviewService.create_review_if_needed) — there's
                  // nothing real to confirm/escalate for an approved or
                  // MFA transaction, so the actions don't render at all
                  // rather than being fake buttons that do nothing.
                  <p className="w-full text-center text-xs text-white/30">
                    This transaction wasn't routed for manual review.
                  </p>
                ) : review.status === 'resolved' ? (
                  <div className="flex w-full items-center justify-center gap-2 rounded-lg border border-success/30 bg-success/10 px-4 py-2.5 text-sm text-success">
                    <CheckCircle2 size={16} />
                    Resolved as {review.analystDecision === 'fraud' ? 'fraud' : 'legitimate'}
                    {review.resolvedAt ? ` · ${formatDateTime(review.resolvedAt)}` : ''}
                  </div>
                ) : (
                  <>
                    <button
                      onClick={handleEscalate}
                      disabled={claiming || review.status === 'in_review'}
                      className="btn-ghost flex-1 disabled:opacity-50"
                    >
                      {claiming ? <Loader2 size={15} className="animate-spin" /> : null}
                      {review.status === 'in_review' ? 'Claimed for review' : 'Escalate to Analyst'}
                    </button>
                    <button onClick={handleConfirm} disabled={resolving} className="btn-primary flex-1 disabled:opacity-50">
                      {resolving ? <Loader2 size={15} className="animate-spin" /> : null}
                      Confirm Decision
                    </button>
                  </>
                )}
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}

function Row({ icon: Icon, label, value }) {
  return (
    <div className="flex items-center justify-between">
      <span className="flex items-center gap-2 text-white/40">
        <Icon size={14} /> {label}
      </span>
      <span className="font-medium text-white/85">{value}</span>
    </div>
  )
}
