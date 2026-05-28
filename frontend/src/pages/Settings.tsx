import { motion } from 'framer-motion'
import { useEffect, useState } from 'react'
import { Clock, Database, KeyRound, PauseCircle, ScanLine, Server, SlidersHorizontal } from 'lucide-react'
import { useArgus } from '@/hooks/useArgus'
import type { RuntimeConfig } from '@/types'

// ---------------------------------------------------------------------------
// Toggle switch
// ---------------------------------------------------------------------------
function Toggle({
  checked,
  onChange,
}: Readonly<{
  checked: boolean
  onChange: (value: boolean) => void
}>) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className={`relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-cyan-500/50 ${
        checked ? 'bg-cyan-500' : 'bg-slate-300 dark:bg-slate-700'
      }`}
    >
      <span
        className={`inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform ${
          checked ? 'translate-x-6' : 'translate-x-1'
        }`}
      />
    </button>
  )
}

// ---------------------------------------------------------------------------
// Exporter definitions
// ---------------------------------------------------------------------------
const EXPORTERS = [
  { key: 'sqlite',     label: 'SQLite',      desc: 'Persist snapshots in a local SQLite database' },
  { key: 'prometheus', label: 'Prometheus',  desc: 'Expose metrics at /metrics for Prometheus scraping' },
  { key: 'influxdb',   label: 'InfluxDB',    desc: 'Write time-series data to an InfluxDB v2 instance' },
  { key: 'loki',       label: 'Loki',        desc: 'Ship structured logs to a Grafana Loki endpoint' },
  { key: 'csv',        label: 'CSV',         desc: 'Append snapshots to a local CSV file' },
  { key: 'energy',     label: 'Energy',      desc: 'Accumulate energy usage and estimated cost' },
] as const

