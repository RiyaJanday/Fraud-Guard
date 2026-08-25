import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { Sliders, Plus, Trash2, X, Power } from 'lucide-react'
import PageHeader from '../components/ui/PageHeader'
import GlassCard from '../components/ui/GlassCard'
import { fraudApi, getApiErrorMessage } from '../lib/api'
import { cn, formatDateTime } from '../lib/utils'
import { useAuth } from '../context/AuthContext'

const FIELD_OPTIONS = [
  { value: 'amount', label: 'Amount', numeric: true },
  { value: 'currency', label: 'Currency' },
  { value: 'merchant', label: 'Merchant' },
  { value: 'customer_reference', label: 'Customer Reference' },
  { value: 'card_last4', label: 'Card Last 4' },
  { value: 'device_info', label: 'Device Info' },
  { value: 'ip_address', label: 'IP Address' },
  { value: 'location', label: 'Location' },
  { value: 'time_feature', label: 'Time (seconds elapsed)', numeric: true },
]

const NUMERIC_OPERATORS = [
  { value: 'gt', label: '> greater than' },
  { value: 'gte', label: '>= greater or equal' },
  { value: 'lt', label: '< less than' },
  { value: 'lte', label: '<= less or equal' },
  { value: 'eq', label: '= equals' },
  { value: 'neq', label: '!= not equal' },
]

const TEXT_OPERATORS = [
  { value: 'eq', label: '= equals' },
  { value: 'neq', label: '!= not equal' },
  { value: 'contains', label: 'contains' },
]

const ACTION_META = {
  notify: { label: 'Notify', className: 'badge-success', hint: 'Just sends a notification — decision unchanged.' },
  flag: { label: 'Flag for Review', className: 'badge-warning', hint: "Pushes into the review queue if it wasn't already headed there." },
  block: { label: 'Block', className: 'badge-danger', hint: 'Hard override — forces the transaction to Blocked.' },
}

const emptyForm = { name: '', field: 'amount', operator: 'gt', value: '', action: 'flag' }

