import { useState } from 'react'
import toast from 'react-hot-toast'
import { FileText, Download, Calendar, Filter } from 'lucide-react'
import PageHeader from '../components/ui/PageHeader'
import GlassCard from '../components/ui/GlassCard'
import { formatDateTime } from '../lib/utils'

const REPORTS = [
  { id: 1, title: 'Weekly Fraud Summary', range: 'Jul 7 – Jul 13, 2026', type: 'Summary', size: '1.2 MB', generated: '2026-07-14T06:00:00' },
  { id: 2, title: 'Model Performance Audit', range: 'Q2 2026', type: 'Compliance', size: '3.8 MB', generated: '2026-07-10T09:30:00' },
  { id: 3, title: 'High-Risk Merchant Review', range: 'Jun 2026', type: 'Analytics', size: '890 KB', generated: '2026-07-01T14:12:00' },
  { id: 4, title: 'Chargeback Reconciliation', range: 'Jun 2026', type: 'Finance', size: '2.1 MB', generated: '2026-06-30T18:45:00' },
  { id: 5, title: 'SHAP Model Explainability Report', range: 'May 2026', type: 'Compliance', size: '4.4 MB', generated: '2026-06-02T11:05:00' },
  { id: 6, title: 'Regional Risk Exposure', range: 'Q1 2026', type: 'Analytics', size: '1.6 MB', generated: '2026-04-05T08:20:00' },
]

const TYPE_COLOR = {
  Summary: 'text-accent bg-accent/10 border-accent/30',
  Compliance: 'text-primary bg-primary/10 border-primary/30',
  Analytics: 'text-warning bg-warning/10 border-warning/30',
  Finance: 'text-success bg-success/10 border-success/30',
}

export default function Reports() {
  const [filter, setFilter] = useState('All')
  const types = ['All', ...new Set(REPORTS.map((r) => r.type))]
  const filtered = filter === 'All' ? REPORTS : REPORTS.filter((r) => r.type === filter)

  return (
    <div>
      <PageHeader
        eyebrow="Compliance"
        title="Reports"
        subtitle="Generated fraud, compliance and performance reports ready for download."
        actions={
          <button onClick={() => toast.success('Custom report queued for generation')} className="btn-primary text-sm">
            <FileText size={15} /> Generate Report
          </button>
        }
      />

      <div className="mb-5 flex flex-wrap items-center gap-2">
        <Filter size={14} className="text-white/30" />
        {types.map((t) => (
          <button
            key={t}
            onClick={() => setFilter(t)}
            className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${
              filter === t
                ? 'border border-primary/40 bg-primary/20 text-white'
                : 'border border-white/10 bg-white/[0.02] text-white/50 hover:text-white'
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {filtered.map((r, i) => (
          <GlassCard key={r.id} delay={i * 0.04} className="flex flex-col justify-between">
            <div>
              <div className="mb-3 flex items-start justify-between">
                <div className="rounded-xl border border-white/10 bg-white/[0.04] p-2.5 text-primary">
                  <FileText size={18} />
                </div>
                <span className={`badge ${TYPE_COLOR[r.type]}`}>{r.type}</span>
              </div>
              <h3 className="font-display text-base font-semibold text-white">{r.title}</h3>
              <p className="mt-1 flex items-center gap-1.5 text-xs text-white/40">
                <Calendar size={12} /> {r.range}
              </p>
              <p className="mt-3 text-xs text-white/30">Generated {formatDateTime(r.generated)}</p>
            </div>
            <div className="mt-5 flex items-center justify-between border-t border-white/5 pt-4">
              <span className="text-xs text-white/30">{r.size} · PDF</span>
              <button
                onClick={() => toast.success(`Downloading "${r.title}"`)}
                className="flex items-center gap-1.5 rounded-lg border border-white/10 bg-white/[0.03] px-3 py-1.5 text-xs font-medium text-white/70 transition hover:border-primary/40 hover:text-white hover:bg-primary/10"
              >
                <Download size={13} /> Download
              </button>
            </div>
          </GlassCard>
        ))}
      </div>
    </div>
  )
}
