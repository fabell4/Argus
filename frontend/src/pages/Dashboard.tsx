import { motion } from 'framer-motion'
import { RefreshCw, AlertCircle } from 'lucide-react'
import { PowerChart } from '@/components/PowerChart'
import { PowerGauge } from '@/components/PowerGauge'
import { EventsTable } from '@/components/EventsTable'
import { useArgus } from '@/hooks/useArgus'

export function Dashboard() {
  const { snapshots, latest, health, isPolling, error, runPoll } = useArgus()

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-6"
    >
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Dashboard</h1>
          <p className="text-slate-400 text-sm mt-0.5">
            {health?.status === 'ok' ? 'Scheduler running' : 'Connecting to Argus…'}
          </p>
        </div>
        <div className="flex items-center gap-3">
          {health && (
            <span className={`text-xs px-2 py-1 rounded-full font-medium ${
              health.status === 'ok'
                ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                : 'bg-red-500/20 text-red-300 border border-red-500/30'
            }`}>
              {health.status}
            </span>
          )}
          <button
            onClick={runPoll}
            disabled={isPolling}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              isPolling
                ? 'bg-slate-800 text-slate-500 cursor-not-allowed'
                : 'bg-violet-600 hover:bg-violet-500 text-white shadow-lg shadow-violet-500/20'
            }`}
          >
            <RefreshCw size={14} className={isPolling ? 'animate-spin' : ''} />
            {isPolling ? 'Polling…' : 'Poll Now'}
          </button>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-2 px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
          <AlertCircle size={16} className="shrink-0" />
          {error}
        </div>
      )}

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <PowerGauge label="Power" value={latest?.power_watts ?? null} unit="W" metric="power" />
        <PowerGauge label="Load" value={latest?.load_percent ?? null} unit="%" metric="load" />
        <PowerGauge label="Battery" value={latest?.battery_percent ?? null} unit="%" metric="battery" />
        <PowerGauge label="Temperature" value={latest?.temperature_c ?? null} unit="°C" metric="temperature" />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="bg-slate-900/40 border border-slate-800 rounded-2xl p-4 md:p-6"
      >
        <h2 className="text-lg font-semibold text-slate-200 mb-4">Power History</h2>
        <PowerChart snapshots={snapshots} />
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="bg-slate-900/40 border border-slate-800 rounded-2xl p-4 md:p-6"
      >
        <h2 className="text-lg font-semibold text-slate-200 mb-4">Recent Events</h2>
        <EventsTable />
      </motion.div>

      {health && (health.last_poll_at || health.next_poll_at) && (
        <div className="flex items-center gap-6 text-xs text-slate-500 pb-2">
          {health.last_poll_at && (
            <span>Last poll: {new Date(health.last_poll_at).toLocaleString()}</span>
          )}
          {health.next_poll_at && (
            <span>Next poll: {new Date(health.next_poll_at).toLocaleString()}</span>
          )}
        </div>
      )}
    </motion.div>
  )
}
