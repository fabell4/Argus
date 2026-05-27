import { motion } from 'framer-motion'
import { useEffect, useState } from 'react'
import { Bell, Plus, Trash2, Send, CheckCircle, AlertCircle, ChevronDown, ChevronUp } from 'lucide-react'
import { getAlerts, updateAlerts, testAlert } from '@/lib/api'
import type { AlertConfig, AlertProvider } from '@/types'

// ─── helpers ────────────────────────────────────────────────────────────────

function emptyProvider(type: AlertProvider['type']): AlertProvider {
  switch (type) {
    case 'webhook': return { type: 'webhook', enabled: true, url: '' }
    case 'gotify':  return { type: 'gotify',  enabled: true, url: '', token: '', priority: 0 }
    case 'ntfy':    return { type: 'ntfy',    enabled: true, url: '', topic: '', token: '', priority: '', tags: '' }
    case 'apprise': return { type: 'apprise', enabled: true, url: '' }
  }
}

const PROVIDER_LABELS: Record<AlertProvider['type'], string> = {
  webhook: 'Webhook',
  gotify: 'Gotify',
  ntfy: 'ntfy',
  apprise: 'Apprise',
}

const inputCls = 'w-full bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-1.5 text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-violet-500/50'
const labelCls = 'text-xs text-slate-500 mb-1'

// ─── per-provider form ───────────────────────────────────────────────────────