export function Settings() {
  const { config, updateConfig, refresh } = useArgus()
  const [form, setForm] = useState<RuntimeConfig | null>(null)
  const [saved, setSaved] = useState(false)
  const [apiKey, setApiKey] = useState(() => localStorage.getItem('argus_api_key') ?? '')
  const [apiKeySaved, setApiKeySaved] = useState(false)

  useEffect(() => {
    if (config) setForm(config)
  }, [config])

  const handleSave = async () => {
    if (!form) return
    await updateConfig(form)
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  const handleSaveApiKey = () => {
    localStorage.setItem('argus_api_key', apiKey)
    setApiKeySaved(true)
    setTimeout(() => setApiKeySaved(false), 2000)
    refresh()
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-6"
    >
      <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Settings</h1>

      <div className="bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800 rounded-2xl p-4 md:p-6 space-y-4">
        <div className="flex items-center gap-2">
          <KeyRound className="w-4 h-4 text-amber-400" />
          <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-200">API Access</h2>
        </div>
        <p className="text-xs text-slate-500">
          Enter your Argus API key to authenticate requests. The key is stored only in your
          browser's local storage.
        </p>
        <label className="flex flex-col gap-1.5">
          <span className="text-sm text-slate-600 dark:text-slate-400">API Key</span>
          <input
            type="password"
            value={apiKey}
            placeholder="Paste your API key here"
            onChange={(e) => setApiKey(e.target.value)}
            className="bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-1.5 text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-amber-500/50"
          />
        </label>
        <button
          onClick={handleSaveApiKey}
          className="px-4 py-1.5 bg-amber-500 hover:bg-amber-400 text-slate-950 rounded-lg text-sm font-medium transition-colors"
        >
          {apiKeySaved ? 'Saved!' : 'Save API Key'}
        </button>
      </div>

      {form ? (
        <>
      {/* Scheduler */}
      <div className="bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800 rounded-2xl p-4 md:p-6 space-y-5">
        <div className="flex items-center gap-2">
          <Clock className="w-4 h-4 text-cyan-400" />
          <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-200">Scheduler</h2>
        </div>

        <div className="flex flex-col gap-1.5">
          <label htmlFor="poll-interval" className="text-sm text-slate-600 dark:text-slate-400">Poll interval (minutes)</label>
          <input
            id="poll-interval"
            type="number"
            min={1}
            max={10080}
            value={form.poll_interval_minutes}
            onChange={(e) => setForm({ ...form, poll_interval_minutes: Number(e.target.value) })}
            className="w-32 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-1.5 text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-cyan-500/50"
          />
          <span className="text-xs text-slate-500">Minimum 1 minute.</span>
        </div>

        <div className="space-y-3">
          {([
            { key: 'scheduler_paused',  icon: PauseCircle, label: 'Pause scheduler', desc: 'Stop all scheduled polling jobs without restarting the service' },
            { key: 'scanning_disabled', icon: ScanLine,    label: 'Disable scanning', desc: 'Skip device discovery and data collection on each poll cycle' },
          ] as const).map(({ key, icon: Icon, label, desc }) => (
            <div key={key} className="flex items-center justify-between gap-4 bg-slate-100 dark:bg-slate-800/50 rounded-xl px-4 py-3 border border-slate-200 dark:border-slate-700/50">
              <div className="flex items-start gap-3 min-w-0">
                <Icon className="w-4 h-4 text-slate-400 mt-0.5 shrink-0" />
                <div className="min-w-0">
                  <p className="text-sm font-medium text-slate-800 dark:text-slate-200">{label}</p>
                  <p className="text-xs text-slate-500 mt-0.5">{desc}</p>
                </div>
              </div>
              <Toggle
                checked={form[key]}
                onChange={(v) => setForm({ ...form, [key]: v })}
              />
            </div>
          ))}
        </div>
      </div>

      {/* Exporters */}
      <div className="bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800 rounded-2xl p-4 md:p-6 space-y-4">
        <div className="flex items-center gap-2">
          <Database className="w-4 h-4 text-blue-400" />
          <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-200">Exporters</h2>
        </div>

        <div className="space-y-3">
          {EXPORTERS.map(({ key, label, desc }) => (
            <div key={key} className="flex items-center justify-between gap-4 bg-slate-100 dark:bg-slate-800/50 rounded-xl px-4 py-3 border border-slate-200 dark:border-slate-700/50">
              <div className="min-w-0">
                <p className="text-sm font-medium text-slate-800 dark:text-slate-200">{label}</p>
                <p className="text-xs text-slate-500 mt-0.5">{desc}</p>
              </div>
              <Toggle
                checked={form.enabled_exporters.includes(key)}
                onChange={(enabled) => {
                  const updated = enabled
                    ? [...form.enabled_exporters, key]
                    : form.enabled_exporters.filter((ex) => ex !== key)
                  setForm({ ...form, enabled_exporters: updated })
                }}
              />
            </div>
          ))}
        </div>
      </div>

      <div className="bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800 rounded-2xl p-4 md:p-6 space-y-4">
        <div className="flex items-center gap-2">
          <Server className="w-4 h-4 text-teal-400" />
          <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-200">NUT Connection</h2>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <label className="flex flex-col gap-1.5">
            <span className="text-sm text-slate-600 dark:text-slate-400">Host</span>
            <input
              type="text"
              value={form.nut_host}
              onChange={(e) => setForm({ ...form, nut_host: e.target.value })}
              className="bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-1.5 text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-cyan-500/50"
            />
          </label>

          <label className="flex flex-col gap-1.5">
            <span className="text-sm text-slate-600 dark:text-slate-400">Port</span>
            <input
              type="number"
              min={1}
              max={65535}
              value={form.nut_port}
              onChange={(e) => setForm({ ...form, nut_port: Number(e.target.value) })}
              className="w-32 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-1.5 text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-cyan-500/50"
            />
          </label>

          <label className="flex flex-col gap-1.5">
            <span className="text-sm text-slate-600 dark:text-slate-400">Username</span>
            <input
              type="text"
              value={form.nut_username}
              onChange={(e) => setForm({ ...form, nut_username: e.target.value })}
              className="bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-1.5 text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-cyan-500/50"
            />
          </label>

          <label className="flex flex-col gap-1.5">
            <span className="text-sm text-slate-600 dark:text-slate-400">Password</span>
            <input
              type="password"
              value={form.nut_password}
              placeholder="Leave blank to keep existing"
              onChange={(e) => setForm({ ...form, nut_password: e.target.value })}
              className="bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-1.5 text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-cyan-500/50"
            />
          </label>

          <label className="flex flex-col gap-1.5">
            <span className="text-sm text-slate-600 dark:text-slate-400">UPS Name(s)</span>
            <input
              type="text"
              value={form.nut_ups_name}
              placeholder="ups1,ups2"
              onChange={(e) => setForm({ ...form, nut_ups_name: e.target.value })}
              className="bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-1.5 text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-cyan-500/50"
            />
            <span className="text-xs text-slate-500">Used when auto-discover is off. Enter a single UPS name or a comma-separated list such as ups1,ups2.</span>
          </label>
        </div>

        <label className="flex items-center gap-2.5 cursor-pointer">
          <input
            type="checkbox"
            checked={form.nut_auto_discover}
            onChange={(e) => setForm({ ...form, nut_auto_discover: e.target.checked })}
            className="w-4 h-4 rounded border-slate-300 dark:border-slate-600 dark:bg-slate-800 accent-cyan-500"
          />
          <span className="text-sm text-slate-700 dark:text-slate-300">Auto-discover UPS devices</span>
        </label>
      </div>

      <div className="bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800 rounded-2xl p-4 md:p-6 space-y-4">
        <div className="flex items-center gap-2">
          <SlidersHorizontal className="w-4 h-4 text-amber-400" />
          <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-200">Event Thresholds</h2>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <label className="flex flex-col gap-1.5">
            <span className="text-sm text-slate-600 dark:text-slate-400">Offline after N missed polls</span>
            <input
              type="number"
              min={1}
              value={form.device_offline_missed_polls}
              onChange={(e) => setForm({ ...form, device_offline_missed_polls: Number(e.target.value) })}
              className="w-32 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-1.5 text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-amber-500/50"
            />
          </label>

          <label className="flex flex-col gap-1.5">
            <span className="text-sm text-slate-600 dark:text-slate-400">Shutdown floor (%)</span>
            <input
              type="number"
              min={0}
              max={99}
              step={1}
              value={form.shutdown_battery_floor_pct}
              onChange={(e) => setForm({ ...form, shutdown_battery_floor_pct: Number(e.target.value) })}
              className="w-32 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-1.5 text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-amber-500/50"
            />
            <span className="text-xs text-slate-500">Battery % that triggers shutdown alert</span>
          </label>

          <label className="flex flex-col gap-1.5">
            <span className="text-sm text-slate-600 dark:text-slate-400">Load alert threshold (%)</span>
            <input
              type="number"
              min={0}
              max={100}
              step={1}
              value={form.threshold_load_percent}
              onChange={(e) => setForm({ ...form, threshold_load_percent: Number(e.target.value) })}
              className="w-32 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-1.5 text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-amber-500/50"
            />
          </label>

          <label className="flex flex-col gap-1.5">
            <span className="text-sm text-slate-600 dark:text-slate-400">Temperature alert threshold (°C)</span>
            <input
              type="number"
              min={0}
              max={200}
              step={0.5}
              value={form.threshold_temp_celsius}
              onChange={(e) => setForm({ ...form, threshold_temp_celsius: Number(e.target.value) })}
              className="w-32 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-1.5 text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-amber-500/50"
            />
          </label>
        </div>
      </div>

      <div className="pt-1">
        <button
          onClick={handleSave}
          className="px-5 py-2 bg-cyan-500 hover:bg-cyan-400 text-slate-950 rounded-lg text-sm font-medium transition-colors shadow-lg shadow-cyan-500/20"
        >
          {saved ? 'Saved!' : 'Save Changes'}
        </button>
      </div>
        </>
      ) : (
        <p className="text-slate-500 text-sm">Loading settings… (set your API key above to connect)</p>
      )}
    </motion.div>
  )
}
