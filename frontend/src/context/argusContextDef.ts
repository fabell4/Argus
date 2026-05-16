import { createContext } from 'react'
import type { Device, HealthStatus, PowerSnapshot, RuntimeConfig } from '@/types'

export interface ArgusContextType {
  snapshots: PowerSnapshot[]
  latest: PowerSnapshot | null
  health: HealthStatus | null
  config: RuntimeConfig | null
  devices: Device[]
  loading: boolean
  isPolling: boolean
  error: string | null
  runPoll: () => Promise<void>
  updateConfig: (patch: Partial<RuntimeConfig>) => Promise<void>
  refresh: () => void
}

export const ArgusContext = createContext<ArgusContextType | null>(null)
