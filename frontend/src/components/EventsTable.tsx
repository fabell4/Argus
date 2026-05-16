import { useEffect, useState } from 'react'
import { getEvents } from '@/lib/api'
import type { PowerEvent } from '@/types'

const EVENT_BADGE: Record<string, string> = {
  on_battery: 'badge-warn',
  power_restored: 'badge-ok',
  battery_low: 'badge-danger',
  threshold_crossed: 'badge-warn',
  device_offline: 'badge-danger',
  device_online: 'badge-ok',
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

  if (loading) return <p className="muted">Loading events…</p>
  if (events.length === 0) return <p className="muted">No events recorded yet.</p>

  return (
    <div className="table-wrapper">
      <table className="data-table">
        <thead>
          <tr>
            <th>Time</th>
            <th>Device</th>
            <th>Event</th>
          </tr>
        </thead>
        <tbody>
          {events.map((ev) => (
            <tr key={ev.id}>
              <td>{new Date(ev.timestamp).toLocaleString()}</td>
              <td>{ev.device_id}</td>
              <td>
                <span className={`badge ${EVENT_BADGE[ev.event_type] ?? 'badge-default'}`}>
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
