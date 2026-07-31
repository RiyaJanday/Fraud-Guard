import { Radar } from 'react-chartjs-2'
import '../../lib/chartSetup'
import { CHART_COLORS } from '../../lib/chartSetup'

export default function PerformanceRadarChart({ data }) {
  const chartData = {
    labels: data.labels,
    datasets: [
      {
        label: 'Model Score',
        data: data.values,
        borderColor: CHART_COLORS.accent,
        backgroundColor: 'rgba(6,182,212,0.18)',
        pointBackgroundColor: CHART_COLORS.accent,
        pointBorderColor: '#09090B',
        pointRadius: 4,
        borderWidth: 2,
      },
    ],
  }

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 1200, easing: 'easeOutQuart' },
    plugins: { legend: { display: false } },
    scales: {
      r: {
        angleLines: { color: CHART_COLORS.grid },
        grid: { color: CHART_COLORS.grid },
        pointLabels: { color: 'rgba(255,255,255,0.55)', font: { size: 11 } },
        ticks: { display: false, backdropColor: 'transparent' },
        suggestedMin: 0,
        suggestedMax: 100,
      },
    },
  }

  return (
    <div className="h-72">
      <Radar data={chartData} options={options} />
    </div>
  )
}
