import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Search, SlidersHorizontal, Download } from 'lucide-react'
import toast from 'react-hot-toast'
import PageHeader from '../components/ui/PageHeader'
import GlassCard from '../components/ui/GlassCard'
import TransactionTable from '../components/transactions/TransactionTable'
import TransactionDrawer from '../components/transactions/TransactionDrawer'
import { fraudApi } from '../lib/api'
import { mapTransactionListItem, mapTransactionDetail, statusToDecision } from '../lib/transform'
import { cn, downloadBlobResponse } from '../lib/utils'

const FILTERS = [
  { id: 'all', label: 'All' },
  { id: 'approved', label: 'Approved' },
  { id: 'mfa', label: 'MFA Required' },
  { id: 'blocked', label: 'Blocked' },
]

export default function Transactions() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [selectedId, setSelectedId] = useState(null)
  const [selected, setSelected] = useState(null)
  // Seeded from ?q= so the Topbar's global search can deep-link straight
  // into a filtered result set here (there's no separate search results page).
  const [query, setQuery] = useState(() => searchParams.get('q') || '')
  const [filter, setFilter] = useState('all')
  const [rows, setRows] = useState([])
  const [loading, setLoading] = useState(true)
  const [exporting, setExporting] = useState(false)

  async function handleExportCsv() {
    setExporting(true)
    try {
      const response = await fraudApi.exportTransactionsCsv({ decision: statusToDecision(filter) || undefined })
      downloadBlobResponse(response, 'fraudguard-transactions.csv')
      toast.success('CSV downloaded')
    } catch (err) {
      toast.error('Could not export transactions')
    } finally {
      setExporting(false)
    }
  }

  // Keep the URL's ?q= in sync with the search box so the current search is
  // shareable/bookmarkable and survives a refresh.
  useEffect(() => {
    setSearchParams(query ? { q: query } : {}, { replace: true })
  }, [query]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    let cancelled = false
    const timer = setTimeout(() => {
      setLoading(true)
      fraudApi
        .getTransactions({
          page: 1,
          page_size: 100,
          decision: statusToDecision(filter) || undefined,
          merchant: query || undefined,
        })
        .then(({ data }) => {
          if (!cancelled) setRows(data.items.map(mapTransactionListItem))
        })
        .catch(() => {
          if (!cancelled) toast.error('Could not load transactions from the backend')
        })
        .finally(() => {
          if (!cancelled) setLoading(false)
        })
    }, 300) // debounce search typing

    return () => { cancelled = true; clearTimeout(timer) }
  }, [query, filter])

  useEffect(() => {
    if (!selectedId) {
      setSelected(null)
      return
    }
    let cancelled = false
    fraudApi.getTransaction(selectedId).then(({ data }) => {
      if (!cancelled) setSelected(mapTransactionDetail(data))
    }).catch(() => {
      if (!cancelled) toast.error('Could not load transaction detail')
    })
    return () => { cancelled = true }
  }, [selectedId])

  return (
    <div>
      <PageHeader
        eyebrow="Payments"
        title="Transactions"
        subtitle="Search, filter and review every transaction scored by the FraudGuard engine."
        actions={
          <button onClick={handleExportCsv} disabled={exporting} className="btn-ghost text-sm disabled:opacity-50">
            <Download size={15} /> {exporting ? 'Exporting…' : 'Export CSV'}
          </button>
        }
      />

      <GlassCard hover={false}>
        <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex w-full max-w-sm items-center gap-2 rounded-xl border border-white/10 bg-white/[0.03] px-3.5 py-2.5">
            <Search size={16} className="text-white/30" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search by merchant..."
              className="w-full bg-transparent text-sm text-white placeholder:text-white/30 outline-none"
            />
          </div>
          <div className="flex items-center gap-2 overflow-x-auto">
            <SlidersHorizontal size={15} className="shrink-0 text-white/30" />
            {FILTERS.map((f) => (
              <button
                key={f.id}
                onClick={() => setFilter(f.id)}
                className={cn(
                  'shrink-0 rounded-lg px-3 py-1.5 text-xs font-medium transition',
                  filter === f.id
                    ? 'bg-primary/20 text-white border border-primary/40'
                    : 'border border-white/10 bg-white/[0.02] text-white/50 hover:text-white'
                )}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>

        {loading ? (
          <div className="flex justify-center py-10">
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-white/10 border-t-primary" />
          </div>
        ) : rows.length ? (
          <TransactionTable data={rows} onSelect={(t) => setSelectedId(t.id)} pageSize={10} />
        ) : (
          <p className="py-10 text-center text-sm text-white/40">No transactions match these filters.</p>
        )}
      </GlassCard>

      <TransactionDrawer transaction={selected} onClose={() => setSelectedId(null)} />
    </div>
  )
}
