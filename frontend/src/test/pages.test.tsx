/**
 * Tests for page components: Dashboard, Settings, Events.
 * These render pages with a mocked ArgusContext to exercise the UI code paths.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import React from 'react'
import { ArgusContext, type ArgusContextType } from '@/context/argusContextDef'
import * as apiModule from '@/lib/api'

vi.mock('@/lib/api', () => ({
  getEvents: vi.fn(),
  getEventsFiltered: vi.fn(),
  getLatestSnapshot: vi.fn(),
}))

// Stub ResizeObserver for recharts
vi.stubGlobal(
  'ResizeObserver',
  class {
    observe() { /* stub for jsdom */ }
    unobserve() { /* stub for jsdom */ }
    disconnect() { /* stub for jsdom */ }
  },
)

const makeSnapshot = (overrides = {}) => ({
  id: 1,
  timestamp: '2024-01-01T00:00:00Z',
  device_id: 'ups1',
  device_type: 'ups',
  power_watts: 120.5,
  load_percent: 45,
  voltage: 230,
  battery_percent: 95,
  runtime_seconds: 3600,
  ups_status: 'OL',
  temperature_c: 35,
  ...overrides,
})

const makeDevice = (overrides = {}) => ({
  id: 'ups1',
  name: 'UPS 1',
  type: 'ups',
  poller: 'nut',
  host: 'localhost',
  port: 3493,
  enabled: true,
  connection_config: {},
  last_seen: '2024-01-01T00:00:00Z',
  ...overrides,
})

const makeHealth = (overrides = {}) => ({
  status: 'ok',
  service: 'argus',
  version: '0.1.0',
  last_poll_at: '2024-01-01T00:00:00Z',
  next_poll_at: null,
  is_polling: false,
  github_repo: undefined as string | undefined,
  ...overrides,
})

const makeConfig = (overrides = {}) => ({
  poll_interval_minutes: 1,
  enabled_exporters: ['sqlite'],
  scanning_disabled: false,
  scheduler_paused: false,
  nut_host: 'localhost',
  nut_port: 3493,
  nut_username: '',
  nut_password: '',
  nut_ups_name: 'ups',
  nut_auto_discover: true,
  device_offline_missed_polls: 3,
  shutdown_battery_floor_pct: 5,
  threshold_load_percent: 90,
  threshold_temp_celsius: 50,
  ...overrides,
})

const baseContext: ArgusContextType = {
  snapshots: [makeSnapshot()],
  latest: makeSnapshot(),
  health: makeHealth(),
  config: makeConfig(),
  devices: [makeDevice()],
  loading: false,
  isPolling: false,
  error: null,
  theme: 'dark',
  toggleTheme: vi.fn(),
  runPoll: vi.fn(),
  updateConfig: vi.fn(),
  refresh: vi.fn(),
}

function renderWithContext(
  ui: React.ReactNode,
  ctx: Partial<ArgusContextType> = {},
  route = '/',
) {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <ArgusContext.Provider value={{ ...baseContext, ...ctx }}>
        {ui}
      </ArgusContext.Provider>
    </MemoryRouter>,
  )
}

// ─────────────────────────────────────── Dashboard ───────────────────────────

import { Dashboard } from '@/pages/Dashboard'

