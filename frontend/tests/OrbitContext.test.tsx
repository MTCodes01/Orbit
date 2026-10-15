import { render, screen, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { OrbitProvider, useOrbit } from '../src/store/OrbitContext'

// Test consumer component
function TestConsumer() {
  const { state, setActiveDevice, updateSettings } = useOrbit()

  return (
    <div>
      <span data-testid="connection-state">{state.connectionState}</span>
      <span data-testid="active-device">{state.activeDeviceId || 'none'}</span>
      <span data-testid="sensitivity">{state.settings.sensitivity}</span>
      <button onClick={() => setActiveDevice('laptop-1')}>Set Laptop 1</button>
      <button onClick={() => updateSettings({ sensitivity: 2.0 })}>Set Sensitivity</button>
    </div>
  )
}

describe('OrbitContext', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
  })

  it('provides default state to consumer and attempts connection', () => {
    render(
      <OrbitProvider>
        <TestConsumer />
      </OrbitProvider>
    )

    // On mount, OrbitWebSocket initiates connection
    expect(['disconnected', 'connecting']).toContain(
      screen.getByTestId('connection-state').textContent
    )
    expect(screen.getByTestId('active-device').textContent).toBe('none')
    expect(screen.getByTestId('sensitivity').textContent).toBe('1.2')
  })

  it('updates active device when setActiveDevice is invoked', () => {
    render(
      <OrbitProvider>
        <TestConsumer />
      </OrbitProvider>
    )

    act(() => {
      screen.getByText('Set Laptop 1').click()
    })

    expect(screen.getByTestId('active-device').textContent).toBe('laptop-1')
  })

  it('updates settings and persists to localStorage', () => {
    render(
      <OrbitProvider>
        <TestConsumer />
      </OrbitProvider>
    )

    act(() => {
      screen.getByText('Set Sensitivity').click()
    })

    expect(screen.getByTestId('sensitivity').textContent).toBe('2')
    const saved = JSON.parse(localStorage.getItem('orbit-settings') || '{}')
    expect(saved.sensitivity).toBe(2.0)
  })
})
