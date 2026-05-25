import { motion } from 'framer-motion'
import { useEffect, useState } from 'react'
import { Wifi, WifiOff, Battery, Zap, Clock, Server, BarChart2 } from 'lucide-react'
import { useArgus } from '@/hooks/useArgus'
import { getLatestSnapshot } from '@/lib/api'
import { DeviceHistoryChart } from '@/components/DeviceHistoryChart'
import type { Device, PowerSnapshot } from '@/types'

const DEVICE_TYPE_LABEL: Record<string, string> = {
  ups: 'UPS',
  pdu: 'PDU',
  sensor: 'Sensor',
}

const POLLER_BADGE: Record<string, string> = {
  nut: 'bg-violet-500/20 text-violet-300 border border-violet-500/30',
  snmp: 'bg-blue-500/20 text-blue-300 border border-blue-500/30',
}

function getStatusFromSnapshot(snap: PowerSnapshot | null, lastSeen: string | null): 'online' | 'on_battery' | 'offline' {
  if (!snap && !lastSeen) return 'offline'
  if (snap?.ups_status) {
    const s = snap.ups_status.toLowerCase()
    if (s.includes('ob') || s.includes('on battery')) return 'on_battery'
  }
  return snap ? 'online' : 'offline'
}

const STATUS_CONFIG = {
  online: {
    label: 'Online',
    dot: 'bg-emerald-400',
    badge: 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30',
    icon: Wifi,
  },
  on_battery: {
    label: 'On Battery',
    dot: 'bg-amber-400',
    badge: 'bg-amber-500/20 text-amber-300 border border-amber-500/30',
    icon: Battery,
  },
  offline: {
    label: 'Offline',
    dot: 'bg-red-400',
    badge: 'bg-red-500/20 text-red-300 border border-red-500/30',
    icon: WifiOff,
  },
}

function MetricPill({ label, value, unit }: Readonly<{ label: string; value: number | null | undefined; unit: string }>) {
  return (
    <div className="flex flex-col items-center px-3 py-2 rounded-lg bg-slate-800/60 dark:bg-slate-800/60 border border-slate-700/50">
      <span className="text-xs text-slate-400 mb-0.5">{label}</span>
      <span className="text-sm font-semibold text-slate-200 dark:text-slate-200">
        {value == null ? '—' : `${value.toFixed(1)}${unit}`}
      </span>
    </div>
  )
}

function DeviceCard({ device }: Readonly<{ device: Device }>) {
  const [snap, setSnap] = useState<PowerSnapshot | null>(null)
  const [showChart, setShowChart] = useState(false)

  useEffect(() => {
    getLatestSnapshot(device.id)
      .then((s) => setSnap(s))
      .catch(() => setSnap(null))
  }, [device.id])

  const status = getStatusFromSnapshot(snap, device.last_seen ?? null)
  const cfg = STATUS_CONFIG[status]
  const StatusIcon = cfg.icon

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 space-y-4"
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-slate-100 dark:bg-slate-800">
            <Server size={18} className="text-slate-500 dark:text-slate-400" />
          </div>
          <div>
            <h3 className="font-semibold text-slate-900 dark:text-slate-100 text-sm leading-tight">
              {device.name || device.id}
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-500 mt-0.5">
              {device.host}:{device.port}
            </p>
          </div>
        </div>
        <span className={`inline-flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full font-medium ${cfg.badge}`}>
          <span className={`w-1.5 h-1.5 rounded-full ${cfg.dot}`} />
          {cfg.label}
        </span>
      </div>

      {/* Type / poller badges */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-xs px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-700">
          {DEVICE_TYPE_LABEL[device.type] ?? device.type}
        </span>
        <span className={`text-xs px-2 py-0.5 rounded border font-medium ${POLLER_BADGE[device.poller] ?? 'bg-slate-700 text-slate-300 border-slate-600'}`}>
          {device.poller.toUpperCase()}
        </span>
        {!device.enabled && (
          <span className="text-xs px-2 py-0.5 rounded bg-slate-200 dark:bg-slate-800 text-slate-500 border border-slate-300 dark:border-slate-700">
            Disabled
          </span>
        )}
      </div>

      {/* Live metrics */}
      {snap && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          <MetricPill label="Power" value={snap.power_watts} unit="W" />
          <MetricPill label="Load" value={snap.load_percent} unit="%" />
          <MetricPill label="Battery" value={snap.battery_percent} unit="%" />
          <MetricPill label="Temp" value={snap.temperature_c} unit="°C" />
        </div>
      )}

      {/* Metadata */}
      {(device.model || device.manufacturer) && (
        <div className="text-xs text-slate-500 space-y-0.5">
          {device.manufacturer && <p>Mfr: {device.manufacturer}</p>}
          {device.model && <p>Model: {device.model}</p>}
          {device.firmware && <p>FW: {device.firmware}</p>}
        </div>
      )}

      {/* Last seen */}
      {device.last_seen && (
        <div className="flex items-center gap-1.5 text-xs text-slate-500">
          <Clock size={11} />
          Last seen: {new Date(device.last_seen).toLocaleString()}
        </div>
      )}

      {/* UPS status raw */}
      {snap?.ups_status && (
        <div className="flex items-center gap-1.5 text-xs text-slate-500">
          <StatusIcon size={11} />
          UPS status: <span className="font-mono">{snap.ups_status}</span>
        </div>
      )}

      {/* History chart toggle */}
      <button
        type="button"
        onClick={() => setShowChart((v) => !v)}
        className="flex items-center gap-1.5 text-xs text-violet-400 hover:text-violet-300 transition-colors"
      >
        <BarChart2 size={13} />
        {showChart ? 'Hide history' : 'Show history'}
      </button>

      {showChart && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          exit={{ opacity: 0, height: 0 }}
          className="pt-2 border-t border-slate-200 dark:border-slate-700"
        >
          <DeviceHistoryChart deviceId={device.id} />
        </motion.div>
      )}
    </motion.div>
  )
}

export function Devices() {
  const { devices, loading } = useArgus()

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-6"
    >
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Devices</h1>
          <p className="text-slate-500 text-sm mt-0.5">
            {devices.length} device{devices.length === 1 ? '' : 's'} registered
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Zap size={16} className="text-violet-400" />
          <span className="text-xs text-slate-500">Live metrics from latest poll</span>
        </div>
      </div>

      {loading && (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {[1, 2].map((i) => (
            <div key={i} className="bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 h-48 animate-pulse" />
          ))}
        </div>
      )}

      {!loading && devices.length === 0 && (
        <div className="text-center py-16 text-slate-500">
          <Server size={40} className="mx-auto mb-3 opacity-30" />
          <p className="font-medium">No devices registered</p>
          <p className="text-sm mt-1">Add devices via the API or configuration file.</p>
        </div>
      )}

      {!loading && devices.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {devices.map((device) => (
            <DeviceCard key={device.id} device={device} />
          ))}
        </div>
      )}
    </motion.div>
  )
}
