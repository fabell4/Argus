import { Battery, Thermometer, Zap, Activity } from 'lucide-react'

interface PowerGaugeProps {
  label: string
  value: number | null
  unit: string
  metric: 'power' | 'battery' | 'load' | 'temperature'
}

const ICONS = {
  power: Zap,
  battery: Battery,
  load: Activity,
  temperature: Thermometer,
} as const

const COLORS = {
  power: '#f59e0b',
  battery: '#10b981',
  load: '#3b82f6',
  temperature: '#ef4444',
} as const

export function PowerGauge({ label, value, unit, metric }: PowerGaugeProps) {
  const Icon = ICONS[metric]
  const color = COLORS[metric]

  return (
    <div className="gauge-card" style={{ borderTopColor: color }}>
      <div className="gauge-header">
        <Icon size={16} style={{ color }} />
        <span className="gauge-label">{label}</span>
      </div>
      <div className="gauge-value">
        {value !== null ? (
          <>
            <span className="gauge-number">{value.toFixed(1)}</span>
            <span className="gauge-unit">{unit}</span>
          </>
        ) : (
          <span className="gauge-na">—</span>
        )}
      </div>
    </div>
  )
}
