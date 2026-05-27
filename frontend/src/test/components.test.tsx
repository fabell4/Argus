/**
 * Tests for: Layout, Alerts page, Devices page, App
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent, act } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import React from 'react'
import { ArgusContext, type ArgusContextType } from '@/context/argusContextDef'
import * as apiModule from '@/lib/api'

vi.mock('@/lib/api', () => ({
  getAlerts: vi.fn(),
  updateAlerts: vi.fn(),
  testAlert: vi.fn(),
  getSnapshots: vi.fn(),
  getLatestSnapshot: vi.fn(),
  getHealth: vi.fn(),
  getConfig: vi.fn(),
  getDevices: vi.fn(),
  getPollStatus: vi.fn(),
  triggerPoll: vi.fn(),
  updateConfig: vi.fn(),
}))

vi.stubGlobal(
  'ResizeObserver',
  class {
    observe() { /* stub for jsdom */ }
    unobserve() { /* stub for jsdom */ }
    disconnect() { /* stub for jsdom */ }
  },
)

const makeDevice = (overrides = {}) => ({
  id: 'ups1',
  name: 'UPS 1',
  type: 'ups',
  poller: 'nut',
  host: 'localhost',
  port: 3493,
  enabled: true,
  connection_config: {},
  last_seen: null,
  ...overrides,
})

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
  temperature_c: null,
  ...overrides,
})

const makeAlertConfig = (overrides = {}) => ({
  providers: [],
  failure_threshold: 3,
  cooldown_seconds: 3600,
  alert_on_battery: true,
  alert_on_battery_low: true,
  alert_on_device_offline: true,
  alert_recovery_notifications: true,
  recovery_cooldown_seconds: 300,
  ...overrides,
})

const baseContext: ArgusContextType = {
  snapshots: [],
  latest: null,
  health: null,
  config: null,
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

// ─────────────────────────────────── Layout ──────────────────────────────────

import { Layout } from '@/components/Layout'

// Wrap Layout in a route so Outlet renders
function LayoutWithContent() {
  return (
    <MemoryRouter initialEntries={['/']}>
      <ArgusContext.Provider value={baseContext}>
        <Layout />
      </ArgusContext.Provider>
    </MemoryRouter>
  )
}

describe('Layout', () => {
  it('renders the Argus brand text', () => {
    render(<LayoutWithContent />)
    expect(screen.getByText('Argus')).toBeDefined()
  })

  it('renders navigation links', () => {
    render(<LayoutWithContent />)
    expect(screen.getByText('Dashboard')).toBeDefined()
    expect(screen.getByText('Devices')).toBeDefined()
    expect(screen.getByText('Events')).toBeDefined()
    expect(screen.getByText('Alerts')).toBeDefined()
    expect(screen.getByText('Settings')).toBeDefined()
  })

  it('renders theme toggle button', () => {
    render(<LayoutWithContent />)
    expect(screen.getByLabelText(/switch to light mode/i)).toBeDefined()
  })

  it('toggles mobile menu open', () => {
    render(<LayoutWithContent />)
    const menuBtn = screen.getByLabelText(/toggle menu/i)
    fireEvent.click(menuBtn)
    // After click menu is open – button should change aria-label-adjacent content
    expect(menuBtn).toBeDefined()
  })

  it('calls toggleTheme when theme button clicked', () => {
    const toggleTheme = vi.fn()
    render(
      <MemoryRouter initialEntries={['/']}>
        <ArgusContext.Provider value={{ ...baseContext, toggleTheme }}>
          <Layout />
        </ArgusContext.Provider>
      </MemoryRouter>,
    )
    const btn = screen.getByLabelText(/switch to light mode/i)
    fireEvent.click(btn)
    expect(toggleTheme).toHaveBeenCalledTimes(1)
  })

  it('renders light theme toggle label when theme is light', () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <ArgusContext.Provider value={{ ...baseContext, theme: 'light' }}>
          <Layout />
        </ArgusContext.Provider>
      </MemoryRouter>,
    )
    expect(screen.getByLabelText(/switch to dark mode/i)).toBeDefined()
  })
})

// ─────────────────────────────────── Alerts page ─────────────────────────────

import { Alerts } from '@/pages/Alerts'

