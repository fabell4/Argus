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
}

export interface HealthStatus {
  status: string
  service: string
  last_poll_at: string | null
  next_poll_at: string | null
  is_polling: boolean
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
