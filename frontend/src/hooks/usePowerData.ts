import { useEffect, useState } from 'react'
import { getSnapshots } from '@/lib/api'
import type { PowerSnapshot } from '@/types'

export function usePowerData(deviceId?: string, pageSize = 100): {
  data: PowerSnapshot[]
  loading: boolean
  error: string | null
} {
  const [data, setData] = useState<PowerSnapshot[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    getSnapshots(1, pageSize, deviceId)
      .then((page) => {
        if (!cancelled) {
          setData(page.items)
          setError(null)
        }
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Failed to load data')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [deviceId, pageSize])

  return { data, loading, error }
}
