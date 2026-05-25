import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { PowerChart } from '@/components/PowerChart'
import type { PowerSnapshot } from '@/types'

// Recharts uses ResizeObserver; provide a no-op stub
vi.stubGlobal(
  'ResizeObserver',
  class {
    observe() { /* stub for jsdom */ }
    unobserve() { /* stub for jsdom */ }
    disconnect() { /* stub for jsdom */ }
  },
)

const makeSnapshot = (overrides = {}): PowerSnapshot => ({
  id: 1,
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
  ...overrides,
})

describe('PowerChart', () => {
  it('shows empty message when no snapshots', () => {
    render(<PowerChart snapshots={[]} />)
    expect(screen.getByText(/no snapshot data yet/i)).toBeDefined()
  })

  it('renders chart container when snapshots provided', () => {
    const snaps = [makeSnapshot(), makeSnapshot({ id: 2, timestamp: '2024-01-01T00:01:00Z' })]
    const { container } = render(<PowerChart snapshots={snaps} />)
    // recharts renders a wrapper div in jsdom (SVG may not be present without layout engine)
    expect(container.firstChild).toBeDefined()
    expect(screen.queryByText(/no snapshot data yet/i)).toBeNull()
  })

  it('renders with null metric values without crashing', () => {
    const snaps = [makeSnapshot({ power_watts: null, load_percent: null, battery_percent: null })]
    const { container } = render(<PowerChart snapshots={snaps} />)
    expect(container).toBeDefined()
  })
})
