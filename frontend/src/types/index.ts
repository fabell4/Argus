// Argus shared TypeScript types

export interface PowerSnapshot {
  id: number
  timestamp: string
  device_id: string
  device_type: string
  power_watts: number | null
  load_percent: number | null
  voltage: number | null
  battery_percent: number | null
  runtime_seconds: number | null
  ups_status: string | null
  temperature_c: number | null
}

export interface PowerEvent {
  id: number
  timestamp: string
  device_id: string
  event_type: string
  metadata: Record<string, unknown>
}

export interface Device {
  id: string
  name: string
  type: string
  poller: string
  host: string
  port: number
  enabled: boolean
  connection_config: Record<string, unknown>
  model?: string | null
  firmware?: string | null
  serial?: string | null
  manufacturer?: string | null
  last_seen?: string | null
}

export interface HealthStatus {
  status: string
  service: string
  version?: string
  last_poll_at: string | null
  next_poll_at: string | null
  is_polling: boolean
  github_repo?: string
}

export interface RuntimeConfig {
  poll_interval_minutes: number
  enabled_exporters: string[]
  scanning_disabled: boolean
  scheduler_paused: boolean
}

export interface SnapshotsPage {
  page: number
  page_size: number
  total: number
  items: PowerSnapshot[]
}

export interface EventsPage {
  page: number
  page_size: number
  total: number
  items: PowerEvent[]
}

export interface TriggerResponse {
  status: string
  message: string
}

export interface WebhookProvider {
  type: 'webhook'
  enabled: boolean
  url: string
}

export interface GotifyProvider {
  type: 'gotify'
  enabled: boolean
  url: string
  token: string
}

export interface NtfyProvider {
  type: 'ntfy'
  enabled: boolean
  url: string
  topic: string
}

export interface AppriseProvider {
  type: 'apprise'
  enabled: boolean
  url: string
}

export type AlertProvider = WebhookProvider | GotifyProvider | NtfyProvider | AppriseProvider

export interface AlertConfig {
  providers: AlertProvider[]
  failure_threshold: number
  cooldown_seconds: number
}
