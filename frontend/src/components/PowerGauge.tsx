import { Battery, Thermometer, Zap, Activity } from 'lucide-react'

interface PowerGaugeProps {
  readonly label: string
  readonly value: number | null
  readonly unit: string
  readonly metric: 'power' | 'battery' | 'load' | 'temperature'
}

const ICONS = {
  power: Zap,
  battery: Battery,
  load: Activity,
  temperature: Thermometer,
} as const

const BORDER_COLORS = {
  power: 'border-t-amber-500',
  battery: 'border-t-emerald-500',
  load: 'border-t-blue-500',
  temperature: 'border-t-red-500',
} as const

const ICON_COLORS = {
  power: 'text-amber-400',
  battery: 'text-emerald-400',
  load: 'text-blue-400',
  temperature: 'text-red-400',
} as const

export function PowerGauge({ label, value, unit, metric }: PowerGaugeProps) {
  const Icon = ICONS[metric]

  return (
    <div className={`bg-slate-900/40 rounded-2xl p-4 border border-slate-800 border-t-2 ${BORDER_COLORS[metric]}`}>
      <div className="flex items-center gap-2 mb-3">
        <Icon size={16} className={ICON_COLORS[metric]} />
        <span className="text-sm text-slate-400">{label}</span>
      </div>
      <div className="text-2xl font-semibold text-slate-100">
        {value === null ? (
          <span className="text-slate-600">—</span>
        ) : (
          <>
            <span>{value.toFixed(1)}</span>
            <span className="text-base text-slate-400 ml-1">{unit}</span>
          </>
        )}
      </div>
    </div>
  )
}
