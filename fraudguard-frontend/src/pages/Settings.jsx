import { useState, useEffect, useCallback } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import toast from 'react-hot-toast'
import { User, Bell, Shield, KeyRound, Users, UserPlus, Copy, Ban, CheckCircle2, Cpu, RefreshCw } from 'lucide-react'
import PageHeader from '../components/ui/PageHeader'
import GlassCard from '../components/ui/GlassCard'
import { cn } from '../lib/utils'
import { useAuth } from '../context/AuthContext'
import { fraudApi, getApiErrorMessage } from '../lib/api'

const profileSchema = z.object({
  name: z.string().min(2, 'Name must be at least 2 characters'),
})

const passwordSchema = z
  .object({
    currentPassword: z.string().min(1, 'Current password is required'),
    newPassword: z
      .string()
      .min(8, 'At least 8 characters')
      .regex(/[0-9]/, 'Must contain at least one digit')
      .regex(/[a-zA-Z]/, 'Must contain at least one letter'),
    confirmPassword: z.string(),
  })
  .refine((d) => d.newPassword === d.confirmPassword, {
    message: "Passwords don't match",
    path: ['confirmPassword'],
  })

const inviteSchema = z.object({
  full_name: z.string().min(2, 'Name is required'),
  email: z.string().email('Enter a valid email address'),
  role: z.enum(['analyst', 'auditor', 'admin']),
})

const NOTIF_TOGGLES = [
  { key: 'blocked_transaction', title: 'Blocked Transaction Alerts', desc: 'Real-time alert whenever a transaction is blocked' },
  { key: 'high_risk_alert', title: 'High Risk Alerts', desc: 'Notify when a transaction is flagged for MFA / high risk' },
  { key: 'review_required', title: 'Review Required', desc: 'Notify when a transaction needs manual analyst review' },
  { key: 'model_update', title: 'Model Update Notices', desc: 'Notify when the detection model is retrained' },
]

const ALL_TABS = [
  { id: 'general', label: 'General', icon: User },
  { id: 'security', label: 'Security', icon: Shield },
  { id: 'notifications', label: 'Notifications', icon: Bell },
  { id: 'api', label: 'API Keys', icon: KeyRound },
  { id: 'team', label: 'Team', icon: Users, adminOnly: true },
  { id: 'model', label: 'Model', icon: Cpu, adminOnly: true },
]

export default function Settings() {
  const { user, updateUser } = useAuth()
  const isAdmin = user?.role === 'admin'
  const tabs = ALL_TABS.filter((t) => !t.adminOnly || isAdmin)
  const [tab, setTab] = useState('general')

  return (
    <div>
      <PageHeader eyebrow="Preferences" title="Settings" subtitle="Manage your account, security and workspace preferences." />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-4">
        <div className="lg:col-span-1">
          <GlassCard hover={false} className="p-2">
            {tabs.map((t) => (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                className={cn(
                  'flex w-full items-center gap-3 rounded-xl px-3.5 py-2.5 text-sm font-medium transition',
                  tab === t.id ? 'bg-primary/15 text-white border border-primary/30' : 'text-white/50 hover:bg-white/[0.05] hover:text-white'
                )}
              >
                <t.icon size={16} /> {t.label}
              </button>
            ))}
          </GlassCard>
        </div>

        <div className="lg:col-span-3">
          {tab === 'general' && <GeneralTab user={user} updateUser={updateUser} />}
          {tab === 'security' && <SecurityTab />}
          {tab === 'notifications' && <NotificationsTab />}
          {tab === 'api' && <ApiKeysTab />}
          {tab === 'team' && isAdmin && <TeamTab currentUserId={user?.id} />}
          {tab === 'model' && isAdmin && <ModelTab />}
        </div>
      </div>
    </div>
  )
}

