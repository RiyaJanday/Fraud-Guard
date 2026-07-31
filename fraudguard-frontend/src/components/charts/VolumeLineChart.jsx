import { Line } from 'react-chartjs-2'
import '../../lib/chartSetup'
import { CHART_COLORS } from '../../lib/chartSetup'

export default function VolumeLineChart({ data }) {
  const chartData = {
    labels: data.labels,
    datasets: [
      {
        label: 'Legitimate',
        data: data.legit,
        borderColor: CHART_COLORS.accent,
        backgroundColor: 'rgba(6,182,212,0.12)',
        pointRadius: 0,
        borderWidth: 2.5,
        tension: 0.4,
        fill: true,
      },
      {
        label: 'Flagged',
        data: data.fraud,
        borderColor: CHART_COLORS.danger,
        backgroundColor: 'rgba(239,68,68,0.12)',
        pointRadius: 0,
        borderWidth: 2.5,
        tension: 0.4,
        fill: true,
      },
    ],
  }

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 1200, easing: 'easeOutQuart' },
    interaction: { mode: 'index', intersect: false },
    plugins: {
      legend: {
        position: 'top',
        align: 'end',
        labels: { boxWidth: 8, boxHeight: 8, usePointStyle: true, pointStyle: 'circle', padding: 16 },
      },
    },
    scales: {
      x: { grid: { display: false }, ticks: { maxTicksLimit: 8 } },
      y: { grid: { color: CHART_COLORS.grid }, border: { display: false } },
    },
  }

  return (
    <div className="h-72">
      <Line data={chartData} options={options} />
    </div>
  )
}
