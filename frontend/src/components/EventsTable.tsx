import { useEffect, useState } from 'react'
import { getEvents } from '@/lib/api'
import type { PowerEvent } from '@/types'

const EVENT_BADGE: Record<string, string> = {
  on_battery: 'bg-amber-500/20 text-amber-300 border border-amber-500/30',
  power_restored: 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30',
  battery_low: 'bg-red-500/20 text-red-300 border border-red-500/30',
  threshold_crossed: 'bg-amber-500/20 text-amber-300 border border-amber-500/30',
  device_offline: 'bg-red-500/20 text-red-300 border border-red-500/30',
  device_online: 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30',
}

export function EventsTable() {
  const [events, setEvents] = useState<PowerEvent[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getEvents()
      .then((page) => setEvents(page.items))
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <p className="text-slate-500 text-sm">Loading events…</p>
  if (events.length === 0) return <p className="text-slate-500 text-sm">No events recorded yet.</p>

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-800">
            <th className="text-left py-2 px-3 text-slate-400 font-medium">Time</th>
            <th className="text-left py-2 px-3 text-slate-400 font-medium">Device</th>
            <th className="text-left py-2 px-3 text-slate-400 font-medium">Event</th>
          </tr>
        </thead>
        <tbody>
          {events.map((ev) => (
            <tr key={ev.id} className="border-b border-slate-800/50 hover:bg-slate-800/30 transition-colors">
              <td className="py-2 px-3 text-slate-400">{new Date(ev.timestamp).toLocaleString()}</td>
              <td className="py-2 px-3 text-slate-300">{ev.device_id}</td>
              <td className="py-2 px-3">
                <span className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${EVENT_BADGE[ev.event_type] ?? 'bg-slate-700 text-slate-300'}`}>
                  {ev.event_type}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
