import { Mail, Building2, ShieldCheck, Award, Activity, Clock } from 'lucide-react'
import PageHeader from '../components/ui/PageHeader'
import GlassCard from '../components/ui/GlassCard'
import AnimatedNumber from '../components/ui/AnimatedNumber'
import { useAuth } from '../context/AuthContext'

const STATS = [
  { label: 'Cases Reviewed', value: 4218, icon: Activity },
  { label: 'Accuracy Rate', value: 98.4, suffix: '%', decimals: 1, icon: Award },
  { label: 'Avg. Response Time', value: 1.8, suffix: 'm', decimals: 1, icon: Clock },
]

const ACTIVITY = [
  { action: 'Confirmed block decision', target: 'TXN-9F2A1-7042', time: '18 min ago' },
  { action: 'Escalated to compliance', target: 'TXN-8B41C-7038', time: '1 hr ago' },
  { action: 'Approved after MFA', target: 'TXN-7C902-7021', time: '3 hr ago' },
  { action: 'Rotated API key', target: 'Production Key', time: 'Yesterday' },
  { action: 'Updated risk threshold', target: 'Sensitivity: 65 → 70', time: '2 days ago' },
]

export default function Profile() {
  const { user } = useAuth()

  return (
    <div>
      <PageHeader eyebrow="Account" title="Profile" subtitle="Your activity, credentials and analyst performance." />

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
        <GlassCard className="flex flex-col items-center text-center lg:col-span-1">
          <div className="flex h-20 w-20 items-center justify-center rounded-2xl bg-gradient-to-br from-primary to-accent font-display text-2xl font-semibold shadow-glow">
            {user?.avatar || 'AM'}
          </div>
          <h3 className="mt-4 font-display text-lg font-semibold">{user?.name || 'Aarav Mehta'}</h3>
          <p className="text-sm text-white/40">{user?.role || 'Senior Fraud Analyst'}</p>
          <span className="badge-success mt-3">
            <ShieldCheck size={12} /> Verified Analyst
          </span>

          <div className="mt-6 w-full space-y-3 border-t border-white/10 pt-5 text-left">
            <div className="flex items-center gap-2.5 text-sm text-white/60">
              <Mail size={14} className="text-white/30" /> {user?.email || 'aarav.mehta@fraudguard.ai'}
            </div>
            <div className="flex items-center gap-2.5 text-sm text-white/60">
              <Building2 size={14} className="text-white/30" /> {user?.org || 'NovaBank Financial Services'}
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
              {ACTIVITY.map((a, i) => (
                <div key={i} className="flex items-start justify-between border-b border-white/5 pb-4 last:border-0 last:pb-0">
                  <div>
                    <p className="text-sm text-white/85">{a.action}</p>
                    <p className="font-mono text-xs text-white/35">{a.target}</p>
                  </div>
                  <span className="whitespace-nowrap text-xs text-white/30">{a.time}</span>
                </div>
              ))}
            </div>
          </GlassCard>
        </div>
      </div>
    </div>
  )
}