function ProviderForm({
  provider,
  index,
  onChange,
  onRemove,
}: Readonly<{
  provider: AlertProvider
  index: number
  onChange: (updated: AlertProvider) => void
  onRemove: () => void
}>) {
  const [expanded, setExpanded] = useState(true)

  return (
    <div className="border border-slate-200 dark:border-slate-700 rounded-xl overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-slate-50 dark:bg-slate-800/60">
        <button
          type="button"
          onClick={() => setExpanded((e) => !e)}
          className="flex items-center gap-2 text-sm font-medium text-slate-700 dark:text-slate-200"
        >
          {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          {PROVIDER_LABELS[provider.type]} #{index + 1}
        </button>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-1.5 cursor-pointer text-xs text-slate-500">
            <input
              type="checkbox"
              checked={provider.enabled}
              onChange={(e) => onChange({ ...provider, enabled: e.target.checked })}
              className="accent-violet-500"
            />
            <span>Enabled</span>
          </label>
          <button
            type="button"
            onClick={onRemove}
            className="text-slate-400 hover:text-red-400 transition-colors"
          >
            <Trash2 size={14} />
          </button>
        </div>
      </div>

      {/* Fields */}
      {expanded && (
        <div className="p-4 space-y-3">
          {/* URL (all types) */}
          <div>
            <label htmlFor={`url-${index}`} className={labelCls}>URL</label>
            <input
              id={`url-${index}`}
              type="url"
              placeholder="https://..."
              value={provider.url}
              onChange={(e) => onChange({ ...provider, url: e.target.value })}
              className={inputCls}
            />
          </div>

          {/* Gotify token + priority */}
          {provider.type === 'gotify' && (
            <>
              <div>
                <label htmlFor={`token-${index}`} className={labelCls}>Token</label>
                <input
                  id={`token-${index}`}
                  type="password"
                  placeholder="Gotify app token"
                  value={provider.token}
                  onChange={(e) => onChange({ ...provider, token: e.target.value })}
                  className={inputCls}
                />
              </div>
              <div>
                <label htmlFor={`priority-${index}`} className={labelCls}>Priority (0 = default)</label>
                <input
                  id={`priority-${index}`}
                  type="number"
                  min={0}
                  max={10}
                  placeholder="0"
                  value={provider.priority ?? 0}
                  onChange={(e) => onChange({ ...provider, priority: Number(e.target.value) })}
                  className={`${inputCls} w-24`}
                />
              </div>
            </>
          )}

          {/* ntfy topic / token / priority / tags */}
          {provider.type === 'ntfy' && (
            <>
              <div>
                <label htmlFor={`topic-${index}`} className={labelCls}>Topic</label>
                <input
                  id={`topic-${index}`}
                  type="text"
                  placeholder="my-argus-alerts"
                  value={provider.topic}
                  onChange={(e) => onChange({ ...provider, topic: e.target.value })}
                  className={inputCls}
                />
              </div>
              <div>
                <label htmlFor={`ntfy-token-${index}`} className={labelCls}>Token (optional)</label>
                <input
                  id={`ntfy-token-${index}`}
                  type="password"
                  placeholder="tk_..."
                  value={provider.token ?? ''}
                  onChange={(e) => onChange({ ...provider, token: e.target.value })}
                  className={inputCls}
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label htmlFor={`ntfy-priority-${index}`} className={labelCls}>Priority (optional)</label>
                  <input
                    id={`ntfy-priority-${index}`}
                    type="text"
                    placeholder="default"
                    value={provider.priority ?? ''}
                    onChange={(e) => onChange({ ...provider, priority: e.target.value })}
                    className={inputCls}
                  />
                </div>
                <div>
                  <label htmlFor={`ntfy-tags-${index}`} className={labelCls}>Tags (optional)</label>
                  <input
                    id={`ntfy-tags-${index}`}
                    type="text"
                    placeholder="warning,rotating_light"
                    value={provider.tags ?? ''}
                    onChange={(e) => onChange({ ...provider, tags: e.target.value })}
                    className={inputCls}
                  />
                </div>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  )
}

// ─── main page ───────────────────────────────────────────────────────────────

export function Alerts() {
  const [config, setConfig] = useState<AlertConfig>({
    providers: [],
    failure_threshold: 3,
    cooldown_seconds: 3600,
    alert_on_battery: true,
    alert_on_battery_low: true,
    alert_on_device_offline: true,
    alert_recovery_notifications: true,
    recovery_cooldown_seconds: 300,
  })
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [testMsg, setTestMsg] = useState<string | null>(null)
  const [addType, setAddType] = useState<AlertProvider['type']>('webhook')

  useEffect(() => {
    getAlerts()
      .then(setConfig)
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load'))
      .finally(() => setLoading(false))
  }, [])

  const handleSave = async () => {
    setSaving(true)
    setError(null)
    try {
      const updated = await updateAlerts(config)
      setConfig(updated)
      setSaved(true)
      setTimeout(() => setSaved(false), 2500)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  const handleTest = async () => {
    setTesting(true)
    setTestMsg(null)
    try {
      const res = await testAlert()
      setTestMsg(res.message)
      setTimeout(() => setTestMsg(null), 4000)
    } catch (e) {
      setTestMsg(e instanceof Error ? e.message : 'Test failed')
    } finally {
      setTesting(false)
    }
  }

  const addProvider = () => {
    setConfig((c) => ({ ...c, providers: [...c.providers, emptyProvider(addType)] }))
  }

  const updateProvider = (index: number, updated: AlertProvider) => {
    setConfig((c) => {
      const providers = [...c.providers]
      providers[index] = updated
      return { ...c, providers }
    })
  }

  const removeProvider = (index: number) => {
    setConfig((c) => ({ ...c, providers: c.providers.filter((_, i) => i !== index) }))
  }

  if (loading) return <p className="text-slate-500 text-sm p-4">Loading alert config…</p>

  let saveLabel = 'Save changes'
  if (saving) saveLabel = 'Saving…'
  else if (saved) saveLabel = 'Saved!'

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-6"
    >
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Alert Configuration</h1>
        <p className="text-slate-500 text-sm mt-0.5">
          Configure notification providers for poll failure alerts.
        </p>
      </div>

      {error && (
        <div className="flex items-center gap-2 px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
          <AlertCircle size={16} className="shrink-0" />
          {error}
        </div>
      )}

      {testMsg && (
        <div className="flex items-center gap-2 px-4 py-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-sm">
          <CheckCircle size={16} className="shrink-0" />
          {testMsg}
        </div>
      )}

      {/* Thresholds */}
      <div className="bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 space-y-4">
        <h2 className="text-base font-semibold text-slate-800 dark:text-slate-200">Thresholds</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <label className="flex flex-col gap-1.5">
            <span className={labelCls}>Failure threshold (consecutive failures before alert)</span>
            <input
              type="number"
              min={1}
              max={100}
              value={config.failure_threshold}
              onChange={(e) => setConfig((c) => ({ ...c, failure_threshold: Number(e.target.value) }))}
              className={`${inputCls} w-28`}
            />
          </label>
          <label className="flex flex-col gap-1.5">
            <span className={labelCls}>Cooldown (seconds between repeated alerts)</span>
            <input
              type="number"
              min={60}
              max={86400}
              value={config.cooldown_seconds}
              onChange={(e) => setConfig((c) => ({ ...c, cooldown_seconds: Number(e.target.value) }))}
              className={`${inputCls} w-28`}
            />
          </label>
          <label className="flex flex-col gap-1.5">
            <span className={labelCls}>Recovery cooldown (seconds before re-alerting after recovery)</span>
            <input
              type="number"
              min={60}
              max={86400}
              value={config.recovery_cooldown_seconds}
              onChange={(e) => setConfig((c) => ({ ...c, recovery_cooldown_seconds: Number(e.target.value) }))}
              className={`${inputCls} w-28`}
            />
          </label>
        </div>
      </div>

      {/* Alert events */}
      <div className="bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 space-y-3">
        <h2 className="text-base font-semibold text-slate-800 dark:text-slate-200">Alert events</h2>
        <p className="text-xs text-slate-500">Choose which conditions trigger notifications.</p>
        {([
          ['alert_on_battery',           'UPS on battery (power failure)'],
          ['alert_on_battery_low',       'Battery low'],
          ['alert_on_device_offline',    'Device offline / unreachable'],
          ['alert_recovery_notifications', 'Recovery notifications (when condition clears)'],
        ] as [keyof AlertConfig, string][]).map(([key, label]) => (
          <label key={key} className="flex items-center gap-2 cursor-pointer text-sm text-slate-700 dark:text-slate-300">
            <input
              type="checkbox"
              checked={Boolean(config[key])}
              onChange={(e) => setConfig((c) => ({ ...c, [key]: e.target.checked }))}
              className="accent-violet-500"
            />
            {label}
          </label>
        ))}
      </div>

      {/* Providers */}
      <div className="bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold text-slate-800 dark:text-slate-200">
            <span>Providers</span>
            <span className="ml-2 text-sm font-normal text-slate-500">
              ({config.providers.length})
            </span>
          </h2>
        </div>

        {config.providers.length === 0 && (
          <p className="text-sm text-slate-500 py-2">No providers configured. Add one below.</p>
        )}

        <div className="space-y-3">
          {config.providers.map((p, i) => (
            <ProviderForm
              key={`${p.type}-${p.url}`}
              provider={p}
              index={i}
              onChange={(updated) => updateProvider(i, updated)}
              onRemove={() => removeProvider(i)}
            />
          ))}
        </div>

        {/* Add provider */}
        <div className="flex items-center gap-2 pt-2">
          <select
            value={addType}
            onChange={(e) => setAddType(e.target.value as AlertProvider['type'])}
            className="bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-1.5 text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-violet-500/50"
          >
            {(Object.keys(PROVIDER_LABELS) as AlertProvider['type'][]).map((t) => (
              <option key={t} value={t}>{PROVIDER_LABELS[t]}</option>
            ))}
          </select>
          <button
            type="button"
            onClick={addProvider}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-violet-600/20 hover:bg-violet-600/30 text-violet-400 text-sm font-medium border border-violet-500/30 transition-colors"
          >
            <Plus size={14} />
            Add provider
          </button>
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-3 flex-wrap">
        <button
          onClick={handleSave}
          disabled={saving}
          className="flex items-center gap-2 px-5 py-2 rounded-lg bg-violet-600 hover:bg-violet-500 disabled:opacity-60 disabled:cursor-not-allowed text-white text-sm font-medium transition-colors shadow-lg shadow-violet-500/20"
        >
          {saved ? <CheckCircle size={14} /> : null}
          {saveLabel}
        </button>

        <button
          onClick={handleTest}
          disabled={testing || config.providers.filter((p) => p.enabled).length === 0}
          className="flex items-center gap-2 px-5 py-2 rounded-lg bg-slate-700 hover:bg-slate-600 disabled:opacity-40 disabled:cursor-not-allowed text-slate-200 text-sm font-medium transition-colors"
        >
          <Send size={14} className={testing ? 'animate-pulse' : ''} />
          {testing ? 'Sending…' : 'Send test alert'}
        </button>

        <div className="flex items-center gap-1.5 text-xs text-slate-500">
          <Bell size={12} />
          Test alert fires via all enabled providers
        </div>
      </div>
    </motion.div>
  )
}
