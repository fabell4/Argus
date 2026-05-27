import { motion } from 'framer-motion'
import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { Bell, Send, CheckCircle, AlertCircle } from 'lucide-react'
import { getAlerts, updateAlerts, testAlert } from '@/lib/api'
import type {
  AlertConfig,
  AlertProvider,
  WebhookProvider,
  GotifyProvider,
  NtfyProvider,
  AppriseProvider,
} from '@/types'

// ─── styling constants ────────────────────────────────────────────────────────

const inputCls =
  'w-full bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-1.5 text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-violet-500/50'
const labelCls = 'text-xs text-slate-500 mb-1'

// ─── per-type provider state ──────────────────────────────────────────────────

interface ProviderStates {
  webhook: WebhookProvider
  gotify: GotifyProvider
  ntfy: NtfyProvider
  apprise: AppriseProvider
}

const DEFAULT_PROVIDERS: ProviderStates = {
  webhook: { type: 'webhook', enabled: false, url: '' },
  gotify:  { type: 'gotify',  enabled: false, url: '', token: '', priority: 5 },
  ntfy:    { type: 'ntfy',    enabled: false, url: '', topic: '', token: '', priority: '', tags: '' },
  apprise: { type: 'apprise', enabled: false, url: '' },
}

function toStates(providers: AlertProvider[]): ProviderStates {
  const s: ProviderStates = {
    webhook: { ...DEFAULT_PROVIDERS.webhook },
    gotify:  { ...DEFAULT_PROVIDERS.gotify },
    ntfy:    { ...DEFAULT_PROVIDERS.ntfy },
    apprise: { ...DEFAULT_PROVIDERS.apprise },
  }
  for (const p of providers) {
    if (p.type === 'webhook') s.webhook = { ...p }
    else if (p.type === 'gotify') s.gotify = { ...p }
    else if (p.type === 'ntfy') s.ntfy = { ...p }
    else if (p.type === 'apprise') s.apprise = { ...p }
  }
  return s
}

function fromStates(s: ProviderStates): AlertProvider[] {
  return [s.webhook, s.gotify, s.ntfy, s.apprise]
}

// ─── toggle switch ────────────────────────────────────────────────────────────

function Toggle({
  checked,
  onChange,
}: Readonly<{ checked: boolean; onChange: (v: boolean) => void }>) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-violet-500/50 ${
        checked ? 'bg-violet-500' : 'bg-slate-300 dark:bg-slate-600'
      }`}
    >
      <span
        className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
          checked ? 'translate-x-4' : 'translate-x-0'
        }`}
      />
    </button>
  )
}

// ─── provider section wrapper ─────────────────────────────────────────────────

