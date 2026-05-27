// Typed API client for Argus

import type {
  AlertConfig,
  Device,
  EventsPage,
  HealthStatus,
  RuntimeConfig,
  SnapshotsPage,
  PowerSnapshot,
  TriggerResponse,
} from '@/types'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const apiKey = localStorage.getItem('argus_api_key') ?? ''
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(init?.headers as Record<string, string> | undefined),
  }
  if (apiKey) headers['X-Api-Key'] = apiKey

  const resp = await fetch(path, { ...init, headers })
  if (!resp.ok) {
    const text = await resp.text()
    throw new Error(`API ${resp.status}: ${text}`)
  }
  return resp.json() as Promise<T>
}

// --- Snapshots ---
export const getSnapshots = (page = 1, pageSize = 50, deviceId?: string): Promise<SnapshotsPage> => {
  const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) })
  if (deviceId) params.set('device_id', deviceId)
  return request(`/api/snapshots?${params}`)
}

export const getLatestSnapshot = (deviceId?: string): Promise<PowerSnapshot | null> => {
  const params = deviceId ? `?device_id=${encodeURIComponent(deviceId)}` : ''
  return request(`/api/snapshots/latest${params}`)
}

// --- Events ---
export const getEvents = (page = 1, pageSize = 50): Promise<EventsPage> =>
  request(`/api/events?page=${page}&page_size=${pageSize}`)

export const getEventsFiltered = (
  page = 1,
  pageSize = 50,
  deviceId?: string,
  eventType?: string,
): Promise<EventsPage> => {
  const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) })
  if (deviceId) params.set('device_id', deviceId)
  if (eventType) params.set('event_type', eventType)
  return request(`/api/events?${params}`)
}

// --- Devices ---
export const getDevices = (): Promise<Device[]> => request('/api/devices')
export const updateDevices = (devices: Device[]): Promise<Device[]> =>
  request('/api/devices', { method: 'PUT', body: JSON.stringify(devices) })

// --- Trigger ---
export const triggerPoll = (): Promise<TriggerResponse> =>
  request('/api/trigger', { method: 'POST' })
export const getPollStatus = (): Promise<TriggerResponse> => request('/api/trigger/status')

// --- Config ---
export const getConfig = (): Promise<RuntimeConfig> => request('/api/config')
export const updateConfig = (cfg: RuntimeConfig): Promise<RuntimeConfig> =>
  request('/api/config', { method: 'PUT', body: JSON.stringify(cfg) })

// --- Health ---
export const getHealth = (): Promise<HealthStatus> => request('/api/health')

// --- Alerts ---
export const getAlerts = (): Promise<AlertConfig> => request('/api/alerts')
export const updateAlerts = (cfg: AlertConfig): Promise<AlertConfig> =>
  request('/api/alerts', { method: 'PUT', body: JSON.stringify(cfg) })
export const testAlert = (): Promise<{ status: string; message: string }> =>
  request('/api/alerts/test', { method: 'POST' })
