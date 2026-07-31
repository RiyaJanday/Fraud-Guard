import { Doughnut } from 'react-chartjs-2'
import '../../lib/chartSetup'

const COLORS = ['#7C3AED', '#4F46E5', '#06B6D4', '#F59E0B', '#EF4444']

export default function FraudDoughnutChart({ data }) {
  const chartData = {
    labels: data.labels,
    datasets: [
      {
        data: data.values,
        backgroundColor: COLORS,
        borderColor: '#09090B',
        borderWidth: 3,
        hoverOffset: 10,
      },
    ],
  }

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    cutout: '68%',
    animation: { duration: 1200, easing: 'easeOutQuart' },
    plugins: {
      legend: {
        position: 'right',
        labels: { boxWidth: 8, boxHeight: 8, usePointStyle: true, pointStyle: 'circle', padding: 14, font: { size: 12 } },
      },
    },
  }

  return (
    <div className="h-72">
      <Doughnut data={chartData} options={options} />
    </div>
  )
}
