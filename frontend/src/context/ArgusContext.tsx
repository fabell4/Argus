import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { Device, HealthStatus, PowerSnapshot, RuntimeConfig } from '@/types'
import {
  getConfig,
  getDevices,
  getHealth,
  getLatestSnapshot,
  getSnapshots,
  getPollStatus,
  triggerPoll,
  updateConfig as apiUpdateConfig,
} from '@/lib/api'
import { ArgusContext, type ArgusContextType } from './argusContextDef'

function getInitialTheme(): 'dark' | 'light' {
  const stored = localStorage.getItem('argus_theme')
  if (stored === 'light' || stored === 'dark') return stored
  return 'dark'
}

function applyTheme(theme: 'dark' | 'light') {
  if (theme === 'dark') {
    document.documentElement.classList.add('dark')
  } else {
    document.documentElement.classList.remove('dark')
  }
}

export function ArgusProvider({ children }: Readonly<{ children: React.ReactNode }>) {
  const [snapshots, setSnapshots] = useState<PowerSnapshot[]>([])
  const [latest, setLatest] = useState<PowerSnapshot | null>(null)
  const [health, setHealth] = useState<HealthStatus | null>(null)
  const [config, setConfig] = useState<RuntimeConfig | null>(null)
  const [devices, setDevices] = useState<Device[]>([])
  const [loading, setLoading] = useState(true)
  const [isPolling, setIsPolling] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [theme, setTheme] = useState<'dark' | 'light'>(getInitialTheme)
  const [needsApiKey, setNeedsApiKey] = useState(() => !localStorage.getItem('argus_api_key'))
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  // Tracks device count across fetches so snapshot page size scales without
  // creating a dependency cycle on the devices state array.
  const deviceCountRef = useRef(0)

  // Apply theme on mount and changes
  useEffect(() => {
    applyTheme(theme)
    localStorage.setItem('argus_theme', theme)
  }, [theme])

  // Show setup screen whenever a 401 is received from any API call
  useEffect(() => {
    const handler = () => setNeedsApiKey(true)
    globalThis.addEventListener('argus:unauthorized', handler)
    return () => globalThis.removeEventListener('argus:unauthorized', handler)
  }, [])

  const toggleTheme = useCallback(() => {
    setTheme((t) => (t === 'dark' ? 'light' : 'dark'))
  }, [])

  const fetchAll = useCallback(async () => {
    try {
      // Scale snapshot page so each device gets ~50 data points in the chart.
      const pageSize = Math.max(50, deviceCountRef.current * 50)
      const [snapshotsPage, latestSnap, healthData, configData, devicesData] = await Promise.all([
        getSnapshots(1, pageSize),
        getLatestSnapshot(),
        getHealth(),
        getConfig(),
        getDevices(),
      ])
      deviceCountRef.current = devicesData.length
      setSnapshots(snapshotsPage.items)
      setLatest(latestSnap)
      setHealth(healthData)
      setConfig(configData)
      setDevices(devicesData)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data')
    } finally {
      setLoading(false)
    }
  }, [])

  // Poll for status changes while a poll cycle is running
  useEffect(() => {
    if (isPolling) {
      pollIntervalRef.current = setInterval(async () => {
        const status = await getPollStatus().catch(() => null)
        if (status?.status !== 'running') {
          setIsPolling(false)
          await fetchAll()
        }
      }, 2000)
    } else if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current)
    }
    return () => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current)
    }
  }, [isPolling, fetchAll])

  useEffect(() => {
    fetchAll()
  }, [fetchAll])

  const runPoll = useCallback(async () => {
    try {
      await triggerPoll()
      setIsPolling(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to trigger poll')
    }
  }, [])

  const updateConfig = useCallback(
    async (patch: Partial<RuntimeConfig>) => {
      if (!config) return
      const merged = { ...config, ...patch }
      const updated = await apiUpdateConfig(merged)
      setConfig(updated)
    },
    [config]
  )

  const saveApiKey = useCallback((key: string) => {
    localStorage.setItem('argus_api_key', key)
    setNeedsApiKey(false)
    fetchAll()
  }, [fetchAll])

  const value: ArgusContextType = useMemo(
    () => ({
      snapshots,
      latest,
      health,
      config,
      devices,
      loading,
      isPolling,
      error,
      theme,
      needsApiKey,
      toggleTheme,
      runPoll,
      updateConfig,
      refresh: fetchAll,
      saveApiKey,
    }),
    [snapshots, latest, health, config, devices, loading, isPolling, error, theme, needsApiKey, toggleTheme, runPoll, updateConfig, fetchAll, saveApiKey]
  )

  return <ArgusContext.Provider value={value}>{children}</ArgusContext.Provider>
}
