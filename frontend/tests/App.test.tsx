import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { BrowserRouter } from 'react-router-dom'
import App from '../src/App'

describe('Orbit App Component', () => {
  it('renders trackpad view by default with bottom navigation', () => {
    render(
      <BrowserRouter>
        <App />
      </BrowserRouter>
    )

    // Check brand in AppShell
    expect(screen.getByText('Orbit')).toBeDefined()

    // Check bottom navigation items
    expect(screen.getByText('Trackpad')).toBeDefined()
    expect(screen.getByText('Keys')).toBeDefined()
    expect(screen.getByText('Devices')).toBeDefined()
    expect(screen.getByText('Layout')).toBeDefined()
    expect(screen.getByText('Settings')).toBeDefined()
  })
})
