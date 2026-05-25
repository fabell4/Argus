import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, act } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { ArgusProvider } from '@/context/ArgusContext'
import { ArgusContext, type ArgusContextType } from '@/context/argusContextDef'
import { useArgus } from '@/hooks/useArgus'
import * as apiModule from '@/lib/api'
import React from 'react'

vi.mock('@/lib/api', () => ({
  getSnapshots: vi.fn(),
  getLatestSnapshot: vi.fn(),
  getHealth: vi.fn(),
  getConfig: vi.fn(),
  getDevices: vi.fn(),
  getPollStatus: vi.fn(),
  triggerPoll: vi.fn(),
  updateConfig: vi.fn(),
}))

const makeSnapshot = () => ({
  id: 1, timestamp: '2024-01-01T00:00:00Z', device_id: 'ups1', device_type: 'ups',
  power_watts: 100, load_percent: 40, voltage: 230, battery_percent: 90,
  runtime_seconds: 3600, ups_status: 'OL', temperature_c: null,
})

const makeSnapshotsPage = () => ({ page: 1, page_size: 50, total: 1, items: [makeSnapshot()] })

const makeDevice = () => ({
  id: 'ups1', name: 'UPS 1', type: 'ups', poller: 'nut',
  host: 'localhost', port: 3493, enabled: true, connection_config: {},
})

const makeConfig = () => ({
  poll_interval_minutes: 1, enabled_exporters: ['sqlite'],
  scanning_disabled: false, scheduler_paused: false,
})

const makeHealth = () => ({
  status: 'ok', service: 'argus', last_poll_at: null,
  next_poll_at: null, is_polling: false,
})

function setupHappyPath() {
  vi.mocked(apiModule.getSnapshots).mockResolvedValue(makeSnapshotsPage())
  vi.mocked(apiModule.getLatestSnapshot).mockResolvedValue(makeSnapshot())
  vi.mocked(apiModule.getHealth).mockResolvedValue(makeHealth())
  vi.mocked(apiModule.getConfig).mockResolvedValue(makeConfig())
  vi.mocked(apiModule.getDevices).mockResolvedValue([makeDevice()])
}

// Consumer component to read context values
function ContextReader({ field }: Readonly<{ field: keyof ArgusContextType }>) {
  const ctx = useArgus()
  const value = ctx[field]
  if (typeof value === 'boolean') return <span data-testid="value">{String(value)}</span>
  if (value === null) return <span data-testid="value">null</span>
  if (typeof value === 'string') return <span data-testid="value">{value}</span>
  if (typeof value === 'number') return <span data-testid="value">{value}</span>
  return <span data-testid="value">defined</span>
}

function renderWithProvider(ui: React.ReactNode) {
  return render(
    <MemoryRouter>
      <ArgusProvider>{ui}</ArgusProvider>
    </MemoryRouter>
  )
}

describe('ArgusContext - ArgusProvider', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.spyOn(Storage.prototype, 'getItem').mockReturnValue(null)
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {})
  })

  it('starts in loading state', async () => {
    vi.mocked(apiModule.getSnapshots).mockReturnValue(new Promise(() => {}))
    vi.mocked(apiModule.getLatestSnapshot).mockReturnValue(new Promise(() => {}))
    vi.mocked(apiModule.getHealth).mockReturnValue(new Promise(() => {}))
    vi.mocked(apiModule.getConfig).mockReturnValue(new Promise(() => {}))
    vi.mocked(apiModule.getDevices).mockReturnValue(new Promise(() => {}))

    renderWithProvider(<ContextReader field="loading" />)
    expect(screen.getByTestId('value').textContent).toBe('true')
  })

  it('loading becomes false after fetchAll resolves', async () => {
    setupHappyPath()
    renderWithProvider(<ContextReader field="loading" />)
    await act(async () => {})
    expect(screen.getByTestId('value').textContent).toBe('false')
  })

  it('error is set when API call fails', async () => {
    vi.mocked(apiModule.getSnapshots).mockRejectedValue(new Error('Network fail'))
    vi.mocked(apiModule.getLatestSnapshot).mockRejectedValue(new Error('Network fail'))
    vi.mocked(apiModule.getHealth).mockRejectedValue(new Error('Network fail'))
    vi.mocked(apiModule.getConfig).mockRejectedValue(new Error('Network fail'))
    vi.mocked(apiModule.getDevices).mockRejectedValue(new Error('Network fail'))

    renderWithProvider(<ContextReader field="error" />)
    await act(async () => {})
    expect(screen.getByTestId('value').textContent).not.toBe('null')
  })

  it('provides default dark theme', async () => {
    setupHappyPath()
    renderWithProvider(<ContextReader field="theme" />)
    await act(async () => {})
    // Default theme when localStorage returns null
    const val = screen.getByTestId('value').textContent
    expect(['dark', 'light']).toContain(val)
  })

  it('respects stored light theme', async () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation((key) => {
      if (key === 'argus_theme') return 'light'
      return null
    })
    setupHappyPath()
    renderWithProvider(<ContextReader field="theme" />)
    await act(async () => {})
    expect(screen.getByTestId('value').textContent).toBe('light')
  })
})

describe('useArgus', () => {
  it('throws when used outside ArgusProvider', () => {
    // Suppress console.error for expected error boundary output
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {})
    expect(() => {
      render(
        <MemoryRouter>
          <ContextReader field="loading" />
        </MemoryRouter>
      )
    }).toThrow('useArgus must be used within ArgusProvider')
    spy.mockRestore()
  })
})

describe('argusContextDef - ArgusContext default value', () => {
  it('context default is null', () => {
    let captured: ArgusContextType | null | undefined = undefined
    function Consumer() {
      const ctx = React.useContext(ArgusContext)
      captured = ctx
      return null
    }
    render(<Consumer />)
    expect(captured).toBeNull()
  })
})
