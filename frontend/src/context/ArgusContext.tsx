import { useCallback, useEffect, useRef, useState } from 'react'
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

export function ArgusProvider({ children }: { children: React.ReactNode }) {
  const [snapshots, setSnapshots] = useState<PowerSnapshot[]>([])
  const [latest, setLatest] = useState<PowerSnapshot | null>(null)
  const [health, setHealth] = useState<HealthStatus | null>(null)
  const [config, setConfig] = useState<RuntimeConfig | null>(null)
  const [devices, setDevices] = useState<Device[]>([])
  const [loading, setLoading] = useState(true)
  const [isPolling, setIsPolling] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const fetchAll = useCallback(async () => {
    try {
      const [snapshotsPage, latestSnap, healthData, configData, devicesData] = await Promise.all([
        getSnapshots(),
        getLatestSnapshot(),
        getHealth(),
        getConfig(),
        getDevices(),
      ])
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
    } else {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current)
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

  const value: ArgusContextType = {
    snapshots,
    latest,
    health,
    config,
    devices,
    loading,
    isPolling,
    error,
    runPoll,
    updateConfig,
    refresh: fetchAll,
  }

  return <ArgusContext.Provider value={value}>{children}</ArgusContext.Provider>
}
