import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { usePowerData } from '@/hooks/usePowerData'
import * as apiModule from '@/lib/api'
import type { SnapshotsPage } from '@/types'

vi.mock('@/lib/api', () => ({
  getSnapshots: vi.fn(),
}))

const makeSnapshot = (id = 1) => ({
  id,
  timestamp: '2024-01-01T00:00:00Z',
  device_id: 'ups1',
  device_type: 'ups',
  power_watts: 100,
  load_percent: 40,
  voltage: 230,
  battery_percent: 90,
  runtime_seconds: 3600,
  ups_status: 'OL',
  temperature_c: null,
})

const makePage = (items = [makeSnapshot()]): SnapshotsPage => ({
  page: 1, page_size: 100, total: items.length, items,
})

describe('usePowerData', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('starts in loading state', () => {
    vi.mocked(apiModule.getSnapshots).mockReturnValue(new Promise(() => {}))
    const { result } = renderHook(() => usePowerData())
    expect(result.current.loading).toBe(true)
    expect(result.current.data).toEqual([])
    expect(result.current.error).toBeNull()
  })

  it('resolves data on success', async () => {
    vi.mocked(apiModule.getSnapshots).mockResolvedValue(makePage())
    const { result } = renderHook(() => usePowerData())
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.data).toHaveLength(1)
    expect(result.current.error).toBeNull()
  })

  it('sets error on failure', async () => {
    vi.mocked(apiModule.getSnapshots).mockRejectedValue(new Error('API Error'))
    const { result } = renderHook(() => usePowerData())
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.error).toBe('API Error')
    expect(result.current.data).toEqual([])
  })

  it('sets generic error for non-Error rejection', async () => {
    vi.mocked(apiModule.getSnapshots).mockRejectedValue('string error')
    const { result } = renderHook(() => usePowerData())
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.error).toBe('Failed to load data')
  })

  it('passes deviceId to getSnapshots', async () => {
    vi.mocked(apiModule.getSnapshots).mockResolvedValue(makePage())
    const { result } = renderHook(() => usePowerData('ups1'))
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(vi.mocked(apiModule.getSnapshots)).toHaveBeenCalledWith(1, 100, 'ups1')
  })

  it('passes custom pageSize to getSnapshots', async () => {
    vi.mocked(apiModule.getSnapshots).mockResolvedValue(makePage())
    const { result } = renderHook(() => usePowerData(undefined, 25))
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(vi.mocked(apiModule.getSnapshots)).toHaveBeenCalledWith(1, 25, undefined)
  })

  it('re-fetches when deviceId changes', async () => {
    vi.mocked(apiModule.getSnapshots).mockResolvedValue(makePage())
    const { result, rerender } = renderHook(
      ({ deviceId }: { deviceId?: string }) => usePowerData(deviceId),
      { initialProps: { deviceId: 'ups1' } },
    )
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(vi.mocked(apiModule.getSnapshots)).toHaveBeenCalledTimes(1)

    rerender({ deviceId: 'ups2' })
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(vi.mocked(apiModule.getSnapshots)).toHaveBeenCalledTimes(2)
    expect(vi.mocked(apiModule.getSnapshots)).toHaveBeenLastCalledWith(1, 100, 'ups2')
  })
})
