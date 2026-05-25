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
  readonly snapshots: PowerSnapshot[]
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
    return <p className="text-slate-500 text-sm py-8 text-center">No snapshot data yet.</p>
  }

  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
        <XAxis dataKey="time" tick={{ fontSize: 11, fill: '#94a3b8' }} />
        <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} />
        <Tooltip
          contentStyle={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px' }}
          labelStyle={{ color: '#94a3b8' }}
        />
        <Legend wrapperStyle={{ fontSize: '12px', color: '#94a3b8' }} />
        <Line type="monotone" dataKey="Power (W)" stroke="#f59e0b" dot={false} strokeWidth={1.5} />
        <Line type="monotone" dataKey="Load (%)" stroke="#3b82f6" dot={false} strokeWidth={1.5} />
        <Line type="monotone" dataKey="Battery (%)" stroke="#10b981" dot={false} strokeWidth={1.5} />
      </LineChart>
    </ResponsiveContainer>
  )
}