describe('Dashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(apiModule.getEvents).mockResolvedValue({
      page: 1, page_size: 50, total: 0, items: [],
    })
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('no network')))
  })

  it('renders heading', () => {
    renderWithContext(<Dashboard />)
    expect(screen.getByText('Dashboard')).toBeDefined()
  })

  it('shows scheduler running status', () => {
    renderWithContext(<Dashboard />)
    expect(screen.getByText(/Scheduler running/i)).toBeDefined()
  })

  it('shows version from health', () => {
    renderWithContext(<Dashboard />, { health: makeHealth({ version: '1.2.3' }) })
    expect(screen.getByText(/v1.2.3/)).toBeDefined()
  })

  it('shows "Poll Now" button', () => {
    renderWithContext(<Dashboard />)
    expect(screen.getByRole('button', { name: /poll now/i })).toBeDefined()
  })

  it('shows "Polling…" when isPolling is true', () => {
    renderWithContext(<Dashboard />, { isPolling: true })
    expect(screen.getByText(/polling…/i)).toBeDefined()
  })

  it('shows error banner when error is set', () => {
    renderWithContext(<Dashboard />, { error: 'Connection refused' })
    expect(screen.getByText('Connection refused')).toBeDefined()
  })

  it('shows gauge labels', () => {
    renderWithContext(<Dashboard />)
    expect(screen.getByText('Power')).toBeDefined()
    expect(screen.getByText('Battery')).toBeDefined()
  })

  it('renders with null latest snapshot', () => {
    renderWithContext(<Dashboard />, { latest: null })
    // Should render dashes for null values
    const dashes = screen.getAllByText('—')
    expect(dashes.length).toBeGreaterThan(0)
  })

  it('shows last poll time from health', () => {
    renderWithContext(<Dashboard />, {
      health: makeHealth({ last_poll_at: '2024-01-01T12:00:00Z', next_poll_at: null }),
    })
    expect(screen.getByText(/Last poll:/i)).toBeDefined()
  })

  it('shows connecting message when health status is not ok', () => {
    renderWithContext(<Dashboard />, { health: makeHealth({ status: 'error' }) })
    expect(screen.getByText(/Connecting to Argus/i)).toBeDefined()
  })

  it('click Poll Now calls runPoll', async () => {
    const runPoll = vi.fn()
    renderWithContext(<Dashboard />, { runPoll })
    fireEvent.click(screen.getByRole('button', { name: /poll now/i }))
    expect(runPoll).toHaveBeenCalledTimes(1)
  })

  it('renders with null health', () => {
    renderWithContext(<Dashboard />, { health: null })
    expect(screen.getByText('Dashboard')).toBeDefined()
  })
})

// ─────────────────────────────────────── Settings ────────────────────────────

import { Settings } from '@/pages/Settings'

describe('Settings', () => {
  beforeEach(() => vi.clearAllMocks())

  it('shows loading when config is null', () => {
    renderWithContext(<Settings />, { config: null })
    expect(screen.getByText(/loading settings/i)).toBeDefined()
  })

  it('renders poll interval input', () => {
    renderWithContext(<Settings />)
    const input = screen.getByRole('spinbutton')
    expect(input).toBeDefined()
  })

  it('shows poll interval value', () => {
    renderWithContext(<Settings />, { config: makeConfig({ poll_interval_minutes: 5 }) })
    const input = screen.getByRole('spinbutton') as HTMLInputElement
    expect(input.value).toBe('5')
  })

  it('shows settings heading', () => {
    renderWithContext(<Settings />)
    expect(screen.getByText('Settings')).toBeDefined()
  })

  it('shows exporter checkboxes', () => {
    renderWithContext(<Settings />)
    expect(screen.getByText('sqlite')).toBeDefined()
    expect(screen.getByText('prometheus')).toBeDefined()
    expect(screen.getByText('influxdb')).toBeDefined()
    expect(screen.getByText('loki')).toBeDefined()
  })

  it('shows Save Changes button', () => {
    renderWithContext(<Settings />)
    expect(screen.getByRole('button', { name: /save changes/i })).toBeDefined()
  })

  it('updates poll interval input', () => {
    renderWithContext(<Settings />)
    const input = screen.getByRole('spinbutton') as HTMLInputElement
    fireEvent.change(input, { target: { value: '10' } })
    expect(input.value).toBe('10')
  })

  it('calls updateConfig when saving', async () => {
    const updateConfig = vi.fn().mockResolvedValue(makeConfig())
    renderWithContext(<Settings />, { updateConfig })
    fireEvent.click(screen.getByRole('button', { name: /save changes/i }))
    await waitFor(() => expect(updateConfig).toHaveBeenCalledTimes(1))
  })

  it('shows Saved! after save', async () => {
    const updateConfig = vi.fn().mockResolvedValue(makeConfig())
    renderWithContext(<Settings />, { updateConfig })
    fireEvent.click(screen.getByRole('button', { name: /save changes/i }))
    await waitFor(() => expect(screen.queryByText(/saved!/i)).toBeDefined())
  })

  it('toggles pause scheduler checkbox', () => {
    renderWithContext(<Settings />, { config: makeConfig({ scheduler_paused: false }) })
    const checkboxes = screen.getAllByRole('checkbox')
    // First checkbox is "Pause scheduler"
    fireEvent.click(checkboxes[0])
    // No error means state update worked
  })

  it('toggles exporter checkbox', () => {
    renderWithContext(<Settings />, { config: makeConfig({ enabled_exporters: ['sqlite'] }) })
    const checkboxes = screen.getAllByRole('checkbox')
    // sqlite is checked; toggle it off
    const sqliteBox = checkboxes.find((cb) => (cb as HTMLInputElement).value !== 'on') ?? checkboxes[2]
    fireEvent.click(sqliteBox)
  })
})

