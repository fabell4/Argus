import { useEffect, useState } from 'react'
import { Download } from 'lucide-react'
import { getEvents } from '@/lib/api'
import type { PowerEvent } from '@/types'

function downloadEventsCSV(events: PowerEvent[], filename = 'argus-events') {
  const headers = ['Time', 'Device', 'Event Type', 'Details']
  const rows = events.map((ev) => [
    new Date(ev.timestamp).toLocaleString(),
    ev.device_id,
    ev.event_type,
    Object.entries(ev.metadata)
      .map(([k, v]) => `${k}: ${v}`)
      .join('; '),
  ])
  const csv = [headers, ...rows]
    .map((r) =>
      r
        .map((cell) =>
          cell.includes(',') || cell.includes('"')
            ? `"${cell.replace(/"/g, '""')}"`
            : cell
        )
        .join(',')
    )
    .join('\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${filename}-${new Date().toISOString().split('T')[0]}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

const EVENT_BADGE: Record<string, string> = {
  on_battery: 'bg-amber-500/20 text-amber-700 dark:text-amber-300 border border-amber-500/30',
  power_restored: 'bg-emerald-500/20 text-emerald-700 dark:text-emerald-300 border border-emerald-500/30',
  battery_low: 'bg-red-500/20 text-red-700 dark:text-red-300 border border-red-500/30',
  threshold_crossed: 'bg-amber-500/20 text-amber-700 dark:text-amber-300 border border-amber-500/30',
  device_offline: 'bg-red-500/20 text-red-700 dark:text-red-300 border border-red-500/30',
  device_online: 'bg-emerald-500/20 text-emerald-700 dark:text-emerald-300 border border-emerald-500/30',
}

interface EventsTableProps {
  readonly title?: string
}

export function EventsTable({ title }: EventsTableProps = {}) {
  const [events, setEvents] = useState<PowerEvent[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getEvents()
      .then((page) => setEvents(page.items))
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  const exportButton = (
    <button
      type="button"
      onClick={() => downloadEventsCSV(events, 'argus-recent-events')}
      disabled={events.length === 0}
      className="flex items-center gap-1.5 text-xs px-2.5 py-1.5 rounded-lg text-amber-600 dark:text-amber-400 bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/20 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
    >
      <Download size={13} />
      Export CSV
    </button>
  )

  if (loading) {
    return (
      <div>
        {title && (
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-200">{title}</h2>
            {exportButton}
          </div>
        )}
        <p className="text-slate-500 text-sm">Loading events…</p>
      </div>
    )
  }

  if (events.length === 0) {
    return (
      <div>
        {title && (
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-200">{title}</h2>
            {exportButton}
          </div>
        )}
        <p className="text-slate-500 text-sm">No events recorded yet.</p>
      </div>
    )
  }

  return (
    <div>
      {title ? (
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-200">{title}</h2>
          {exportButton}
        </div>
      ) : (
        <div className="flex justify-end mb-2">{exportButton}</div>
      )}
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-200 dark:border-slate-800">
            <th className="text-left py-2 px-3 text-slate-500 dark:text-slate-400 font-medium">Time</th>
            <th className="text-left py-2 px-3 text-slate-500 dark:text-slate-400 font-medium">Device</th>
            <th className="text-left py-2 px-3 text-slate-500 dark:text-slate-400 font-medium">Event</th>
          </tr>
        </thead>
        <tbody>
          {events.map((ev) => (
            <tr key={ev.id} className="border-b border-slate-200 dark:border-slate-800/50 hover:bg-slate-50 dark:hover:bg-slate-800/30 transition-colors">
              <td className="py-2 px-3 text-slate-500 dark:text-slate-400">{new Date(ev.timestamp).toLocaleString()}</td>
              <td className="py-2 px-3 text-slate-700 dark:text-slate-300">{ev.device_id}</td>
              <td className="py-2 px-3">
                <span className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${EVENT_BADGE[ev.event_type] ?? 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300'}`}>
                  {ev.event_type}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
    </div>
  )
}
