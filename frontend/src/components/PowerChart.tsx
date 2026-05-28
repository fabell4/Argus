import { useState } from 'react'
import type { ReactNode } from 'react'
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

type ChartDataPoint = Record<string, string | number | null>

// ---------------------------------------------------------------------------
// Shared chart constants
// ---------------------------------------------------------------------------

const GRID_STROKE = '#1e293b'
const TICK_STYLE = { fontSize: 11, fill: '#94a3b8' }
const TOOLTIP_CONTENT_STYLE = {
  background: '#0f172a',
  border: '1px solid #1e293b',
  borderRadius: '8px',
}
const TOOLTIP_LABEL_STYLE = { color: '#94a3b8' }
const LEGEND_STYLE = { fontSize: '12px', color: '#94a3b8' }

// Wraps the shared Recharts boilerplate so it isn't duplicated across branches.
function SharedLineChart({
  data,
  children,
}: {
  readonly data: ChartDataPoint[]
  readonly children: ReactNode
}) {
  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke={GRID_STROKE} />
        <XAxis dataKey="time" tick={TICK_STYLE} />
        <YAxis tick={TICK_STYLE} />
        <Tooltip contentStyle={TOOLTIP_CONTENT_STYLE} labelStyle={TOOLTIP_LABEL_STYLE} />
        <Legend wrapperStyle={LEGEND_STYLE} />
        {children}
      </LineChart>
    </ResponsiveContainer>
  )
}

export function PowerChart({ snapshots, devices }: PowerChartProps) {
  const [metric, setMetric] = useState<MetricKey>('power')
  const chronological = [...snapshots].reverse()

  if (devices && devices.length > 1) {
    const deviceNames = new Map(devices.map((d) => [d.id, d.name || d.id]))
    const deviceIds = [...new Set(chronological.map((s) => s.device_id))]
    const { suffix } = METRIC_OPTIONS.find((m) => m.key === metric)!
    const field = METRIC_FIELD[metric]

    // Merge snapshots into time-keyed data points — one column per device
    const byTime = new Map<string, ChartDataPoint>()
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
          <SharedLineChart data={data}>
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
          </SharedLineChart>
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
    <SharedLineChart data={data}>
      <Line type="monotone" dataKey="Power (W)" stroke="#f59e0b" dot={false} strokeWidth={1.5} />
      <Line type="monotone" dataKey="Load (%)" stroke="#3b82f6" dot={false} strokeWidth={1.5} />
      <Line type="monotone" dataKey="Battery (%)" stroke="#10b981" dot={false} strokeWidth={1.5} />
    </SharedLineChart>
  )
}
