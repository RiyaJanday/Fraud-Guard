import { useMemo, useState } from 'react'
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getPaginationRowModel,
  flexRender,
} from '@tanstack/react-table'
import { ArrowUpDown, ChevronLeft, ChevronRight, Eye } from 'lucide-react'
import { motion } from 'framer-motion'
import StatusBadge from './StatusBadge'
import { formatCurrency, formatDateTime, riskLevel } from '../../lib/utils'

export default function TransactionTable({ data, onSelect, pageSize = 8 }) {
  const [sorting, setSorting] = useState([{ id: 'timestamp', desc: true }])

  const columns = useMemo(
    () => [
      {
        accessorKey: 'id',
        header: 'Transaction ID',
        cell: (info) => <span className="font-mono text-xs text-white/70">{info.getValue()}</span>,
      },
      {
        accessorKey: 'merchant',
        header: 'Merchant',
        cell: (info) => <span className="text-sm text-white/85">{info.getValue()}</span>,
      },
      {
        accessorKey: 'amount',
        header: 'Amount',
        cell: (info) => <span className="text-sm font-medium text-white">{formatCurrency(info.getValue())}</span>,
      },
      {
        accessorKey: 'timestamp',
        header: 'Time',
        cell: (info) => <span className="text-xs text-white/45">{formatDateTime(info.getValue())}</span>,
      },
      {
        accessorKey: 'risk',
        header: 'Risk Score',
        cell: (info) => {
          const value = info.getValue()
          const level = riskLevel(value)
          const barColor = level.color === 'danger' ? 'bg-danger' : level.color === 'warning' ? 'bg-warning' : 'bg-success'
          return (
            <div className="flex items-center gap-2">
              <div className="h-1.5 w-16 overflow-hidden rounded-full bg-white/10">
                <div className={`h-full rounded-full ${barColor}`} style={{ width: `${value}%` }} />
              </div>
              <span className="text-xs font-medium text-white/60">{value}</span>
            </div>
          )
        },
      },
      {
        accessorKey: 'status',
        header: 'Status',
        cell: (info) => <StatusBadge status={info.getValue()} />,
      },
      {
        id: 'action',
        header: 'Action',
        cell: ({ row }) => (
          <button
            onClick={() => onSelect(row.original)}
            className="flex items-center gap-1.5 rounded-lg border border-white/10 bg-white/[0.03] px-2.5 py-1.5 text-xs font-medium text-white/70 transition hover:border-primary/40 hover:text-white hover:bg-primary/10"
          >
            <Eye size={13} /> View
          </button>
        ),
      },
    ],
    [onSelect]
  )

  const table = useReactTable({
    data,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    initialState: { pagination: { pageSize } },
  })

  return (
    <div>
      <div className="overflow-x-auto rounded-xl border border-white/10">
        <table className="w-full min-w-[820px] border-collapse text-left">
          <thead>
            <tr className="border-b border-white/10 bg-white/[0.02]">
              {table.getHeaderGroups().map((hg) =>
                hg.headers.map((header) => (
                  <th
                    key={header.id}
                    onClick={header.column.getToggleSortingHandler()}
                    className="cursor-pointer select-none whitespace-nowrap px-4 py-3 text-xs font-semibold uppercase tracking-wide text-white/40"
                  >
                    <span className="flex items-center gap-1.5">
                      {flexRender(header.column.columnDef.header, header.getContext())}
                      {header.column.getCanSort() && <ArrowUpDown size={11} className="opacity-40" />}
                    </span>
                  </th>
                ))
              )}
            </tr>
          </thead>
          <tbody>
            {table.getRowModel().rows.map((row, i) => (
              <motion.tr
                key={row.id}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.25, delay: i * 0.03 }}
                onClick={() => onSelect(row.original)}
                className="cursor-pointer border-b border-white/5 transition-colors hover:bg-white/[0.03] last:border-0"
              >
                {row.getVisibleCells().map((cell) => (
                  <td key={cell.id} className="whitespace-nowrap px-4 py-3.5">
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </motion.tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="mt-4 flex items-center justify-between text-sm text-white/40">
        <span>
          Page {table.getState().pagination.pageIndex + 1} of {table.getPageCount()} · {data.length} transactions
        </span>
        <div className="flex items-center gap-2">
          <button
            onClick={() => table.previousPage()}
            disabled={!table.getCanPreviousPage()}
            className="flex h-8 w-8 items-center justify-center rounded-lg border border-white/10 bg-white/[0.03] disabled:opacity-30 hover:bg-white/[0.08]"
          >
            <ChevronLeft size={15} />
          </button>
          <button
            onClick={() => table.nextPage()}
            disabled={!table.getCanNextPage()}
            className="flex h-8 w-8 items-center justify-center rounded-lg border border-white/10 bg-white/[0.03] disabled:opacity-30 hover:bg-white/[0.08]"
          >
            <ChevronRight size={15} />
          </button>
        </div>
      </div>
    </div>
  )
}
