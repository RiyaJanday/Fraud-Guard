import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import toast from 'react-hot-toast'
import { User, Bell, Shield, KeyRound, Users } from 'lucide-react'
import PageHeader from '../components/ui/PageHeader'
import GlassCard from '../components/ui/GlassCard'
import { cn } from '../lib/utils'
import { useAuth } from '../context/AuthContext'

const profileSchema = z.object({
  name: z.string().min(2, 'Name must be at least 2 characters'),
  email: z.string().email('Enter a valid email address'),
  org: z.string().min(2, 'Organization is required'),
})

const TABS = [
  { id: 'general', label: 'General', icon: User },
  { id: 'security', label: 'Security', icon: Shield },
  { id: 'notifications', label: 'Notifications', icon: Bell },
  { id: 'api', label: 'API Keys', icon: KeyRound },
  { id: 'team', label: 'Team', icon: Users },
]

export default function Settings() {
  const [tab, setTab] = useState('general')
  const { user } = useAuth()

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm({
    resolver: zodResolver(profileSchema),
    defaultValues: { name: user?.name || '', email: user?.email || '', org: user?.org || '' },
  })

  const onSubmit = async () => {
    await new Promise((r) => setTimeout(r, 700))
    toast.success('Settings saved successfully')
  }

  return (
    <div>
      <PageHeader eyebrow="Preferences" title="Settings" subtitle="Manage your account, security and workspace preferences." />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-4">
        <div className="lg:col-span-1">
          <GlassCard hover={false} className="p-2">
            {TABS.map((t) => (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                className={cn('flex w-full items-center gap-3 rounded-xl px-3.5 py-2.5 text-sm font-medium transition', tab === t.id ? 'bg-primary/15 text-white border border-primary/30' : 'text-white/50 hover:bg-white/[0.05] hover:text-white')}
              >
                <t.icon size={16} /> {t.label}
              </button>
            ))}
          </GlassCard>
        </div>

        <div className="lg:col-span-3">
          {tab === 'general' && (
            <GlassCard hover={false}>
              <h3 className="mb-5 font-display text-base font-semibold">General Information</h3>
              <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <div>
                    <label className="mb-1.5 block text-xs font-medium text-white/50">Full Name</label>
                    <input {...register('name')} className="input-glass" />
                    {errors.name && <p className="mt-1 text-xs text-danger">{errors.name.message}</p>}
                  </div>
                  <div>
                    <label className="mb-1.5 block text-xs font-medium text-white/50">Email Address</label>
                    <input {...register('email')} className="input-glass" />
                    {errors.email && <p className="mt-1 text-xs text-danger">{errors.email.message}</p>}
                  </div>
                </div>
                <div>
                  <label className="mb-1.5 block text-xs font-medium text-white/50">Organization</label>
                  <input {...register('org')} className="input-glass" />
                  {errors.org && <p className="mt-1 text-xs text-danger">{errors.org.message}</p>}
                </div>
                <div>
                  <label className="mb-1.5 block text-xs font-medium text-white/50">Fraud Sensitivity Threshold</label>
                  <input type="range" min="0" max="100" defaultValue="65" className="w-full accent-primary" />
                  <div className="mt-1 flex justify-between text-[11px] text-white/30">
                    <span>Permissive</span>
                    <span>Balanced</span>
                    <span>Strict</span>
                  </div>
                </div>
                <div className="flex justify-end gap-3 pt-2">
                  <button type="button" className="btn-ghost text-sm">Cancel</button>
                  <button type="submit" disabled={isSubmitting} className="btn-primary text-sm">
                    {isSubmitting ? 'Saving...' : 'Save Changes'}
                  </button>
                </div>
              </form>
            </GlassCard>
          )}

          {tab === 'security' && (
            <GlassCard hover={false}>
              <h3 className="mb-5 font-display text-base font-semibold">Security</h3>
              <div className="space-y-4">
                <ToggleRow title="Two-Factor Authentication" desc="Require a verification code at every login" defaultOn />
                <ToggleRow title="Login Alerts" desc="Get notified when a new device signs in" defaultOn />
                <ToggleRow title="IP Allowlisting" desc="Restrict dashboard access to approved IP ranges" />
                <div className="pt-2">
                  <button className="btn-ghost text-sm">Change Password</button>
                </div>
              </div>
            </GlassCard>
          )}

          {tab === 'notifications' && (
            <GlassCard hover={false}>
              <h3 className="mb-5 font-display text-base font-semibold">Notification Preferences</h3>
              <div className="space-y-4">
                <ToggleRow title="Critical Fraud Alerts" desc="Real-time alerts for blocked high-risk transactions" defaultOn />
                <ToggleRow title="Weekly Summary Email" desc="A digest of fraud activity every Monday" defaultOn />
                <ToggleRow title="Model Update Notices" desc="Notify when the detection model is retrained" />
                <ToggleRow title="Product Announcements" desc="Occasional updates about new FraudGuard features" />
              </div>
            </GlassCard>
          )}

          {tab === 'api' && (
            <GlassCard hover={false}>
              <h3 className="mb-5 font-display text-base font-semibold">API Keys</h3>
              <div className="space-y-3">
                {[
                  { name: 'Production Key', key: 'fg_live_••••••••••••8f2a', created: 'Created Jan 12, 2026' },
                  { name: 'Sandbox Key', key: 'fg_test_••••••••••••c910', created: 'Created Mar 3, 2026' },
                ].map((k) => (
                  <div key={k.name} className="flex items-center justify-between rounded-xl border border-white/10 bg-white/[0.02] p-4">
                    <div>
                      <p className="text-sm font-medium text-white/85">{k.name}</p>
                      <p className="font-mono text-xs text-white/40">{k.key}</p>
                      <p className="mt-0.5 text-[11px] text-white/25">{k.created}</p>
                    </div>
                    <button onClick={() => toast('Key rotated', { icon: '🔑' })} className="btn-ghost text-xs">Rotate</button>
                  </div>
                ))}
                <button onClick={() => toast.success('New API key generated')} className="btn-primary mt-2 text-sm">
                  Generate New Key
                </button>
              </div>
            </GlassCard>
          )}

          {tab === 'team' && (
            <GlassCard hover={false}>
              <h3 className="mb-5 font-display text-base font-semibold">Team Members</h3>
              <div className="space-y-3">
                {[
                  { name: 'Aarav Mehta', role: 'Senior Fraud Analyst', initials: 'AM' },
                  { name: 'Aditi Sharma', role: 'Fraud Analyst', initials: 'AS' },
                  { name: 'Rohan Kapoor', role: 'ML Engineer', initials: 'RK' },
                  { name: 'Priya Nair', role: 'Compliance Lead', initials: 'PN' },
                ].map((m) => (
                  <div key={m.name} className="flex items-center justify-between rounded-xl border border-white/10 bg-white/[0.02] p-3.5">
                    <div className="flex items-center gap-3">
                      <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-primary to-accent text-xs font-semibold">
                        {m.initials}
                      </div>
                      <div>
                        <p className="text-sm font-medium text-white/85">{m.name}</p>
                        <p className="text-xs text-white/40">{m.role}</p>
                      </div>
                    </div>
                    <button className="btn-ghost text-xs">Manage</button>
                  </div>
                ))}
                <button onClick={() => toast.success('Invitation sent')} className="btn-primary mt-2 text-sm">
                  Invite Team Member
                </button>
              </div>
            </GlassCard>
          )}
        </div>
      </div>
    </div>
  )
}

function ToggleRow({ title, desc, defaultOn = false }) {
  const [on, setOn] = useState(defaultOn)
  return (
    <div className="flex items-center justify-between rounded-xl border border-white/10 bg-white/[0.02] p-4">
      <div>
        <p className="text-sm font-medium text-white/85">{title}</p>
        <p className="text-xs text-white/40">{desc}</p>
      </div>
      <button
        onClick={() => setOn((v) => !v)}
        className={cn('relative h-6 w-11 shrink-0 rounded-full transition-colors', on ? 'bg-primary' : 'bg-white/10')}
      >
        <span className={cn('absolute top-0.5 h-5 w-5 rounded-full bg-white transition-transform', on ? 'translate-x-5' : 'translate-x-0.5')} />
      </button>
    </div>
  )
}