// ------------------------------------------------------------------ //
// General
// ------------------------------------------------------------------ //
function GeneralTab({ user, updateUser }) {
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm({
    resolver: zodResolver(profileSchema),
    defaultValues: { name: user?.name || '' },
  })

  const onSubmit = async ({ name }) => {
    try {
      const { data } = await fraudApi.updateProfile({ full_name: name })
      updateUser({ name: data.full_name, avatar: initials(data.full_name) })
      toast.success('Profile updated')
    } catch (err) {
      toast.error(getApiErrorMessage(err, 'Failed to update profile'))
    }
  }

  return (
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
            <input value={user?.email || ''} disabled className="input-glass cursor-not-allowed opacity-60" />
            <p className="mt-1 text-[11px] text-white/25">Email is your login ID and can't be changed here.</p>
          </div>
        </div>
        <div>
          <label className="mb-1.5 block text-xs font-medium text-white/50">Role</label>
          <input value={user?.role || ''} disabled className="input-glass cursor-not-allowed capitalize opacity-60" />
        </div>
        <div className="flex justify-end gap-3 pt-2">
          <button type="submit" disabled={isSubmitting} className="btn-primary text-sm">
            {isSubmitting ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </form>
    </GlassCard>
  )
}

function initials(name) {
  if (!name) return 'FG'
  const parts = name.trim().split(/\s+/)
  return (parts[0][0] + (parts[1]?.[0] || '')).toUpperCase()
}

// ------------------------------------------------------------------ //
// Security
// ------------------------------------------------------------------ //
function SecurityTab() {
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm({ resolver: zodResolver(passwordSchema) })

  const onSubmit = async ({ currentPassword, newPassword }) => {
    try {
      await fraudApi.changePassword({ current_password: currentPassword, new_password: newPassword })
      toast.success('Password changed successfully')
      reset()
    } catch (err) {
      toast.error(getApiErrorMessage(err, 'Failed to change password — check your current password'))
    }
  }

  return (
    <GlassCard hover={false}>
      <h3 className="mb-5 font-display text-base font-semibold">Security</h3>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div>
          <label className="mb-1.5 block text-xs font-medium text-white/50">Current Password</label>
          <input type="password" {...register('currentPassword')} className="input-glass" />
          {errors.currentPassword && <p className="mt-1 text-xs text-danger">{errors.currentPassword.message}</p>}
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <label className="mb-1.5 block text-xs font-medium text-white/50">New Password</label>
            <input type="password" {...register('newPassword')} className="input-glass" />
            {errors.newPassword && <p className="mt-1 text-xs text-danger">{errors.newPassword.message}</p>}
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-white/50">Confirm New Password</label>
            <input type="password" {...register('confirmPassword')} className="input-glass" />
            {errors.confirmPassword && <p className="mt-1 text-xs text-danger">{errors.confirmPassword.message}</p>}
          </div>
        </div>
        <div className="flex justify-end pt-2">
          <button type="submit" disabled={isSubmitting} className="btn-primary text-sm">
            {isSubmitting ? 'Changing...' : 'Change Password'}
          </button>
        </div>
      </form>

      <div className="mt-6 space-y-4 border-t border-white/10 pt-5">
        <ToggleRow title="Two-Factor Authentication" desc="Require a verification code at every login" disabled comingSoon />
        <ToggleRow title="Login Alerts" desc="Get notified when a new device signs in" disabled comingSoon />
        <ToggleRow title="IP Allowlisting" desc="Restrict dashboard access to approved IP ranges" disabled comingSoon />
      </div>
    </GlassCard>
  )
}

// ------------------------------------------------------------------ //
// Notifications
// ------------------------------------------------------------------ //
function NotificationsTab() {
  const [prefs, setPrefs] = useState({})
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    fraudApi
      .getNotificationPreferences()
      .then(({ data }) => !cancelled && setPrefs(data.preferences || {}))
      .catch(() => toast.error('Failed to load notification preferences'))
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
  }, [])

  const toggle = useCallback(
    async (key) => {
      const nextValue = !(prefs[key] ?? true)
      const prev = prefs
      setPrefs((p) => ({ ...p, [key]: nextValue })) // optimistic
      try {
        await fraudApi.updateNotificationPreferences({ [key]: nextValue })
      } catch {
        setPrefs(prev) // rollback
        toast.error('Failed to save preference')
      }
    },
    [prefs]
  )

  return (
    <GlassCard hover={false}>
      <h3 className="mb-5 font-display text-base font-semibold">Notification Preferences</h3>
      {loading ? (
        <p className="py-6 text-center text-xs text-white/30">Loading preferences…</p>
      ) : (
        <div className="space-y-4">
          {NOTIF_TOGGLES.map((t) => (
            <ToggleRow
              key={t.key}
              title={t.title}
              desc={t.desc}
              on={prefs[t.key] ?? true}
              onChange={() => toggle(t.key)}
            />
          ))}
        </div>
      )}
    </GlassCard>
  )
}

