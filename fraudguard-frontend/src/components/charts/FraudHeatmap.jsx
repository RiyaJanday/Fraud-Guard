import { motion } from 'framer-motion'
import { HEATMAP_HOURS } from '../../data/mockData'

function intensityColor(value) {
  if (value >= 75) return 'bg-danger'
  if (value >= 50) return 'bg-warning'
  if (value >= 25) return 'bg-primary'
  return 'bg-accent/60'
}

export default function FraudHeatmap({ data, hours }) {
  const hourLabels = hours && hours.length ? hours : HEATMAP_HOURS
  return (
    <div>
      <div className="flex gap-2 pl-12">
        {hourLabels.map((h) => (
          <div key={h} className="flex-1 text-center text-[11px] text-white/35">
            {h}
          </div>
        ))}
      </div>
      <div className="mt-2 space-y-1.5">
        {data.map((row, ri) => (
          <div key={row.day} className="flex items-center gap-2">
            <span className="w-9 shrink-0 text-xs text-white/40">{row.day}</span>
            <div className="grid flex-1 grid-cols-6 gap-1.5">
              {row.values.map((v, ci) => (
                <motion.div
                  key={ci}
                  initial={{ opacity: 0, scale: 0.6 }}
                  whileInView={{ opacity: 1, scale: 1 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.3, delay: (ri * 6 + ci) * 0.012 }}
                  whileHover={{ scale: 1.15 }}
                  className={`group relative h-7 rounded-md ${intensityColor(v)} cursor-pointer`}
                  style={{ opacity: 0.25 + (v / 100) * 0.75 }}
                >
                  <div className="pointer-events-none absolute -top-8 left-1/2 z-10 -translate-x-1/2 whitespace-nowrap rounded-lg border border-white/10 bg-bg-card/95 px-2 py-1 text-[11px] font-medium text-white opacity-0 shadow-card transition-opacity group-hover:opacity-100">
                    {v} events
                  </div>
                </motion.div>
              ))}
            </div>
          </div>
        ))}
      </div>
      <div className="mt-4 flex items-center justify-end gap-4 text-[11px] text-white/40">
        <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm bg-accent/60" /> Low</span>
        <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm bg-primary" /> Medium</span>
        <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm bg-warning" /> High</span>
        <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm bg-danger" /> Critical</span>
      </div>
    </div>
  )
}