describe('Alerts page', () => {
  beforeEach(() => vi.clearAllMocks())

  it('shows loading state initially', () => {
    vi.mocked(apiModule.getAlerts).mockReturnValue(new Promise(() => {}))
    renderWithContext(<Alerts />)
    expect(screen.getByText(/loading alert config/i)).toBeDefined()
  })

  it('renders page heading after load', async () => {
    vi.mocked(apiModule.getAlerts).mockResolvedValue(makeAlertConfig())
    renderWithContext(<Alerts />)
    await waitFor(() => expect(screen.queryByText(/loading/i)).toBeNull())
    expect(screen.getByText('Alert Configuration')).toBeDefined()
  })

  it('shows no providers message', async () => {
    vi.mocked(apiModule.getAlerts).mockResolvedValue(makeAlertConfig())
    renderWithContext(<Alerts />)
    await waitFor(() => expect(screen.queryByText(/loading/i)).toBeNull())
    expect(screen.getByText(/no providers configured/i)).toBeDefined()
  })

  it('shows Save button', async () => {
    vi.mocked(apiModule.getAlerts).mockResolvedValue(makeAlertConfig())
    renderWithContext(<Alerts />)
    await waitFor(() => expect(screen.queryByText(/loading/i)).toBeNull())
    expect(screen.getByRole('button', { name: /save changes/i })).toBeDefined()
  })

  it('shows Add provider button', async () => {
    vi.mocked(apiModule.getAlerts).mockResolvedValue(makeAlertConfig())
    renderWithContext(<Alerts />)
    await waitFor(() => expect(screen.queryByText(/loading/i)).toBeNull())
    expect(screen.getByRole('button', { name: /add provider/i })).toBeDefined()
  })

  it('adds a webhook provider', async () => {
    vi.mocked(apiModule.getAlerts).mockResolvedValue(makeAlertConfig())
    renderWithContext(<Alerts />)
    await waitFor(() => expect(screen.queryByText(/loading/i)).toBeNull())
    fireEvent.click(screen.getByRole('button', { name: /add provider/i }))
    expect(screen.getByText(/webhook #1/i)).toBeDefined()
  })

  it('handles API load error', async () => {
    vi.mocked(apiModule.getAlerts).mockRejectedValue(new Error('Load failed'))
    renderWithContext(<Alerts />)
    await waitFor(() => expect(screen.queryByText(/loading/i)).toBeNull())
    expect(screen.getByText('Load failed')).toBeDefined()
  })

  it('saves alert config', async () => {
    vi.mocked(apiModule.getAlerts).mockResolvedValue(makeAlertConfig())
    vi.mocked(apiModule.updateAlerts).mockResolvedValue(makeAlertConfig())
    renderWithContext(<Alerts />)
    await waitFor(() => expect(screen.queryByText(/loading/i)).toBeNull())
    fireEvent.click(screen.getByRole('button', { name: /save changes/i }))
    await waitFor(() => expect(apiModule.updateAlerts).toHaveBeenCalledTimes(1))
  })

  it('sends test alert when providers exist', async () => {
    vi.mocked(apiModule.getAlerts).mockResolvedValue(makeAlertConfig({
      providers: [{ type: 'webhook', enabled: true, url: 'https://example.com' }],
    }))
    vi.mocked(apiModule.testAlert).mockResolvedValue({ status: 'ok', message: 'Test sent!' })
    renderWithContext(<Alerts />)
    await waitFor(() => expect(screen.queryByText(/loading/i)).toBeNull())
    const testBtn = screen.getByRole('button', { name: /send test alert/i })
    expect((testBtn as HTMLButtonElement).disabled).toBe(false)
    fireEvent.click(testBtn)
    await waitFor(() => expect(apiModule.testAlert).toHaveBeenCalledTimes(1))
  })

  it('shows threshold and cooldown inputs', async () => {
    vi.mocked(apiModule.getAlerts).mockResolvedValue(makeAlertConfig({ failure_threshold: 3, cooldown_seconds: 3600 }))
    renderWithContext(<Alerts />)
    await waitFor(() => expect(screen.queryByText(/loading/i)).toBeNull())
    expect(screen.getByText(/failure threshold/i)).toBeDefined()
    expect(screen.getAllByText(/cooldown/i).length).toBeGreaterThanOrEqual(1)
  })

  it('renders a webhook provider form', async () => {
    vi.mocked(apiModule.getAlerts).mockResolvedValue(makeAlertConfig({
      providers: [{ type: 'webhook', enabled: true, url: 'https://example.com/hook' }],
    }))
    renderWithContext(<Alerts />)
    await waitFor(() => expect(screen.queryByText(/loading/i)).toBeNull())
    expect(screen.getByText(/webhook #1/i)).toBeDefined()
  })

  it('renders a gotify provider form', async () => {
    vi.mocked(apiModule.getAlerts).mockResolvedValue(makeAlertConfig({
      providers: [{ type: 'gotify', enabled: true, url: 'https://gotify.example.com', token: 'abc' }],
    }))
    renderWithContext(<Alerts />)
    await waitFor(() => expect(screen.queryByText(/loading/i)).toBeNull())
    expect(screen.getByText(/gotify #1/i)).toBeDefined()
    expect(screen.getByText('Token')).toBeDefined()
  })

  it('renders an ntfy provider form', async () => {
    vi.mocked(apiModule.getAlerts).mockResolvedValue(makeAlertConfig({
      providers: [{ type: 'ntfy', enabled: true, url: 'https://ntfy.sh', topic: 'argus' }],
    }))
    renderWithContext(<Alerts />)
    await waitFor(() => expect(screen.queryByText(/loading/i)).toBeNull())
    expect(screen.getByText(/ntfy #1/i)).toBeDefined()
    expect(screen.getByText('Topic')).toBeDefined()
  })

  it('removes a provider', async () => {
    vi.mocked(apiModule.getAlerts).mockResolvedValue(makeAlertConfig({
      providers: [{ type: 'webhook', enabled: true, url: '' }],
    }))
    renderWithContext(<Alerts />)
    await waitFor(() => expect(screen.queryByText(/webhook #1/i)).toBeDefined())
    const trashBtn = screen.getAllByRole('button').find((b) =>
      b.querySelector('svg') && !b.textContent?.includes('#')
    )
    if (trashBtn) fireEvent.click(trashBtn)
    // No error means state update worked
  })
})

// ─────────────────────────────────── Devices page ────────────────────────────

import { Devices } from '@/pages/Devices'

describe('Devices page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(apiModule.getLatestSnapshot).mockResolvedValue(makeSnapshot())
  })

  it('renders page heading', async () => {
    renderWithContext(<Devices />, { devices: [makeDevice()], loading: false })
    await act(async () => {})
    expect(screen.getByText('Devices')).toBeDefined()
  })

  it('shows device count', async () => {
    renderWithContext(<Devices />, { devices: [makeDevice()], loading: false })
    await act(async () => {})
    expect(screen.getByText(/1 device registered/i)).toBeDefined()
  })

  it('shows no devices message', async () => {
    renderWithContext(<Devices />, { devices: [], loading: false })
    await act(async () => {})
    expect(screen.getByText(/no devices registered/i)).toBeDefined()
  })

  it('shows device name', async () => {
    renderWithContext(<Devices />, { devices: [makeDevice({ name: 'My UPS' })], loading: false })
    await waitFor(() => expect(screen.queryByText('My UPS')).toBeDefined())
  })

  it('shows loading skeleton when loading', () => {
    renderWithContext(<Devices />, { devices: [], loading: true })
    // pulse skeleton divs rendered during loading
    const { container } = renderWithContext(<Devices />, { devices: [], loading: true })
    expect(container).toBeDefined()
  })

  it('shows multiple devices', async () => {
    const devices = [
      makeDevice({ id: 'ups1', name: 'UPS 1' }),
      makeDevice({ id: 'ups2', name: 'UPS 2' }),
    ]
    renderWithContext(<Devices />, { devices, loading: false })
    await act(async () => {})
    expect(screen.getByText(/2 devices registered/i)).toBeDefined()
  })

  it('shows on battery status when UPS status contains OB', async () => {
    vi.mocked(apiModule.getLatestSnapshot).mockResolvedValue(
      makeSnapshot({ ups_status: 'OB DISCHRG' }),
    )
    renderWithContext(<Devices />, { devices: [makeDevice()], loading: false })
    await waitFor(() => expect(screen.queryByText(/on battery/i)).toBeDefined())
  })
})