// ------------------------------------------------------------------ //
// API Keys (not backed by the API yet — shown honestly, not faked)
// ------------------------------------------------------------------ //
function ApiKeysTab() {
  return (
    <GlassCard hover={false}>
      <h3 className="mb-2 font-display text-base font-semibold">API Keys</h3>
      <p className="text-sm text-white/50">
        Programmatic API key management isn't available yet — the backend doesn't issue or track API keys at this
        stage. All requests are currently authenticated via the login-based JWT tokens used by this dashboard.
      </p>
    </GlassCard>
  )
}

// ------------------------------------------------------------------ //
// Team (admin only)
// ------------------------------------------------------------------ //
function TeamTab({ currentUserId }) {
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [inviteOpen, setInviteOpen] = useState(false)
  const [newCreds, setNewCreds] = useState(null) // { email, temporary_password }
  const [busyId, setBusyId] = useState(null)

  const loadUsers = useCallback(() => {
    setLoading(true)
    fraudApi
      .listUsers({ page: 1, page_size: 200 })
      .then(({ data }) => setUsers(data.items))
      .catch(() => toast.error('Failed to load team members'))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    loadUsers()
  }, [loadUsers])

  const toggleActive = async (u) => {
    setBusyId(u.id)
    try {
      if (u.is_active) {
        await fraudApi.deactivateUser(u.id)
        toast.success(`${u.full_name} deactivated`)
      } else {
        await fraudApi.activateUser(u.id)
        toast.success(`${u.full_name} reactivated`)
      }
      loadUsers()
    } catch (err) {
      toast.error(getApiErrorMessage(err, 'Action failed'))
    } finally {
      setBusyId(null)
    }
  }

  return (
    <GlassCard hover={false}>
      <div className="mb-5 flex items-center justify-between">
        <h3 className="font-display text-base font-semibold">Team Members</h3>
        <button onClick={() => setInviteOpen(true)} className="btn-primary flex items-center gap-1.5 text-xs">
          <UserPlus size={14} /> Invite Member
        </button>
      </div>

      {loading ? (
        <p className="py-8 text-center text-xs text-white/30">Loading team…</p>
      ) : (
        <div className="space-y-3">
          {users.map((m) => (
            <div key={m.id} className="flex items-center justify-between rounded-xl border border-white/10 bg-white/[0.02] p-3.5">
              <div className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-primary to-accent text-xs font-semibold">
                  {initials(m.full_name)}
                </div>
                <div>
                  <p className="text-sm font-medium text-white/85">
                    {m.full_name} {m.id === currentUserId && <span className="text-white/30">(you)</span>}
                  </p>
                  <p className="text-xs capitalize text-white/40">{m.role} · {m.email}</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className={cn('badge text-[10px]', m.is_active ? 'badge-success' : 'border border-white/10 bg-white/5 text-white/40')}>
                  {m.is_active ? 'Active' : 'Deactivated'}
                </span>
                {m.id !== currentUserId && (
                  <button
                    onClick={() => toggleActive(m)}
                    disabled={busyId === m.id}
                    className="btn-ghost flex items-center gap-1.5 text-xs disabled:opacity-50"
                  >
                    {m.is_active ? <Ban size={12} /> : <CheckCircle2 size={12} />}
                    {busyId === m.id ? '...' : m.is_active ? 'Deactivate' : 'Activate'}
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {inviteOpen && (
        <InviteModal
          onClose={() => setInviteOpen(false)}
          onCreated={(creds) => {
            setInviteOpen(false)
            setNewCreds(creds)
            loadUsers()
          }}
        />
      )}

      {newCreds && <TempPasswordModal creds={newCreds} onClose={() => setNewCreds(null)} />}
    </GlassCard>
  )
}

function InviteModal({ onClose, onCreated }) {
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm({ resolver: zodResolver(inviteSchema), defaultValues: { role: 'analyst' } })

  const onSubmit = async (payload) => {
    try {
      const { data } = await fraudApi.createUser(payload)
      toast.success(`${data.user.full_name} added`)
      onCreated({ email: data.user.email, temporary_password: data.temporary_password })
    } catch (err) {
      toast.error(getApiErrorMessage(err, 'Failed to create user'))
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onClick={onClose}>
      <div onClick={(e) => e.stopPropagation()} className="glass-card w-full max-w-sm p-5">
        <h4 className="mb-4 font-display text-sm font-semibold">Invite Team Member</h4>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-3">
          <div>
            <label className="mb-1.5 block text-xs font-medium text-white/50">Full Name</label>
            <input {...register('full_name')} className="input-glass" />
            {errors.full_name && <p className="mt-1 text-xs text-danger">{errors.full_name.message}</p>}
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-white/50">Email</label>
            <input {...register('email')} className="input-glass" />
            {errors.email && <p className="mt-1 text-xs text-danger">{errors.email.message}</p>}
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-white/50">Role</label>
            <select {...register('role')} className="input-glass">
              <option value="analyst">Analyst</option>
              <option value="auditor">Auditor</option>
              <option value="admin">Admin</option>
            </select>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={onClose} className="btn-ghost text-sm">Cancel</button>
            <button type="submit" disabled={isSubmitting} className="btn-primary text-sm">
              {isSubmitting ? 'Creating...' : 'Create Account'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

function TempPasswordModal({ creds, onClose }) {
  const copy = () => {
    navigator.clipboard.writeText(creds.temporary_password)
    toast.success('Copied to clipboard')
  }
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onClick={onClose}>
      <div onClick={(e) => e.stopPropagation()} className="glass-card w-full max-w-sm p-5">
        <h4 className="mb-2 font-display text-sm font-semibold">Account Created</h4>
        <p className="mb-4 text-xs text-white/50">
          Share this temporary password with <span className="text-white/80">{creds.email}</span> — it can't be
          retrieved again after you close this window.
        </p>
        <div className="flex items-center justify-between rounded-xl border border-white/10 bg-white/[0.03] px-3.5 py-2.5">
          <code className="font-mono text-sm text-white/90">{creds.temporary_password}</code>
          <button onClick={copy} className="text-white/40 hover:text-white">
            <Copy size={14} />
          </button>
        </div>
        <div className="flex justify-end pt-4">
          <button onClick={onClose} className="btn-primary text-sm">Done</button>
        </div>
      </div>
    </div>
  )
}

// ------------------------------------------------------------------ //
// Model (admin only) — view active model metrics, trigger a retrain
// ------------------------------------------------------------------ //
function ModelTab() {
  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState(true)
  const [triggering, setTriggering] = useState(false)

  const loadStatus = useCallback(() => {
    fraudApi
      .getModelStatus()
      .then(({ data }) => setStatus(data))
      .catch((err) => toast.error(getApiErrorMessage(err, 'Failed to load model status')))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    loadStatus()
  }, [loadStatus])

  // Poll while a retrain is running so the page updates itself once it
  // finishes, without the admin needing to manually refresh.
  useEffect(() => {
    if (!status?.training_in_progress) return
    const interval = setInterval(loadStatus, 5000)
    return () => clearInterval(interval)
  }, [status?.training_in_progress, loadStatus])

  const handleRetrain = async () => {
    setTriggering(true)
    try {
      const { data } = await fraudApi.triggerRetrain()
      toast.success(data.message)
      loadStatus()
    } catch (err) {
      toast.error(getApiErrorMessage(err, 'Failed to start retraining'))
    } finally {
      setTriggering(false)
    }
  }

  const m = status?.active_model

  return (
    <GlassCard hover={false}>
      <div className="mb-5 flex items-center justify-between">
        <h3 className="font-display text-base font-semibold">Model</h3>
        <button
          onClick={handleRetrain}
          disabled={triggering || status?.training_in_progress}
          className="btn-primary flex items-center gap-1.5 text-xs disabled:opacity-50"
        >
          <RefreshCw size={14} className={status?.training_in_progress ? 'animate-spin' : ''} />
          {status?.training_in_progress ? 'Training…' : 'Retrain Model'}
        </button>
      </div>

      {status?.training_in_progress && (
        <div className="mb-5 rounded-xl border border-primary/25 bg-primary/5 px-4 py-3 text-sm text-white/70">
          A training run is in progress in the background — this page checks for updates automatically every few seconds.
        </div>
      )}

      {status?.last_training_error && !status.training_in_progress && (
        <div className="mb-5 rounded-xl border border-danger/25 bg-danger/5 px-4 py-3 text-sm text-danger">
          Last retrain attempt failed: {status.last_training_error}
        </div>
      )}

      {loading ? (
        <p className="py-8 text-center text-xs text-white/30">Loading…</p>
      ) : !m ? (
        <p className="py-8 text-center text-sm text-white/40">
          No model is currently registered as active. Run a retrain, or see the backend README for registering an
          already-trained model.
        </p>
      ) : (
        <>
          <div className="mb-5 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-white/10 bg-white/[0.02] p-4">
            <div>
              <p className="text-xs text-white/40">Active Version</p>
              <p className="font-display text-lg font-semibold">
                {m.version} <span className="text-sm font-normal capitalize text-white/40">({m.algorithm})</span>
              </p>
            </div>
            <div className="text-right text-xs text-white/40">
              <p>Trained {new Date(m.training_date).toLocaleString('en-IN')}</p>
              <p>{m.dataset_row_count.toLocaleString()} rows</p>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            {[
              { label: 'Accuracy', value: m.accuracy },
              { label: 'Precision', value: m.precision },
              { label: 'Recall', value: m.recall },
              { label: 'F1 Score', value: m.f1_score },
              { label: 'ROC-AUC', value: m.roc_auc },
              { label: 'PR-AUC', value: m.pr_auc },
            ].map(({ label, value }) => (
              <div key={label} className="rounded-xl border border-white/10 bg-white/[0.02] p-3.5">
                <p className="text-[11px] text-white/40">{label}</p>
                <p className="font-display text-lg font-semibold text-white/90">{(value * 100).toFixed(2)}%</p>
              </div>
            ))}
          </div>
        </>
      )}

      <p className="mt-5 border-t border-white/10 pt-4 text-xs text-white/30">
        Retraining runs in quick mode (fixed hyperparameters, no grid search) so it finishes in a reasonable
        window on the live server. It replaces the active model and deactivates the previous one automatically.
      </p>
    </GlassCard>
  )
}

// ------------------------------------------------------------------ //
// Shared
// ------------------------------------------------------------------ //
function ToggleRow({ title, desc, on = false, onChange, disabled = false, comingSoon = false }) {
  return (
    <div className="flex items-center justify-between rounded-xl border border-white/10 bg-white/[0.02] p-4">
      <div>
        <p className="flex items-center gap-2 text-sm font-medium text-white/85">
          {title}
          {comingSoon && <span className="rounded-full border border-white/10 bg-white/5 px-2 py-0.5 text-[10px] font-normal text-white/35">Coming soon</span>}
        </p>
        <p className="text-xs text-white/40">{desc}</p>
      </div>
      <button
        onClick={onChange}
        disabled={disabled}
        className={cn(
          'relative h-6 w-11 shrink-0 rounded-full transition-colors disabled:cursor-not-allowed disabled:opacity-40',
          on ? 'bg-primary' : 'bg-white/10'
        )}
      >
        <span className={cn('absolute left-0.5 top-0.5 h-5 w-5 rounded-full bg-white transition-transform', on ? 'translate-x-5' : 'translate-x-0')} />
      </button>
    </div>
  )
}
