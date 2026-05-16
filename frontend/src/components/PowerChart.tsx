import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { PowerSnapshot } from '@/types'

interface PowerChartProps {
  snapshots: PowerSnapshot[]
}

export function PowerChart({ snapshots }: PowerChartProps) {
  const data = [...snapshots]
    .reverse()
    .map((s) => ({
      time: new Date(s.timestamp).toLocaleTimeString(),
      'Power (W)': s.power_watts,
      'Load (%)': s.load_percent,
      'Battery (%)': s.battery_percent,
    }))

  if (data.length === 0) {
    return <div className="chart-empty">No snapshot data yet.</div>
  }

  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
        <XAxis dataKey="time" tick={{ fontSize: 11 }} />
        <YAxis tick={{ fontSize: 11 }} />
        <Tooltip />
        <Legend />
        <Line type="monotone" dataKey="Power (W)" stroke="#f59e0b" dot={false} />
        <Line type="monotone" dataKey="Load (%)" stroke="#3b82f6" dot={false} />
        <Line type="monotone" dataKey="Battery (%)" stroke="#10b981" dot={false} />
      </LineChart>
    </ResponsiveContainer>
  )
}
