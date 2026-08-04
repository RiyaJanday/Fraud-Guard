import { useEffect, useState } from 'react'
import { Mail, Building2, ShieldCheck, Award, Activity, Clock, CheckCircle2, XCircle } from 'lucide-react'
import PageHeader from '../components/ui/PageHeader'
import GlassCard from '../components/ui/GlassCard'
import AnimatedNumber from '../components/ui/AnimatedNumber'
import { useAuth } from '../context/AuthContext'
import { fraudApi } from '../lib/api'
import { timeAgo } from '../lib/transform'

const DECISION_META = {
  fraud: { label: 'Confirmed fraud', icon: XCircle, className: 'text-danger' },
  legitimate: { label: 'Marked legitimate', icon: CheckCircle2, className: 'text-success' },
}

export default function Profile() {
  const { user } = useAuth()
  const [stats, setStats] = useState(null)
  const [activity, setActivity] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    Promise.all([fraudApi.getMyStats(), fraudApi.getMyActivity()])
      .then(([statsRes, activityRes]) => {
        if (cancelled) return
        setStats(statsRes.data)
        setActivity(activityRes.data)
      })
      .catch(() => {})
      .finally(() => !cancelled && setLoading(false))
    return () => { cancelled = true }
  }, [])

  const STATS = [
    { label: 'Cases Reviewed', value: stats?.cases_reviewed ?? 0, icon: Activity },
    { label: 'Fraud Confirmed', value: stats?.fraud_confirmed ?? 0, icon: Award },
    {
      label: 'Avg. Response Time',
      value: stats?.avg_response_minutes ?? 0,
      suffix: 'm',
      decimals: 1,
      icon: Clock,
    },
  ]

  return (
    <div>
      <PageHeader eyebrow="Account" title="Profile" subtitle="Your activity, credentials and analyst performance." />

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
        <GlassCard className="flex flex-col items-center text-center lg:col-span-1">
          <div className="flex h-20 w-20 items-center justify-center rounded-2xl bg-gradient-to-br from-primary to-accent font-display text-2xl font-semibold shadow-glow">
            {user?.avatar || 'AM'}
          </div>
          <h3 className="mt-4 font-display text-lg font-semibold">{user?.name || 'Analyst'}</h3>
          <p className="text-sm capitalize text-white/40">{user?.role || 'analyst'}</p>
          {user?.isVerified && (
            <span className="badge-success mt-3">
              <ShieldCheck size={12} /> Verified
            </span>
          )}

          <div className="mt-6 w-full space-y-3 border-t border-white/10 pt-5 text-left">
            <div className="flex items-center gap-2.5 text-sm text-white/60">
              <Mail size={14} className="text-white/30" /> {user?.email || '—'}
            </div>
            <div className="flex items-center gap-2.5 text-sm text-white/60">
              <Building2 size={14} className="text-white/30" /> {user?.org || '—'}
            </div>
          </div>
        </GlassCard>

        <div className="space-y-5 lg:col-span-2">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            {STATS.map((s, i) => (
              <GlassCard key={s.label} delay={i * 0.05}>
                <div className="mb-2 w-fit rounded-lg border border-white/10 bg-white/[0.04] p-2 text-primary">
                  <s.icon size={16} />
                </div>
                <p className="font-display text-2xl font-semibold">
                  <AnimatedNumber value={s.value} decimals={s.decimals || 0} duration={1.4} suffix={s.suffix} />
                </p>
                <p className="mt-1 text-xs text-white/40">{s.label}</p>
              </GlassCard>
            ))}
          </div>

          <GlassCard hover={false}>
            <h3 className="mb-4 font-display text-base font-semibold">Recent Activity</h3>
            <div className="space-y-4">
              {loading ? (
                <p className="py-6 text-center text-xs text-white/30">Loading activity…</p>
              ) : activity.length === 0 ? (
                <p className="py-6 text-center text-xs text-white/30">No resolved reviews yet.</p>
              ) : (
                activity.map((a) => {
                  const meta = DECISION_META[a.analyst_decision] || { label: a.analyst_decision || 'Reviewed', icon: Activity, className: 'text-white/50' }
                  const Icon = meta.icon
                  return (
                    <div key={a.transaction_id} className="flex items-start justify-between border-b border-white/5 pb-4 last:border-0 last:pb-0">
                      <div className="flex items-start gap-2.5">
                        <Icon size={14} className={`mt-0.5 shrink-0 ${meta.className}`} />
                        <div>
                          <p className="text-sm text-white/85">{meta.label}{a.merchant ? ` — ${a.merchant}` : ''}</p>
                          <p className="font-mono text-xs text-white/35">{a.transaction_id}</p>
                        </div>
                      </div>
                      <span className="whitespace-nowrap text-xs text-white/30">{timeAgo(a.resolved_at)}</span>
                    </div>
                  )
                })
              )}
            </div>
          </GlassCard>
        </div>
      </div>
    </div>
  )
}
