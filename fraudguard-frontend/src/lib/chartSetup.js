import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  RadialLinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Filler,
  Tooltip,
  Legend,
} from 'chart.js'

ChartJS.register(
  CategoryScale,
  LinearScale,
  RadialLinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Filler,
  Tooltip,
  Legend
)

ChartJS.defaults.font.family = "'Outfit', sans-serif"
ChartJS.defaults.color = 'rgba(255,255,255,0.45)'
ChartJS.defaults.plugins.tooltip.backgroundColor = 'rgba(15,15,20,0.95)'
ChartJS.defaults.plugins.tooltip.borderColor = 'rgba(255,255,255,0.1)'
ChartJS.defaults.plugins.tooltip.borderWidth = 1
ChartJS.defaults.plugins.tooltip.padding = 10
ChartJS.defaults.plugins.tooltip.cornerRadius = 10
ChartJS.defaults.plugins.tooltip.titleFont = { family: "'Outfit', sans-serif", weight: '600' }
ChartJS.defaults.plugins.tooltip.bodyFont = { family: "'Outfit', sans-serif" }
ChartJS.defaults.plugins.tooltip.displayColors = true

export const CHART_COLORS = {
  primary: '#7C3AED',
  secondary: '#4F46E5',
  accent: '#06B6D4',
  success: '#22C55E',
  warning: '#F59E0B',
  danger: '#EF4444',
  grid: 'rgba(255,255,255,0.06)',
}

export default ChartJS
