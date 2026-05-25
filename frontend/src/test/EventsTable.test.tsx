import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { EventsTable } from '@/components/EventsTable'
import * as apiModule from '@/lib/api'
import type { EventsPage } from '@/types'

vi.mock('@/lib/api', () => ({
  getEvents: vi.fn(),
}))

const makeEvent = (overrides = {}) => ({
  id: 1,
  timestamp: '2024-01-01T10:00:00Z',
  device_id: 'ups1',
  event_type: 'on_battery',
  metadata: {},
  ...overrides,
})

const makePage = (items = [makeEvent()]): EventsPage => ({
  page: 1,
  page_size: 50,
  total: items.length,
  items,
})

describe('EventsTable', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows loading state initially', () => {
    vi.mocked(apiModule.getEvents).mockReturnValue(new Promise(() => {}))
    render(<EventsTable />)
    expect(screen.getByText(/loading events/i)).toBeDefined()
  })

  it('shows empty message when no events', async () => {
    vi.mocked(apiModule.getEvents).mockResolvedValue(makePage([]))
    render(<EventsTable />)
    await waitFor(() => expect(screen.queryByText(/loading/i)).toBeNull())
    expect(screen.getByText(/no events recorded yet/i)).toBeDefined()
  })

  it('renders event rows', async () => {
    const events = [
      makeEvent({ id: 1, device_id: 'ups1', event_type: 'on_battery' }),
      makeEvent({ id: 2, device_id: 'ups2', event_type: 'power_restored' }),
    ]
    vi.mocked(apiModule.getEvents).mockResolvedValue(makePage(events))
    render(<EventsTable />)
    await waitFor(() => expect(screen.queryByText(/loading/i)).toBeNull())
    expect(screen.getByText('ups1')).toBeDefined()
    expect(screen.getByText('ups2')).toBeDefined()
    expect(screen.getByText('on_battery')).toBeDefined()
    expect(screen.getByText('power_restored')).toBeDefined()
  })

  it('renders all known event type badges', async () => {
    const eventTypes = [
      'on_battery',
      'power_restored',
      'battery_low',
      'threshold_crossed',
      'device_offline',
      'device_online',
    ]
    const events = eventTypes.map((t, i) => makeEvent({ id: i + 1, event_type: t }))
    vi.mocked(apiModule.getEvents).mockResolvedValue(makePage(events))
    render(<EventsTable />)
    await waitFor(() => expect(screen.queryByText(/loading/i)).toBeNull())
    for (const t of eventTypes) {
      expect(screen.getByText(t)).toBeDefined()
    }
  })

  it('renders unknown event type with fallback style', async () => {
    const events = [makeEvent({ event_type: 'custom_event' })]
    vi.mocked(apiModule.getEvents).mockResolvedValue(makePage(events))
    render(<EventsTable />)
    await waitFor(() => expect(screen.queryByText(/loading/i)).toBeNull())
    expect(screen.getByText('custom_event')).toBeDefined()
  })

  it('handles API error gracefully (stays in loading→empty)', async () => {
    vi.mocked(apiModule.getEvents).mockRejectedValue(new Error('Network Error'))
    render(<EventsTable />)
    await waitFor(() => expect(screen.queryByText(/loading/i)).toBeNull())
    // After error, events is empty → shows empty message
    expect(screen.getByText(/no events recorded yet/i)).toBeDefined()
  })
})