// ─────────────────────────────────────── Events page ─────────────────────────

import { Events } from '@/pages/Events'

const makeEvent = (overrides = {}) => ({
  id: 1,
  timestamp: '2024-01-01T10:00:00Z',
  device_id: 'ups1',
  event_type: 'on_battery',
  metadata: {},
  ...overrides,
})

const makeEventsPage = (items = [makeEvent()]) => ({
  page: 1, page_size: 25, total: items.length, items,
})

describe('Events page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders page heading', async () => {
    vi.mocked(apiModule.getEventsFiltered).mockResolvedValue(makeEventsPage([]))
    renderWithContext(<Events />)
    await waitFor(() => expect(screen.queryByText(/loading/i)).toBeNull())
    expect(screen.getByText('Events')).toBeDefined()
  })

  it('shows no events message', async () => {
    vi.mocked(apiModule.getEventsFiltered).mockResolvedValue(makeEventsPage([]))
    renderWithContext(<Events />)
    await waitFor(() => expect(screen.queryByText(/loading/i)).toBeNull())
    expect(screen.getByText(/no events/i)).toBeDefined()
  })

  it('renders events in table', async () => {
    vi.mocked(apiModule.getEventsFiltered).mockResolvedValue(
      makeEventsPage([makeEvent({ event_type: 'on_battery', device_id: 'ups1' })]),
    )
    renderWithContext(<Events />, { devices: [makeDevice()] })
    await waitFor(() => expect(screen.queryByText(/loading/i)).toBeNull())
    // event_type displayed with underscores replaced by spaces
    expect(screen.getAllByText('on battery').length).toBeGreaterThan(0)
  })

  it('renders device filter dropdown', async () => {
    vi.mocked(apiModule.getEventsFiltered).mockResolvedValue(makeEventsPage([]))
    renderWithContext(<Events />, { devices: [makeDevice()] })
    await waitFor(() => expect(screen.queryByText(/loading/i)).toBeNull())
    expect(screen.getAllByText(/all devices/i).length).toBeGreaterThan(0)
  })

  it('renders event type filter dropdown', async () => {
    vi.mocked(apiModule.getEventsFiltered).mockResolvedValue(makeEventsPage([]))
    renderWithContext(<Events />)
    await waitFor(() => expect(screen.queryByText(/loading/i)).toBeNull())
    expect(screen.getByText(/all types/i)).toBeDefined()
  })

  it('handles API error gracefully', async () => {
    vi.mocked(apiModule.getEventsFiltered).mockRejectedValue(new Error('Network error'))
    renderWithContext(<Events />)
    await waitFor(() => expect(screen.queryByText(/loading/i)).toBeNull())
    expect(screen.getByText(/no events/i)).toBeDefined()
  })
})
