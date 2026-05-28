import { motion } from 'framer-motion'
import { useCallback, useEffect, useState } from 'react'
import { ChevronLeft, ChevronRight, Filter, ListChecks } from 'lucide-react'
import { getEventsFiltered } from '@/lib/api'
import { useArgus } from '@/hooks/useArgus'
import type { PowerEvent } from '@/types'

const EVENT_BADGE: Record<string, string> = {
  on_battery: 'bg-amber-500/20 text-amber-700 dark:text-amber-300 border border-amber-500/30',
  power_restored: 'bg-emerald-500/20 text-emerald-700 dark:text-emerald-300 border border-emerald-500/30',
  battery_low: 'bg-red-500/20 text-red-700 dark:text-red-300 border border-red-500/30',
  threshold_crossed: 'bg-amber-500/20 text-amber-700 dark:text-amber-300 border border-amber-500/30',
  device_offline: 'bg-red-500/20 text-red-700 dark:text-red-300 border border-red-500/30',
  device_online: 'bg-emerald-500/20 text-emerald-700 dark:text-emerald-300 border border-emerald-500/30',
  shutdown_initiated: 'bg-red-500/20 text-red-700 dark:text-red-300 border border-red-500/30',
}

const EVENT_TYPES = [
  'on_battery',
  'power_restored',
  'battery_low',
  'threshold_crossed',
  'device_offline',
  'device_online',
  'shutdown_initiated',
]

const PAGE_SIZE = 25

export function Events() {
  const { devices } = useArgus()
  const [events, setEvents] = useState<PowerEvent[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [filterDevice, setFilterDevice] = useState('')
  const [filterType, setFilterType] = useState('')

  const fetchEvents = useCallback(async (p: number, devId: string, evType: string) => {
    setLoading(true)
    try {
      const result = await getEventsFiltered(p, PAGE_SIZE, devId || undefined, evType || undefined)
      setEvents(result.items)
      setTotal(result.total)
    } catch {
      setEvents([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchEvents(page, filterDevice, filterType)
  }, [fetchEvents, page, filterDevice, filterType])

  const handleFilterChange = (dev: string, type: string) => {
    setFilterDevice(dev)
    setFilterType(type)
    setPage(1)
  }

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  function renderTable() {
    if (loading) {
      return (
        <div className="p-8 text-center">
          <div className="inline-block w-5 h-5 border-2 border-amber-500 border-t-transparent rounded-full animate-spin" />
        </div>
      )
    }
    if (events.length === 0) {
      return (
        <div className="py-16 text-center text-slate-500">
          <ListChecks size={40} className="mx-auto mb-3 opacity-30" />
          <p>No events found{filterDevice || filterType ? ' for the selected filters' : ''}.</p>
        </div>
      )
    }
    return (
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/60">
              <th className="text-left py-3 px-4 text-slate-500 dark:text-slate-400 font-medium">Time</th>
              <th className="text-left py-3 px-4 text-slate-500 dark:text-slate-400 font-medium">Device</th>
              <th className="text-left py-3 px-4 text-slate-500 dark:text-slate-400 font-medium">Event</th>
              <th className="text-left py-3 px-4 text-slate-500 dark:text-slate-400 font-medium hidden md:table-cell">Details</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800/50">
            {events.map((ev) => (
              <tr key={ev.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/30 transition-colors">
                <td className="py-3 px-4 text-slate-500 dark:text-slate-400 whitespace-nowrap">
                  {new Date(ev.timestamp).toLocaleString()}
                </td>
                <td className="py-3 px-4 text-slate-700 dark:text-slate-300 font-medium">
                  {ev.device_id}
                </td>
                <td className="py-3 px-4">
                  <span className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${EVENT_BADGE[ev.event_type] ?? 'bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-300'}`}>
                    {ev.event_type.replace(/_/g, ' ')}
                  </span>
                </td>
                <td className="py-3 px-4 text-xs text-slate-500 dark:text-slate-500 hidden md:table-cell max-w-xs truncate">
                  {Object.keys(ev.metadata).length > 0
                    ? Object.entries(ev.metadata)
                        .map(([k, v]) => `${k}: ${v}`)
                        .join(', ')
                    : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-6"
    >
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Events</h1>
        <p className="text-slate-500 text-sm mt-0.5">
          Power event history across all devices
        </p>
      </div>

      {/* Filters */}
      <div className="bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800 rounded-xl p-4">
        <div className="flex items-center gap-2 mb-3">
          <Filter size={14} className="text-slate-400" />
          <span className="text-sm font-medium text-slate-700 dark:text-slate-300">Filters</span>
        </div>
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="flex flex-col gap-1">
            <label htmlFor="filter-device" className="text-xs text-slate-500">Device</label>
            <select
              id="filter-device"
              value={filterDevice}
              onChange={(e) => handleFilterChange(e.target.value, filterType)}
              className="bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-1.5 text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-amber-500/50 min-w-[160px]"
            >
              <option value="">All devices</option>
              {devices.map((d) => (
                <option key={d.id} value={d.id}>{d.name || d.id}</option>
              ))}
            </select>
          </div>

          <div className="flex flex-col gap-1">
            <label htmlFor="filter-type" className="text-xs text-slate-500">Event type</label>
            <select
              id="filter-type"
              value={filterType}
              onChange={(e) => handleFilterChange(filterDevice, e.target.value)}
              className="bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-1.5 text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-amber-500/50 min-w-[160px]"
            >
              <option value="">All types</option>
              {EVENT_TYPES.map((t) => (
                <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>
              ))}
            </select>
          </div>

          {(filterDevice || filterType) && (
            <button
              onClick={() => handleFilterChange('', '')}
              className="self-end text-xs text-slate-500 hover:text-slate-300 transition-colors"
            >
              Clear filters
            </button>
          )}
        </div>
      </div>

      {/* Table */}
      <div className="bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800 rounded-2xl overflow-hidden">
        {renderTable()}

        {/* Pagination */}
        {!loading && total > PAGE_SIZE && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-slate-100 dark:border-slate-800">
            <span className="text-xs text-slate-500">
              Showing {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, total)} of {total}
            </span>
            <div className="flex items-center gap-1">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="p-1.5 rounded-md text-slate-500 hover:text-slate-700 hover:bg-slate-200/70 dark:text-slate-400 dark:hover:text-slate-200 dark:hover:bg-slate-700/50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronLeft size={16} />
              </button>
              <span className="text-xs text-slate-500 dark:text-slate-400 px-2">
                {page} / {totalPages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="p-1.5 rounded-md text-slate-500 hover:text-slate-700 hover:bg-slate-200/70 dark:text-slate-400 dark:hover:text-slate-200 dark:hover:bg-slate-700/50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronRight size={16} />
              </button>
            </div>
          </div>
        )}
      </div>
    </motion.div>
  )
}
