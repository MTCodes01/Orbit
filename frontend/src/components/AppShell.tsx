import { Outlet, NavLink } from 'react-router-dom'
import { useOrbit } from '../store/OrbitContext'

// SVG icons (inline for zero dependency)
const IconTrackpad = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
    <rect x="2" y="4" width="20" height="16" rx="3"/>
    <line x1="2" y1="15" x2="22" y2="15"/>
  </svg>
)
const IconDevices = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
    <rect x="2" y="3" width="20" height="13" rx="2"/>
    <path d="M8 21h8M12 17v4"/>
  </svg>
)
const IconLayout = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="3" width="7" height="9" rx="1"/>
    <rect x="14" y="3" width="7" height="5" rx="1"/>
    <rect x="14" y="12" width="7" height="9" rx="1"/>
    <rect x="3" y="16" width="7" height="5" rx="1"/>
  </svg>
)
const IconKeyboard = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
    <rect x="2" y="6" width="20" height="12" rx="2"/>
    <path d="M6 10h.01M10 10h.01M14 10h.01M18 10h.01M8 14h8"/>
  </svg>
)
const IconSettings = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="3"/>
    <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z"/>
  </svg>
)

export default function AppShell() {
  const { state } = useOrbit()
  const { connectionState, latencyMs } = state

  const latencyClass =
    latencyMs === 0 ? '' :
    latencyMs < 30 ? 'good' :
    latencyMs < 80 ? 'ok' : 'bad'

  return (
    <div className="app-shell">
      {/* Top bar */}
      <header className="nav-bar">
        <div className="nav-logo">
          <span className="logo-dot" />
          Orbit
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {latencyMs > 0 && (
            <span className={`latency ${latencyClass}`}>{latencyMs}ms</span>
          )}
          <div className="status-badge">
            <span className={`status-dot ${connectionState}`} />
            {connectionState === 'connected' ? 'Live' :
             connectionState === 'connecting' ? 'Connecting' :
             connectionState === 'error' ? 'Error' : 'Offline'}
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="page fade-in">
        <Outlet />
      </main>

      {/* Bottom navigation */}
      <nav className="tab-bar">
        {[
          { to: '/trackpad', icon: <IconTrackpad />, label: 'Trackpad' },
          { to: '/keyboard', icon: <IconKeyboard />, label: 'Keys' },
          { to: '/devices', icon: <IconDevices />, label: 'Devices' },
          { to: '/layout', icon: <IconLayout />, label: 'Layout' },
          { to: '/settings', icon: <IconSettings />, label: 'Settings' },
        ].map(({ to, icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) => `tab-item${isActive ? ' active' : ''}`}
          >
            {icon}
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>
    </div>
  )
}
