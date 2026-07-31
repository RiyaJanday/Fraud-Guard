import { Line } from 'react-chartjs-2'
import '../../lib/chartSetup'
import { CHART_COLORS } from '../../lib/chartSetup'

export default function RiskAreaChart({ data }) {
  const chartData = {
    labels: data.labels,
    datasets: [
      {
        label: 'Avg. Risk Score',
        data: data.values,
        borderColor: CHART_COLORS.primary,
        pointRadius: 0,
        borderWidth: 2.5,
        tension: 0.4,
        fill: true,
        backgroundColor: (ctx) => {
          const { chart } = ctx
          const { ctx: canvasCtx, chartArea } = chart
          if (!chartArea) return 'rgba(124,58,237,0.15)'
          const gradient = canvasCtx.createLinearGradient(0, chartArea.top, 0, chartArea.bottom)
          gradient.addColorStop(0, 'rgba(124,58,237,0.45)')
          gradient.addColorStop(1, 'rgba(124,58,237,0.02)')
          return gradient
        },
      },
    ],
  }

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 1200, easing: 'easeOutQuart' },
    plugins: { legend: { display: false } },
    scales: {
      x: { grid: { display: false } },
      y: { grid: { color: CHART_COLORS.grid }, border: { display: false }, suggestedMin: 0, suggestedMax: 100 },
    },
  }

  return (
    <div className="h-64">
      <Line data={chartData} options={options} />
    </div>
  )
}
