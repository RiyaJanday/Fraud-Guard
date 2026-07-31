import { Line } from 'react-chartjs-2'
import '../../lib/chartSetup'
import { CHART_COLORS } from '../../lib/chartSetup'

export default function RiskTimelineChart({ data }) {
  const chartData = {
    labels: data.labels,
    datasets: [
      {
        data: data.values,
        borderColor: CHART_COLORS.secondary,
        backgroundColor: 'rgba(79,70,229,0.1)',
        pointRadius: 0,
        borderWidth: 2,
        tension: 0.35,
        fill: true,
      },
    ],
  }
  const options = {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 1000 },
    plugins: { legend: { display: false } },
    scales: {
      x: { display: false },
      y: { display: false, suggestedMin: 0, suggestedMax: 100 },
    },
  }
  return (
    <div className="h-32">
      <Line data={chartData} options={options} />
    </div>
  )
}
