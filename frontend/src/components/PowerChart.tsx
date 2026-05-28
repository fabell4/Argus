import { useState } from 'react'
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

type MetricKey = 'power' | 'load' | 'battery'

const METRIC_OPTIONS: { key: MetricKey; label: string; suffix: string }[] = [
  { key: 'power',   label: 'Power',   suffix: 'Power (W)' },
  { key: 'load',    label: 'Load',    suffix: 'Load (%)' },
  { key: 'battery', label: 'Battery', suffix: 'Battery (%)' },
]

const METRIC_FIELD: Record<MetricKey, keyof PowerSnapshot> = {
  power:   'power_watts',
  load:    'load_percent',
  battery: 'battery_percent',
}

// 8-colour palette — enough for most real-world deployments
const DEVICE_COLORS = [
  '#f59e0b', '#3b82f6', '#10b981', '#f97316',
  '#6366f1', '#06b6d4', '#ec4899', '#84cc16',
]

export function PowerChart({ snapshots, devices }: PowerChartProps) {
  const [metric, setMetric] = useState<MetricKey>('power')
  const chronological = [...snapshots].reverse()

  if (devices && devices.length > 1) {
    const deviceNames = new Map(devices.map((d) => [d.id, d.name || d.id]))
    const deviceIds = [...new Set(chronological.map((s) => s.device_id))]
    const { suffix } = METRIC_OPTIONS.find((m) => m.key === metric)!
    const field = METRIC_FIELD[metric]

    // Merge snapshots into time-keyed data points — one column per device
    const byTime = new Map<string, Record<string, string | number | null>>()
    for (const snap of chronological) {
      const time = new Date(snap.timestamp).toLocaleTimeString()
      if (!byTime.has(time)) byTime.set(time, { time })
      const point = byTime.get(time)!
      const name = deviceNames.get(snap.device_id) ?? snap.device_id
      point[`${name} ${suffix}`] = snap[field]
    }
    const data = [...byTime.values()]

    return (
      <div>
        {/* Metric selector */}
        <div className="flex gap-1 mb-4">
          {METRIC_OPTIONS.map((m) => (
            <button
              key={m.key}
              type="button"
              onClick={() => setMetric(m.key)}
              className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${
                metric === m.key
                  ? 'bg-violet-600 text-white'
                  : 'bg-slate-100 dark:bg-slate-800 text-slate-500 hover:text-slate-300'
              }`}
            >
              {m.label}
            </button>
          ))}
        </div>

        {data.length === 0 ? (
          <p className="text-slate-500 text-sm py-8 text-center">No snapshot data yet.</p>
        ) : (
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
                return (
                  <Line
                    key={deviceId}
                    type="monotone"
                    dataKey={`${name} ${suffix}`}
                    stroke={DEVICE_COLORS[i % DEVICE_COLORS.length]}
                    dot={false}
                    strokeWidth={1.5}
                  />
                )
              })}
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    )
  }

  // Single device or no device info — original behaviour
  const data = chronological.map((s) => ({
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