function ProviderSection({
  title,
  description,
  enabled,
  onToggle,
  children,
}: Readonly<{
  title: string
  description?: string
  enabled: boolean
  onToggle: (v: boolean) => void
  children: ReactNode
}>) {
  return (
    <div className="border border-slate-200 dark:border-slate-700 rounded-xl overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 bg-slate-50 dark:bg-slate-800/60">
        <div>
          <p className="text-sm font-medium text-slate-700 dark:text-slate-200">{title}</p>
          {description && (
            <p className="text-xs text-slate-400 mt-0.5">{description}</p>
          )}
        </div>
        <Toggle checked={enabled} onChange={onToggle} />
      </div>
      {enabled && (
        <div className="p-4 space-y-3 border-t border-slate-200 dark:border-slate-700">
          {children}
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
  const [providers, setProviders] = useState<ProviderStates>({ ...DEFAULT_PROVIDERS })
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [testMsg, setTestMsg] = useState<string | null>(null)

  useEffect(() => {
    getAlerts()
      .then((cfg) => {
        setConfig(cfg)
        setProviders(toStates(cfg.providers))
      })
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load'))
      .finally(() => setLoading(false))
  }, [])

  const handleSave = async () => {
    setSaving(true)
    setError(null)
    try {
      const payload: AlertConfig = { ...config, providers: fromStates(providers) }
      const updated = await updateAlerts(payload)
      setConfig(updated)
      setProviders(toStates(updated.providers))
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

  const patchWebhook  = (patch: Partial<WebhookProvider>)  => setProviders((s) => ({ ...s, webhook:  { ...s.webhook,  ...patch } }))
  const patchGotify   = (patch: Partial<GotifyProvider>)   => setProviders((s) => ({ ...s, gotify:   { ...s.gotify,   ...patch } }))
  const patchNtfy     = (patch: Partial<NtfyProvider>)     => setProviders((s) => ({ ...s, ntfy:     { ...s.ntfy,     ...patch } }))
  const patchApprise  = (patch: Partial<AppriseProvider>)  => setProviders((s) => ({ ...s, apprise:  { ...s.apprise,  ...patch } }))

  const enabledCount = [providers.webhook, providers.gotify, providers.ntfy, providers.apprise]
    .filter((p) => p.enabled).length

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
          Configure notification providers for power event alerts.
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
          ['alert_on_battery',             'UPS on battery (power failure)'],
          ['alert_on_battery_low',         'Battery low'],
          ['alert_on_device_offline',      'Device offline / unreachable'],
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

      {/* Notification providers */}
      <div className="bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 space-y-4">
        <div>
          <h2 className="text-base font-semibold text-slate-800 dark:text-slate-200">
            {'Notification providers '}
            <span className="text-sm font-normal text-slate-500">({enabledCount} enabled)</span>
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Toggle a provider on to configure it. At least one must be enabled to receive alerts.
          </p>
        </div>

        <div className="space-y-3">
          {/* Webhook */}
          <ProviderSection
            title="Webhook"
            description="POST a JSON payload to any HTTP endpoint"
            enabled={providers.webhook.enabled}
            onToggle={(v) => patchWebhook({ enabled: v })}
          >
            <div>
              <label htmlFor="webhook-url" className={labelCls}>URL</label>
              <input
                id="webhook-url"
                type="url"
                placeholder="https://hooks.example.com/..."
                value={providers.webhook.url}
                onChange={(e) => patchWebhook({ url: e.target.value })}
                className={inputCls}
              />
            </div>
          </ProviderSection>

          {/* Gotify */}
          <ProviderSection
            title="Gotify"
            description="Self-hosted push notification server"
            enabled={providers.gotify.enabled}
            onToggle={(v) => patchGotify({ enabled: v })}
          >
            <div>
              <label htmlFor="gotify-url" className={labelCls}>Server URL</label>
              <input
                id="gotify-url"
                type="url"
                placeholder="https://gotify.example.com"
                value={providers.gotify.url}
                onChange={(e) => patchGotify({ url: e.target.value })}
                className={inputCls}
              />
            </div>
            <div>
              <label htmlFor="gotify-token" className={labelCls}>App token</label>
              <input
                id="gotify-token"
                type="password"
                placeholder="Application token"
                value={providers.gotify.token}
                onChange={(e) => patchGotify({ token: e.target.value })}
                className={inputCls}
              />
            </div>
            <div>
              <label htmlFor="gotify-priority" className={labelCls}>Priority (0–10, default 5)</label>
              <input
                id="gotify-priority"
                type="number"
                min={0}
                max={10}
                value={providers.gotify.priority ?? 5}
                onChange={(e) => patchGotify({ priority: Number(e.target.value) })}
                className={`${inputCls} w-24`}
              />
            </div>
          </ProviderSection>

          {/* ntfy */}
          <ProviderSection
            title="ntfy"
            description="Simple HTTP-based pub-sub notification service"
            enabled={providers.ntfy.enabled}
            onToggle={(v) => patchNtfy({ enabled: v })}
          >
            <div>
              <label htmlFor="ntfy-topic" className={labelCls}>Topic</label>
              <input
                id="ntfy-topic"
                type="text"
                placeholder="argus-alerts"
                value={providers.ntfy.topic}
                onChange={(e) => patchNtfy({ topic: e.target.value })}
                className={inputCls}
              />
            </div>
            <div>
              <label htmlFor="ntfy-url" className={labelCls}>Server URL (leave blank for ntfy.sh)</label>
              <input
                id="ntfy-url"
                type="url"
                placeholder="https://ntfy.sh"
                value={providers.ntfy.url}
                onChange={(e) => patchNtfy({ url: e.target.value })}
                className={inputCls}
              />
            </div>
            <div>
              <label htmlFor="ntfy-token" className={labelCls}>Token (optional)</label>
              <input
                id="ntfy-token"
                type="password"
                placeholder="tk_..."
                value={providers.ntfy.token ?? ''}
                onChange={(e) => patchNtfy({ token: e.target.value })}
                className={inputCls}
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label htmlFor="ntfy-priority" className={labelCls}>Priority (optional)</label>
                <input
                  id="ntfy-priority"
                  type="text"
                  placeholder="default"
                  value={providers.ntfy.priority ?? ''}
                  onChange={(e) => patchNtfy({ priority: e.target.value })}
                  className={inputCls}
                />
              </div>
              <div>
                <label htmlFor="ntfy-tags" className={labelCls}>Tags (optional)</label>
                <input
                  id="ntfy-tags"
                  type="text"
                  placeholder="warning,rotating_light"
                  value={providers.ntfy.tags ?? ''}
                  onChange={(e) => patchNtfy({ tags: e.target.value })}
                  className={inputCls}
                />
              </div>
            </div>
          </ProviderSection>

          {/* Apprise */}
          <ProviderSection
            title="Apprise"
            description="100+ services: Discord, Telegram, Slack, and more"
            enabled={providers.apprise.enabled}
            onToggle={(v) => patchApprise({ enabled: v })}
          >
            <div>
              <label htmlFor="apprise-url" className={labelCls}>Apprise API URL</label>
              <input
                id="apprise-url"
                type="url"
                placeholder="https://apprise.example.com/notify/apprise"
                value={providers.apprise.url}
                onChange={(e) => patchApprise({ url: e.target.value })}
                className={inputCls}
              />
              <p className="text-xs text-slate-400 mt-1">
                Full URL with config ID (e.g. https://apprise.example.com/notify/argus) or stateless URL
              </p>
            </div>
          </ProviderSection>
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
          disabled={testing || enabledCount === 0}
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