export default function Rules() {
  const { user } = useAuth()
  const isAdmin = user?.role === 'admin'

  const [rules, setRules] = useState([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState(emptyForm)
  const [saving, setSaving] = useState(false)
  const [busyId, setBusyId] = useState(null)

  function load() {
    setLoading(true)
    fraudApi
      .listRules()
      .then(({ data }) => setRules(data.items))
      .catch((err) => toast.error(getApiErrorMessage(err, 'Could not load rules')))
      .finally(() => setLoading(false))
  }

  useEffect(load, [])

  const fieldMeta = FIELD_OPTIONS.find((f) => f.value === form.field)
  const operatorOptions = fieldMeta?.numeric ? NUMERIC_OPERATORS : TEXT_OPERATORS

  async function handleCreate(e) {
    e.preventDefault()
    if (!form.name.trim() || !form.value.trim()) {
      toast.error('Give the rule a name and a value to compare against')
      return
    }
    setSaving(true)
    try {
      await fraudApi.createRule(form)
      toast.success('Rule created — active immediately on the next transaction scored')
      setForm(emptyForm)
      setShowForm(false)
      load()
    } catch (err) {
      toast.error(getApiErrorMessage(err, 'Could not create this rule'))
    } finally {
      setSaving(false)
    }
  }

  async function handleToggle(rule) {
    setBusyId(rule.id)
    try {
      await fraudApi.updateRule(rule.id, { enabled: !rule.enabled })
      setRules((rs) => rs.map((r) => (r.id === rule.id ? { ...r, enabled: !r.enabled } : r)))
    } catch (err) {
      toast.error(getApiErrorMessage(err, 'Could not update this rule'))
    } finally {
      setBusyId(null)
    }
  }

  async function handleDelete(rule) {
    if (!window.confirm(`Delete rule "${rule.name}"? This can't be undone.`)) return
    setBusyId(rule.id)
    try {
      await fraudApi.deleteRule(rule.id)
      toast.success('Rule deleted')
      setRules((rs) => rs.filter((r) => r.id !== rule.id))
    } catch (err) {
      toast.error(getApiErrorMessage(err, 'Could not delete this rule'))
    } finally {
      setBusyId(null)
    }
  }

  return (
    <div>
      <PageHeader
        eyebrow="Policy"
        title="Business Rules"
        subtitle="Hard-coded policy that runs alongside the ML model on every transaction — for logic you never want left to a probability score, like always blocking a first-time merchant over a set amount."
        actions={
          isAdmin && (
            <button onClick={() => setShowForm((v) => !v)} className="btn-primary text-sm">
              <Plus size={15} /> New Rule
            </button>
          )
        }
      />

      {showForm && isAdmin && (
        <GlassCard hover={false} className="mb-6">
          <form onSubmit={handleCreate} className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
            <div className="sm:col-span-2 lg:col-span-5">
              <label className="mb-1.5 block text-xs font-medium text-white/50">Rule Name</label>
              <input
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                placeholder="e.g. Block large first-time transactions"
                className="input-glass"
              />
            </div>

            <div>
              <label className="mb-1.5 block text-xs font-medium text-white/50">Field</label>
              <select
                value={form.field}
                onChange={(e) => {
                  const next = e.target.value
                  const nextNumeric = FIELD_OPTIONS.find((f) => f.value === next)?.numeric
                  setForm((f) => ({ ...f, field: next, operator: nextNumeric ? 'gt' : 'eq' }))
                }}
                className="input-glass"
              >
                {FIELD_OPTIONS.map((f) => (
                  <option key={f.value} value={f.value}>{f.label}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="mb-1.5 block text-xs font-medium text-white/50">Operator</label>
              <select
                value={form.operator}
                onChange={(e) => setForm((f) => ({ ...f, operator: e.target.value }))}
                className="input-glass"
              >
                {operatorOptions.map((o) => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="mb-1.5 block text-xs font-medium text-white/50">Value</label>
              <input
                value={form.value}
                onChange={(e) => setForm((f) => ({ ...f, value: e.target.value }))}
                placeholder={fieldMeta?.numeric ? '50000' : 'e.g. Unknown Merchant'}
                className="input-glass"
              />
            </div>

            <div>
              <label className="mb-1.5 block text-xs font-medium text-white/50">Action</label>
              <select
                value={form.action}
                onChange={(e) => setForm((f) => ({ ...f, action: e.target.value }))}
                className="input-glass"
              >
                {Object.entries(ACTION_META).map(([value, meta]) => (
                  <option key={value} value={value}>{meta.label}</option>
                ))}
              </select>
            </div>

            <div className="flex items-end gap-3 sm:col-span-2 lg:col-span-5">
              <button type="submit" disabled={saving} className="btn-primary text-sm disabled:opacity-50">
                {saving ? 'Creating…' : 'Create Rule'}
              </button>
              <button type="button" onClick={() => setShowForm(false)} className="btn-ghost text-sm">
                Cancel
              </button>
              <p className="text-xs text-white/35">{ACTION_META[form.action].hint}</p>
            </div>
          </form>
        </GlassCard>
      )}

      <GlassCard hover={false}>
        {loading ? (
          <p className="py-10 text-center text-sm text-white/40">Loading…</p>
        ) : rules.length === 0 ? (
          <div className="flex flex-col items-center gap-3 py-10 text-center">
            <Sliders size={28} className="text-white/25" />
            <p className="text-sm text-white/40">No rules configured yet — every decision comes purely from the model.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/10 text-left text-xs uppercase tracking-wide text-white/35">
                  <th className="pb-3 pr-4 font-medium">Rule</th>
                  <th className="pb-3 pr-4 font-medium">Condition</th>
                  <th className="pb-3 pr-4 font-medium">Action</th>
                  <th className="pb-3 pr-4 font-medium">Created By</th>
                  <th className="pb-3 pr-4 font-medium">Status</th>
                  {isAdmin && <th className="pb-3 font-medium" />}
                </tr>
              </thead>
              <tbody>
                {rules.map((r) => {
                  const fieldLabel = FIELD_OPTIONS.find((f) => f.value === r.field)?.label || r.field
                  const opLabel = [...NUMERIC_OPERATORS, ...TEXT_OPERATORS].find((o) => o.value === r.operator)?.label || r.operator
                  return (
                    <tr key={r.id} className="border-b border-white/5 last:border-0">
                      <td className="py-3 pr-4">
                        <p className="text-white/80">{r.name}</p>
                        <p className="text-xs text-white/35">{formatDateTime(r.created_at)}</p>
                      </td>
                      <td className="py-3 pr-4 font-mono text-xs text-white/60">
                        {fieldLabel} {opLabel.split(' ')[0]} "{r.value}"
                      </td>
                      <td className="py-3 pr-4">
                        <span className={cn('badge text-[10px]', ACTION_META[r.action]?.className)}>
                          {ACTION_META[r.action]?.label || r.action}
                        </span>
                      </td>
                      <td className="py-3 pr-4 text-white/60">{r.created_by_name || '—'}</td>
                      <td className="py-3 pr-4">
                        <span className={cn('badge text-[10px]', r.enabled ? 'badge-success' : 'border border-white/10 bg-white/5 text-white/40')}>
                          {r.enabled ? 'Active' : 'Disabled'}
                        </span>
                      </td>
                      {isAdmin && (
                        <td className="py-3 text-right">
                          <div className="flex items-center justify-end gap-2">
                            <button
                              onClick={() => handleToggle(r)}
                              disabled={busyId === r.id}
                              title={r.enabled ? 'Disable' : 'Enable'}
                              className="btn-ghost px-2.5 py-1.5 text-xs disabled:opacity-50"
                            >
                              <Power size={13} />
                            </button>
                            <button
                              onClick={() => handleDelete(r)}
                              disabled={busyId === r.id}
                              title="Delete"
                              className="btn-ghost px-2.5 py-1.5 text-xs text-danger hover:border-danger/30 hover:bg-danger/10 disabled:opacity-50"
                            >
                              <Trash2 size={13} />
                            </button>
                          </div>
                        </td>
                      )}
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </GlassCard>
    </div>
  )
}
