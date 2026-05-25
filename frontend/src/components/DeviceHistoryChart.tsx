import { useCallback, useEffect, useState } from 'react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import { getSnapshots } from '@/lib/api'
import type { PowerSnapshot } from '@/types'

interface MetricDef {
  key: keyof PowerSnapshot
  label: string
  color: string
  unit: string
}

const METRICS: MetricDef[] = [
  { key: 'power_watts',    label: 'Power (W)',    color: '#f59e0b', unit: 'W'  },
  { key: 'load_percent',   label: 'Load (%)',     color: '#3b82f6', unit: '%'  },
  { key: 'battery_percent',label: 'Battery (%)',  color: '#10b981', unit: '%'  },
  { key: 'voltage',        label: 'Voltage (V)',  color: '#a78bfa', unit: 'V'  },
  { key: 'runtime_seconds',label: 'Runtime (s)',  color: '#ec4899', unit: 's'  },
]

const PAGE_SIZES = [25, 50, 100, 200]

interface ChartPoint {
  time: string
  [key: string]: string | number | null
}

function formatTime(ts: string): string {
  const d = new Date(ts)
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

interface DeviceHistoryChartProps {
  readonly deviceId: string
}

export function DeviceHistoryChart({ deviceId }: DeviceHistoryChartProps) {
  const [snapshots, setSnapshots] = useState<PowerSnapshot[]>([])
  const [loading, setLoading] = useState(false)
  const [pageSize, setPageSize] = useState(50)
  const [enabledMetrics, setEnabledMetrics] = useState<Set<keyof PowerSnapshot>>(
    new Set<keyof PowerSnapshot>(['power_watts', 'battery_percent', 'load_percent'])
  )

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const page = await getSnapshots(1, pageSize, deviceId)
      setSnapshots([...page.items].reverse())
    } catch {
      setSnapshots([])
    } finally {
      setLoading(false)
    }
  }, [deviceId, pageSize])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const toggleMetric = (key: keyof PowerSnapshot) => {
    setEnabledMetrics((prev) => {
      const next = new Set(prev)
      if (next.has(key)) {
        next.delete(key)
      } else {
        next.add(key)
      }
      return next
    })
  }

  function renderChart() {
    if (loading) {
      return (
        <div className="h-[280px] flex items-center justify-center">
          <div className="w-5 h-5 border-2 border-violet-500 border-t-transparent rounded-full animate-spin" />
        </div>
      )
    }
    if (snapshots.length === 0) {
      return (
        <div className="h-[280px] flex items-center justify-center text-slate-500 text-sm">
          No data available for this device.
        </div>
      )
    }
    return (
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={chartData} margin={{ top: 5, right: 10, left: -10, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis
            dataKey="time"
            tick={{ fill: '#64748b', fontSize: 11 }}
            tickLine={false}
            axisLine={{ stroke: '#1e293b' }}
          />
          <YAxis
            tick={{ fill: '#64748b', fontSize: 11 }}
            tickLine={false}
            axisLine={{ stroke: '#1e293b' }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#0f172a',
              border: '1px solid #1e293b',
              borderRadius: '8px',
              fontSize: '12px',
            }}
            labelStyle={{ color: '#94a3b8' }}
          />
          <Legend
            wrapperStyle={{ fontSize: '12px', paddingTop: '8px' }}
          />
          {METRICS.filter((m) => enabledMetrics.has(m.key)).map((m) => (
            <Line
              key={m.key}
              type="monotone"
              dataKey={m.key}
              name={m.label}
              stroke={m.color}
              dot={false}
              strokeWidth={2}
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    )
  }

  const chartData: ChartPoint[] = snapshots.map((s) => ({
    time: formatTime(s.timestamp),
    power_watts:     s.power_watts,
    load_percent:    s.load_percent,
    battery_percent: s.battery_percent,
    voltage:         s.voltage,
    runtime_seconds: s.runtime_seconds,
  }))

  return (
    <div className="space-y-4">
      {/* Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center gap-3">
        {/* Metric toggles */}
        <div className="flex flex-wrap gap-2">
          {METRICS.map((m) => (
            <button
              key={m.key}
              type="button"
              onClick={() => toggleMetric(m.key)}
              className={`flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full border font-medium transition-all ${
                enabledMetrics.has(m.key)
                  ? 'opacity-100'
                  : 'opacity-40 grayscale'
              }`}
              style={{
                borderColor: m.color + '60',
                backgroundColor: m.color + '20',
                color: m.color,
              }}
            >
              <span
                className="w-2 h-2 rounded-full"
                style={{ backgroundColor: m.color }}
              />
              {m.label}
            </button>
          ))}
        </div>

        {/* Points selector */}
        <div className="flex items-center gap-2 sm:ml-auto">
          <span className="text-xs text-slate-500">Points:</span>
          <select
            value={pageSize}
            onChange={(e) => setPageSize(Number(e.target.value))}
            className="bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-2 py-1 text-xs text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-violet-500/50"
          >
            {PAGE_SIZES.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Chart */}
      {renderChart()}
    </div>
  )
}
