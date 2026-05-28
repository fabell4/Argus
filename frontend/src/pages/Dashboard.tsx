import { motion } from 'framer-motion'
import { useEffect, useMemo, useState } from 'react'
import { RefreshCw, AlertCircle, Clock, ExternalLink } from 'lucide-react'
import { PowerChart } from '@/components/PowerChart'
import { PowerGauge } from '@/components/PowerGauge'
import { EventsTable } from '@/components/EventsTable'
import { useArgus } from '@/hooks/useArgus'
import type { PowerSnapshot } from '@/types'

// ─── countdown timer ─────────────────────────────────────────────────────────

function useCountdown(nextPollAt: string | null | undefined): string {
  const [remaining, setRemaining] = useState<string>('')

  useEffect(() => {
    if (!nextPollAt) {
      setRemaining('')
      return
    }
    const update = () => {
      const diff = Math.max(0, Math.round((new Date(nextPollAt).getTime() - Date.now()) / 1000))
      if (diff <= 0) {
        setRemaining('now')
        return
      }
      const m = Math.floor(diff / 60)
      const s = diff % 60
      setRemaining(m > 0 ? `${m}m ${s}s` : `${s}s`)
    }
    update()
    const id = setInterval(update, 1000)
    return () => clearInterval(id)
  }, [nextPollAt])

  return remaining
}

// ─── version check ────────────────────────────────────────────────────────────

interface GithubRelease { tag_name: string; html_url: string }

function useVersionCheck(currentVersion: string | undefined, githubRepo: string | undefined) {
  const [latest, setLatest] = useState<GithubRelease | null>(null)

  useEffect(() => {
    if (!currentVersion || !githubRepo) return
    const url = `https://api.github.com/repos/${githubRepo}/releases/latest`
    fetch(url, { headers: { Accept: 'application/vnd.github+json' } })
      .then((r) => (r.ok ? r.json() : null))
      .then((data: GithubRelease | null) => {
        if (data?.tag_name && data.tag_name !== currentVersion && data.tag_name !== `v${currentVersion}`) {
          setLatest(data)
        }
      })
      .catch(() => undefined)
  }, [currentVersion, githubRepo])

  return latest
}

// ─── dashboard ────────────────────────────────────────────────────────────────

export function Dashboard() {
  const { snapshots, latest, health, isPolling, error, runPoll, devices } = useArgus()

  const countdown = useCountdown(health?.next_poll_at)
  const latestRelease = useVersionCheck(health?.version, health?.github_repo)

  // Derive the latest snapshot per device from the shared snapshots pool (newest-first)
  const latestByDevice = useMemo(() => {
    const map = new Map<string, PowerSnapshot>()
    for (const snap of snapshots) {
      if (!map.has(snap.device_id)) map.set(snap.device_id, snap)
    }
    return map
  }, [snapshots])

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-6"
    >
      {/* Update banner */}
      {latestRelease && (
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center justify-between gap-3 px-4 py-3 rounded-xl bg-violet-500/10 border border-violet-500/30 text-sm"
        >
          <span className="text-violet-300">
            Update available: <span className="font-semibold">{latestRelease.tag_name}</span>
          </span>
          <a
            href={latestRelease.html_url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 text-violet-400 hover:text-violet-300 transition-colors font-medium"
          >
            View release <ExternalLink size={12} />
          </a>
        </motion.div>
      )}

      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Dashboard</h1>
          <p className="text-slate-500 text-sm mt-0.5">
            {health?.status === 'ok' ? 'Scheduler running' : 'Connecting to Argus…'}
            {health?.version && (
              <span className="ml-2 text-slate-600 dark:text-slate-500">v{health.version}</span>
            )}
          </p>
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          {health && (
            <span className={`text-xs px-2 py-1 rounded-full font-medium ${
              health.status === 'ok'
                ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                : 'bg-red-500/20 text-red-300 border border-red-500/30'
            }`}>
              {health.status}
            </span>
          )}
          {countdown && !isPolling && (
            <span className="flex items-center gap-1 text-xs text-slate-500">
              <Clock size={12} />
              Next poll in {countdown}
            </span>
          )}
          <button
            onClick={runPoll}
            disabled={isPolling}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              isPolling
                ? 'bg-slate-200 dark:bg-slate-800 text-slate-500 cursor-not-allowed'
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

      {devices.length > 0 ? (
        <div className="space-y-5">
          {devices.map((device) => {
            const snap = latestByDevice.get(device.id) ?? null
            return (
              <div key={device.id}>
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400 mb-2">
                  {device.name || device.id}
                </p>
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                  <PowerGauge label="Power" value={snap?.power_watts ?? null} unit="W" metric="power" />
                  <PowerGauge label="Load" value={snap?.load_percent ?? null} unit="%" metric="load" />
                  <PowerGauge label="Battery" value={snap?.battery_percent ?? null} unit="%" metric="battery" />
                  <PowerGauge label="Temperature" value={snap?.temperature_c ?? null} unit="°C" metric="temperature" />
                </div>
              </div>
            )
          })}
        </div>
      ) : (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <PowerGauge label="Power" value={latest?.power_watts ?? null} unit="W" metric="power" />
          <PowerGauge label="Load" value={latest?.load_percent ?? null} unit="%" metric="load" />
          <PowerGauge label="Battery" value={latest?.battery_percent ?? null} unit="%" metric="battery" />
          <PowerGauge label="Temperature" value={latest?.temperature_c ?? null} unit="°C" metric="temperature" />
        </div>
      )}

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800 rounded-2xl p-4 md:p-6"
      >
        <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-200 mb-4">Power History</h2>
        <PowerChart snapshots={snapshots} devices={devices} />
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800 rounded-2xl p-4 md:p-6"
      >
        <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-200 mb-4">Recent Events</h2>
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
