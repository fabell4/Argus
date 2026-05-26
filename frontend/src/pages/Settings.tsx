import { motion } from 'framer-motion'
import { useEffect, useState } from 'react'
import { useArgus } from '@/hooks/useArgus'
import type { RuntimeConfig } from '@/types'

export function Settings() {
  const { config, updateConfig } = useArgus()
  const [form, setForm] = useState<RuntimeConfig | null>(null)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    if (config) setForm(config)
  }, [config])

  if (!form) return <p className="text-slate-500 text-sm">Loading settings…</p>

  const handleSave = async () => {
    await updateConfig(form)
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-6"
    >
      <h1 className="text-2xl font-bold text-slate-100">Settings</h1>

      <div className="bg-slate-900/40 border border-slate-800 rounded-2xl p-4 md:p-6 space-y-4">
        <h2 className="text-lg font-semibold text-slate-200">Scheduler</h2>

        <label className="flex flex-col gap-1.5">
          <span className="text-sm text-slate-400">Poll interval (minutes)</span>
          <input
            type="number"
            min={1}
            max={10080}
            value={form.poll_interval_minutes}
            onChange={(e) => setForm({ ...form, poll_interval_minutes: Number(e.target.value) })}
            className="w-32 bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-violet-500/50"
          />
        </label>

        <label className="flex items-center gap-2.5 cursor-pointer">
          <input
            type="checkbox"
            checked={form.scheduler_paused}
            onChange={(e) => setForm({ ...form, scheduler_paused: e.target.checked })}
            className="w-4 h-4 rounded border-slate-600 bg-slate-800 accent-violet-500"
          />
          <span className="text-sm text-slate-300">Pause scheduler</span>
        </label>

        <label className="flex items-center gap-2.5 cursor-pointer">
          <input
            type="checkbox"
            checked={form.scanning_disabled}
            onChange={(e) => setForm({ ...form, scanning_disabled: e.target.checked })}
            className="w-4 h-4 rounded border-slate-600 bg-slate-800 accent-violet-500"
          />
          <span className="text-sm text-slate-300">Disable scanning</span>
        </label>
      </div>

      <div className="bg-slate-900/40 border border-slate-800 rounded-2xl p-4 md:p-6 space-y-4">
        <h2 className="text-lg font-semibold text-slate-200">Exporters</h2>
        {(['sqlite', 'prometheus', 'influxdb', 'loki'] as const).map((exporter) => (
          <label key={exporter} className="flex items-center gap-2.5 cursor-pointer">
            <input
              type="checkbox"
              checked={form.enabled_exporters.includes(exporter)}
              onChange={(e) => {
                const updated = e.target.checked
                  ? [...form.enabled_exporters, exporter]
                  : form.enabled_exporters.filter((ex) => ex !== exporter)
                setForm({ ...form, enabled_exporters: updated })
              }}
              className="w-4 h-4 rounded border-slate-600 bg-slate-800 accent-violet-500"
            />
            <span className="text-sm text-slate-300">{exporter}</span>
          </label>
        ))}
      </div>

      <div className="bg-slate-900/40 border border-slate-800 rounded-2xl p-4 md:p-6 space-y-4">
        <h2 className="text-lg font-semibold text-slate-200">NUT Connection</h2>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <label className="flex flex-col gap-1.5">
            <span className="text-sm text-slate-400">Host</span>
            <input
              type="text"
              value={form.nut_host}
              onChange={(e) => setForm({ ...form, nut_host: e.target.value })}
              className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-violet-500/50"
            />
          </label>

          <label className="flex flex-col gap-1.5">
            <span className="text-sm text-slate-400">Port</span>
            <input
              type="number"
              min={1}
              max={65535}
              value={form.nut_port}
              onChange={(e) => setForm({ ...form, nut_port: Number(e.target.value) })}
              className="w-32 bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-violet-500/50"
            />
          </label>

          <label className="flex flex-col gap-1.5">
            <span className="text-sm text-slate-400">Username</span>
            <input
              type="text"
              value={form.nut_username}
              onChange={(e) => setForm({ ...form, nut_username: e.target.value })}
              className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-violet-500/50"
            />
          </label>

          <label className="flex flex-col gap-1.5">
            <span className="text-sm text-slate-400">Password</span>
            <input
              type="password"
              value={form.nut_password}
              placeholder="Leave blank to keep existing"
              onChange={(e) => setForm({ ...form, nut_password: e.target.value })}
              className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-violet-500/50"
            />
          </label>

          <label className="flex flex-col gap-1.5">
            <span className="text-sm text-slate-400">UPS Name(s)</span>
            <input
              type="text"
              value={form.nut_ups_name}
              placeholder="ups1,ups2"
              onChange={(e) => setForm({ ...form, nut_ups_name: e.target.value })}
              className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-violet-500/50"
            />
            <span className="text-xs text-slate-500">Used when auto-discover is off. Enter a single UPS name or a comma-separated list such as ups1,ups2.</span>
          </label>
        </div>

        <label className="flex items-center gap-2.5 cursor-pointer">
          <input
            type="checkbox"
            checked={form.nut_auto_discover}
            onChange={(e) => setForm({ ...form, nut_auto_discover: e.target.checked })}
            className="w-4 h-4 rounded border-slate-600 bg-slate-800 accent-violet-500"
          />
          <span className="text-sm text-slate-300">Auto-discover UPS devices</span>
        </label>
      </div>

      <div className="bg-slate-900/40 border border-slate-800 rounded-2xl p-4 md:p-6 space-y-4">
        <h2 className="text-lg font-semibold text-slate-200">Event Thresholds</h2>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <label className="flex flex-col gap-1.5">
            <span className="text-sm text-slate-400">Offline after N missed polls</span>
            <input
              type="number"
              min={1}
              value={form.device_offline_missed_polls}
              onChange={(e) => setForm({ ...form, device_offline_missed_polls: Number(e.target.value) })}
              className="w-32 bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-violet-500/50"
            />
          </label>

          <label className="flex flex-col gap-1.5">
            <span className="text-sm text-slate-400">Shutdown floor (%)</span>
            <input
              type="number"
              min={0}
              max={99}
              step={1}
              value={form.shutdown_battery_floor_pct}
              onChange={(e) => setForm({ ...form, shutdown_battery_floor_pct: Number(e.target.value) })}
              className="w-32 bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-violet-500/50"
            />
            <span className="text-xs text-slate-500">Battery % that triggers shutdown alert</span>
          </label>

          <label className="flex flex-col gap-1.5">
            <span className="text-sm text-slate-400">Load alert threshold (%)</span>
            <input
              type="number"
              min={0}
              max={100}
              step={1}
              value={form.threshold_load_percent}
              onChange={(e) => setForm({ ...form, threshold_load_percent: Number(e.target.value) })}
              className="w-32 bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-violet-500/50"
            />
          </label>

          <label className="flex flex-col gap-1.5">
            <span className="text-sm text-slate-400">Temperature alert threshold (°C)</span>
            <input
              type="number"
              min={0}
              max={200}
              step={0.5}
              value={form.threshold_temp_celsius}
              onChange={(e) => setForm({ ...form, threshold_temp_celsius: Number(e.target.value) })}
              className="w-32 bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-violet-500/50"
            />
          </label>
        </div>
      </div>

      <div className="pt-1">
        <button
          onClick={handleSave}
          className="px-5 py-2 bg-violet-600 hover:bg-violet-500 text-white rounded-lg text-sm font-medium transition-colors shadow-lg shadow-violet-500/20"
        >
          {saved ? 'Saved!' : 'Save Changes'}
        </button>
      </div>
    </motion.div>
  )
}
