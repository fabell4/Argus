import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { PowerGauge } from '@/components/PowerGauge'

describe('PowerGauge', () => {
  it('renders the label', () => {
    render(<PowerGauge label="Power" value={120.5} unit="W" metric="power" />)
    expect(screen.getByText('Power')).toBeDefined()
  })

  it('renders numeric value with unit', () => {
    render(<PowerGauge label="Battery" value={85.3} unit="%" metric="battery" />)
    expect(screen.getByText('85.3')).toBeDefined()
    expect(screen.getByText('%')).toBeDefined()
  })

  it('renders dash when value is null', () => {
    render(<PowerGauge label="Load" value={null} unit="%" metric="load" />)
    expect(screen.getByText('—')).toBeDefined()
  })

  it('renders temperature metric without error', () => {
    render(<PowerGauge label="Temp" value={42} unit="°C" metric="temperature" />)
    expect(screen.getByText('Temp')).toBeDefined()
    expect(screen.getByText('42.0')).toBeDefined()
  })

  it('formats value to 1 decimal place', () => {
    render(<PowerGauge label="Power" value={100} unit="W" metric="power" />)
    expect(screen.getByText('100.0')).toBeDefined()
  })

  it('renders load metric', () => {
    render(<PowerGauge label="Load" value={60} unit="%" metric="load" />)
    expect(screen.getByText('60.0')).toBeDefined()
  })
})
