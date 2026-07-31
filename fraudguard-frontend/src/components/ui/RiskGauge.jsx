import { motion } from 'framer-motion'
import { riskLevel } from '../../lib/utils'

const COLORS = { success: '#22C55E', warning: '#F59E0B', danger: '#EF4444' }
const TEXT_CLASS = { success: 'text-success', warning: 'text-warning', danger: 'text-danger' }

export default function RiskGauge({ value = 24, size = 200 }) {
  const level = riskLevel(value)
  const radius = 80
  const circumference = Math.PI * radius
  const progress = Math.min(Math.max(value, 0), 100) / 100
  const strokeColor = COLORS[level.color]

  return (
    <div className="flex flex-col items-center">
      <svg width={size} height={size / 1.7} viewBox="0 0 220 130">
        <defs>
          <linearGradient id="gaugeTrack" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="#22C55E" />
            <stop offset="50%" stopColor="#F59E0B" />
            <stop offset="100%" stopColor="#EF4444" />
          </linearGradient>
        </defs>
        <path
          d="M 30 110 A 80 80 0 0 1 190 110"
          fill="none"
          stroke="rgba(255,255,255,0.08)"
          strokeWidth="16"
          strokeLinecap="round"
        />
        <path
          d="M 30 110 A 80 80 0 0 1 190 110"
          fill="none"
          stroke="url(#gaugeTrack)"
          strokeOpacity="0.35"
          strokeWidth="16"
          strokeLinecap="round"
        />
        <motion.path
          d="M 30 110 A 80 80 0 0 1 190 110"
          fill="none"
          stroke={strokeColor}
          strokeWidth="16"
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: circumference * (1 - progress) }}
          transition={{ duration: 1.4, ease: [0.22, 1, 0.36, 1] }}
          style={{ filter: `drop-shadow(0 0 8px ${strokeColor}80)` }}
        />
        <motion.g
          initial={{ rotate: -90 }}
          animate={{ rotate: -90 + progress * 180 }}
          transition={{ duration: 1.4, ease: [0.22, 1, 0.36, 1] }}
          style={{ transformOrigin: '110px 110px' }}
        >
          <line x1="110" y1="110" x2="110" y2="42" stroke="white" strokeWidth="3" strokeLinecap="round" />
          <circle cx="110" cy="110" r="6" fill="white" />
        </motion.g>
      </svg>
      <div className="-mt-4 text-center">
        <p className="font-display text-4xl font-bold text-white">{value}</p>
        <p className={`text-sm font-medium ${TEXT_CLASS[level.color]}`}>{level.label} Risk</p>
      </div>
    </div>
  )
}
