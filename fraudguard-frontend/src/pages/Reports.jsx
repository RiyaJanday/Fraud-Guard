import { useState } from 'react'
import toast from 'react-hot-toast'
import { FileText, Table2, Download, Loader2 } from 'lucide-react'
import PageHeader from '../components/ui/PageHeader'
import GlassCard from '../components/ui/GlassCard'
import { fraudApi } from '../lib/api'
import { downloadBlobResponse } from '../lib/utils'
import { statusToDecision } from '../lib/transform'

// ISO datetime the backend expects, built from a plain <input type="date">
// value — "" means "no boundary", so we only append the time-of-day and
// convert to UTC when the user actually picked a date.
function toIsoOrUndefined(dateStr, endOfDay = false) {
  if (!dateStr) return undefined
  const time = endOfDay ? '23:59:59' : '00:00:00'
  return new Date(`${dateStr}T${time}`).toISOString()
}

function DateRangeFields({ from, to, onFrom, onTo }) {
  return (
    <div className="grid grid-cols-2 gap-2">
      <div>
        <label className="mb-1 block text-[11px] text-white/40">From</label>
        <input
          type="date"
          value={from}
          onChange={(e) => onFrom(e.target.value)}
          className="w-full rounded-lg border border-white/10 bg-white/[0.03] px-2.5 py-1.5 text-xs text-white/80 outline-none focus:border-primary/40"
        />
      </div>
      <div>
        <label className="mb-1 block text-[11px] text-white/40">To</label>
        <input
          type="date"
          value={to}
          onChange={(e) => onTo(e.target.value)}
          className="w-full rounded-lg border border-white/10 bg-white/[0.03] px-2.5 py-1.5 text-xs text-white/80 outline-none focus:border-primary/40"
        />
      </div>
    </div>
  )
}

function SummaryReportCard() {
  const [from, setFrom] = useState('')
  const [to, setTo] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleDownload() {
    setLoading(true)
    try {
      const response = await fraudApi.exportSummaryPdf({
        date_from: toIsoOrUndefined(from),
        date_to: toIsoOrUndefined(to, true),
      })
      downloadBlobResponse(response, 'fraudguard-summary.pdf')
      toast.success('Summary report downloaded')
    } catch (err) {
      toast.error(err?.response?.data?.detail?.message || 'Could not generate report')
    } finally {
      setLoading(false)
    }
  }

  return (
    <GlassCard className="flex flex-col justify-between">
      <div>
        <div className="mb-3 flex items-start justify-between">
          <div className="rounded-xl border border-white/10 bg-white/[0.04] p-2.5 text-primary">
            <FileText size={18} />
          </div>
          <span className="badge text-accent bg-accent/10 border-accent/30">PDF</span>
        </div>
        <h3 className="font-display text-base font-semibold text-white">Fraud Summary Report</h3>
        <p className="mt-1 text-xs text-white/40">
          Headline stats, decision distribution, and top flagged merchants for the selected period.
        </p>
        <div className="mt-4">
          <DateRangeFields from={from} to={to} onFrom={setFrom} onTo={setTo} />
          <p className="mt-2 text-[11px] text-white/30">Leave blank for all-time.</p>
        </div>
      </div>
      <div className="mt-5 flex items-center justify-between border-t border-white/5 pt-4">
        <span className="text-xs text-white/30">Generated on demand</span>
        <button
          onClick={handleDownload}
          disabled={loading}
          className="flex items-center gap-1.5 rounded-lg border border-white/10 bg-white/[0.03] px-3 py-1.5 text-xs font-medium text-white/70 transition hover:border-primary/40 hover:text-white hover:bg-primary/10 disabled:opacity-50"
        >
          {loading ? <Loader2 size={13} className="animate-spin" /> : <Download size={13} />}
          {loading ? 'Generating…' : 'Download PDF'}
        </button>
      </div>
    </GlassCard>
  )
}

function TransactionsCsvCard() {
  const [from, setFrom] = useState('')
  const [to, setTo] = useState('')
  const [status, setStatus] = useState('All')
  const [loading, setLoading] = useState(false)

  async function handleDownload() {
    setLoading(true)
    try {
      const response = await fraudApi.exportTransactionsCsv({
        decision: statusToDecision(status.toLowerCase()) || undefined,
        date_from: toIsoOrUndefined(from),
        date_to: toIsoOrUndefined(to, true),
      })
      downloadBlobResponse(response, 'fraudguard-transactions.csv')
      toast.success('Transaction export downloaded')
    } catch (err) {
      toast.error(err?.response?.data?.detail?.message || 'Could not export transactions')
    } finally {
      setLoading(false)
    }
  }

  return (
    <GlassCard delay={0.05} className="flex flex-col justify-between">
      <div>
        <div className="mb-3 flex items-start justify-between">
          <div className="rounded-xl border border-white/10 bg-white/[0.04] p-2.5 text-primary">
            <Table2 size={18} />
          </div>
          <span className="badge text-success bg-success/10 border-success/30">CSV</span>
        </div>
        <h3 className="font-display text-base font-semibold text-white">Transaction Export</h3>
        <p className="mt-1 text-xs text-white/40">
          Raw transaction-level data — amount, risk score, decision, and model version per row.
        </p>
        <div className="mt-4 space-y-3">
          <DateRangeFields from={from} to={to} onFrom={setFrom} onTo={setTo} />
          <div>
            <label className="mb-1 block text-[11px] text-white/40">Decision</label>
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              className="w-full rounded-lg border border-white/10 bg-white/[0.03] px-2.5 py-1.5 text-xs text-white/80 outline-none focus:border-primary/40"
            >
              <option value="All">All</option>
              <option value="approved">Approved</option>
              <option value="mfa">MFA Required</option>
              <option value="blocked">Blocked</option>
            </select>
          </div>
        </div>
      </div>
      <div className="mt-5 flex items-center justify-between border-t border-white/5 pt-4">
        <span className="text-xs text-white/30">Up to 10,000 rows</span>
        <button
          onClick={handleDownload}
          disabled={loading}
          className="flex items-center gap-1.5 rounded-lg border border-white/10 bg-white/[0.03] px-3 py-1.5 text-xs font-medium text-white/70 transition hover:border-primary/40 hover:text-white hover:bg-primary/10 disabled:opacity-50"
        >
          {loading ? <Loader2 size={13} className="animate-spin" /> : <Download size={13} />}
          {loading ? 'Generating…' : 'Download CSV'}
        </button>
      </div>
    </GlassCard>
  )
}

export default function Reports() {
  return (
    <div>
      <PageHeader
        eyebrow="Compliance"
        title="Reports"
        subtitle="Generate and download real fraud reports straight from live data — no pre-baked files."
      />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <SummaryReportCard />
        <TransactionsCsvCard />
      </div>
    </div>
  )
}
