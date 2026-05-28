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
import type { Device, PowerSnapshot } from '@/types'

interface PowerChartProps {
  readonly snapshots: PowerSnapshot[]
  readonly devices?: Device[]
}

// Per-device colour palettes (power, load, battery)
const DEVICE_PALETTE = [
  { power: '#f59e0b', load: '#3b82f6', battery: '#10b981' },
  { power: '#f97316', load: '#6366f1', battery: '#06b6d4' },
  { power: '#ec4899', load: '#a855f7', battery: '#84cc16' },
]

export function PowerChart({ snapshots, devices }: PowerChartProps) {
  const chronological = [...snapshots].reverse()

  if (devices && devices.length > 1) {
    const deviceNames = new Map(devices.map((d) => [d.id, d.name || d.id]))
    const deviceIds = [...new Set(chronological.map((s) => s.device_id))]

    // Merge snapshots into time-keyed data points with per-device metric columns
    const byTime = new Map<string, Record<string, string | number | null>>()
    for (const snap of chronological) {
      const time = new Date(snap.timestamp).toLocaleTimeString()
      if (!byTime.has(time)) byTime.set(time, { time })
      const point = byTime.get(time)!
      const name = deviceNames.get(snap.device_id) ?? snap.device_id
      point[`${name} Power (W)`] = snap.power_watts
      point[`${name} Load (%)`] = snap.load_percent
      point[`${name} Battery (%)`] = snap.battery_percent
    }
    const data = [...byTime.values()]

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
          {deviceIds.map((deviceId, i) => {
            const name = deviceNames.get(deviceId) ?? deviceId
            const colors = DEVICE_PALETTE[i % DEVICE_PALETTE.length]
            return [
              <Line key={`${deviceId}-power`} type="monotone" dataKey={`${name} Power (W)`} stroke={colors.power} dot={false} strokeWidth={1.5} />,
              <Line key={`${deviceId}-load`} type="monotone" dataKey={`${name} Load (%)`} stroke={colors.load} dot={false} strokeWidth={1.5} />,
              <Line key={`${deviceId}-battery`} type="monotone" dataKey={`${name} Battery (%)`} stroke={colors.battery} dot={false} strokeWidth={1.5} />,
            ]
          })}
        </LineChart>
      </ResponsiveContainer>
    )
  }

  // Single device or no device info — original behaviour
  const data = chronological
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
