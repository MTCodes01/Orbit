/**
 * Trackpad Page — the primary controller screen.
 *
 * Layout (portrait):
 *   ┌─────────────────────────────┐
 *   │  Device selector + status   │
 *   ├─────────────────────────────┤
 *   │                             │
 *   │     Trackpad surface        │
 *   │       (flex-grow)           │
 *   │                             │
 *   ├─────────────────────────────┤
 *   │  LEFT  │  MID  │   RIGHT    │
 *   ├─────────────────────────────┤
 *   │  Quick shortcuts            │
 *   └─────────────────────────────┘
 */

import { useRef, useCallback, useEffect, useState } from 'react'
import { useOrbit } from '../store/OrbitContext'
import { useTrackpad } from '../hooks/useTrackpad'

const SHORTCUTS = [
  { label: 'Ctrl+C', keys: ['ctrl', 'c'] },
  { label: 'Ctrl+V', keys: ['ctrl', 'v'] },
  { label: 'Ctrl+Z', keys: ['ctrl', 'z'] },
  { label: 'Alt+Tab', keys: ['alt', 'tab'] },
  { label: 'Win+Shift+➔', keys: ['meta', 'shift', 'arrowright'] },
  { label: 'Alt+F4', keys: ['alt', 'F4'] },
  { label: 'Win+D', keys: ['meta', 'd'] },
  { label: 'Win+L', keys: ['meta', 'l'] },
]

export default function TrackpadPage() {
  const { state, ws, setActiveDevice, sendInput } = useOrbit()
  const { devices, activeDeviceId, connectionState, settings } = state
  const trackpadRef = useRef<HTMLDivElement>(null)
  const [isActive, setIsActive] = useState(false)
  const [leftPressed, setLeftPressed] = useState(false)
  const [rightPressed, setRightPressed] = useState(false)
  const [midPressed, setMidPressed] = useState(false)

  const activeDevice = devices.find(d => d.device_id === activeDeviceId)
  const isConnected = connectionState === 'connected'
  const hasTarget = !!activeDeviceId && activeDevice?.online

  const sendMouse = useCallback((type: string, button: string) => {
    if (!activeDeviceId) return
    sendInput({ type, protocol_version: '1.0.0', target_device_id: activeDeviceId, button, timestamp_ms: Date.now() })
  }, [activeDeviceId, sendInput])

  const trackpadCallbacks = {
    onPointerMove: useCallback((dx: number, dy: number) => {
      if (!activeDeviceId || !ws) return
      ws.sendPointerMove(activeDeviceId, dx, dy)
    }, [activeDeviceId, ws]),

    onMouseDown: useCallback((button: 'left' | 'right' | 'middle') => {
      sendMouse('mouse_down', button)
    }, [sendMouse]),

    onMouseUp: useCallback((button: 'left' | 'right' | 'middle') => {
      sendMouse('mouse_up', button)
    }, [sendMouse]),

    onScroll: useCallback((dx: number, dy: number) => {
      if (!activeDeviceId) return
      const naturalDy = settings.scrollNatural ? -dy : dy
      sendInput({ type: 'scroll', protocol_version: '1.0.0', target_device_id: activeDeviceId, dx, dy: naturalDy, timestamp_ms: Date.now() })
    }, [activeDeviceId, sendInput, settings.scrollNatural]),
  }

  const handlers = useTrackpad(trackpadCallbacks, settings.sensitivity, settings.acceleration)

  // Attach pointer events to the trackpad surface
  useEffect(() => {
    const el = trackpadRef.current
    if (!el) return

    const opts = { passive: false }

    const down = (e: PointerEvent) => {
      if (!hasTarget) return
      el.setPointerCapture(e.pointerId)
      setIsActive(true)
      handlers.onPointerDown(e)
    }
    const move = (e: PointerEvent) => { if (hasTarget) handlers.onPointerMove(e) }
    const up = (e: PointerEvent) => {
      handlers.onPointerUp(e)
      setIsActive(false)
    }
    const cancel = (e: PointerEvent) => {
      handlers.onPointerCancel(e)
      setIsActive(false)
    }
    const ctx = (e: Event) => { if (hasTarget) handlers.onContextMenu(e) }

    el.addEventListener('pointerdown', down, opts)
    el.addEventListener('pointermove', move, opts)
    el.addEventListener('pointerup', up, opts)
    el.addEventListener('pointercancel', cancel, opts)
    el.addEventListener('contextmenu', ctx, opts)

    return () => {
      el.removeEventListener('pointerdown', down)
      el.removeEventListener('pointermove', move)
      el.removeEventListener('pointerup', up)
      el.removeEventListener('pointercancel', cancel)
      el.removeEventListener('contextmenu', ctx)
    }
  }, [handlers, hasTarget])

  // Release held buttons on device deselect or disconnect
  useEffect(() => {
    return () => {
      if (activeDeviceId) {
        sendInput({ type: 'mouse_up', protocol_version: '1.0.0', target_device_id: activeDeviceId, button: 'left' })
        sendInput({ type: 'mouse_up', protocol_version: '1.0.0', target_device_id: activeDeviceId, button: 'right' })
        sendInput({ type: 'mouse_up', protocol_version: '1.0.0', target_device_id: activeDeviceId, button: 'middle' })
      }
    }
  }, [activeDeviceId, sendInput])

  const sendShortcut = (keys: string[]) => {
    if (!activeDeviceId) return
    sendInput({ type: 'shortcut', protocol_version: '1.0.0', target_device_id: activeDeviceId, keys, timestamp_ms: Date.now() })
  }

  const handleSwitchMonitor = (monitorIndex: number) => {
    if (!activeDeviceId) return
    sendInput({
      type: 'switch_monitor',
      protocol_version: '1.0.0',
      target_device_id: activeDeviceId,
      monitor_index: monitorIndex,
      timestamp_ms: Date.now(),
    })
  }

  const monitors = activeDevice?.capabilities?.monitors || []

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', padding: '12px 12px 8px', gap: 10 }}>
      {/* Device selector */}
      <div style={{ display: 'flex', gap: 8, overflowX: 'auto', paddingBottom: 4, flexShrink: 0 }}>
        {devices.length === 0 ? (
          <div style={{ color: 'var(--text-muted)', fontSize: 13, padding: '8px 0' }}>
            No devices — pair a laptop first
          </div>
        ) : (
          devices.map(d => (
            <button
              key={d.device_id}
              className={`device-chip${d.online ? ' online' : ''}${activeDeviceId === d.device_id ? ' active' : ''}`}
              onClick={() => setActiveDevice(activeDeviceId === d.device_id ? null : d.device_id)}
            >
              <span className="online-dot" />
              {d.friendly_name}
            </button>
          ))
        )}
      </div>

      {/* Multi-display switcher if multiple monitors detected */}
      {monitors.length > 1 && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0, background: 'rgba(255,255,255,0.03)', padding: '6px 10px', borderRadius: 8, border: '1px solid var(--border-subtle)' }}>
          <span style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600 }}>DISPLAYS:</span>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {monitors.map((mon, idx) => (
              <button
                key={mon.index}
                className="btn btn-sm"
                style={{
                  fontSize: 11,
                  padding: '4px 8px',
                  borderRadius: 6,
                  background: 'var(--bg-elevated)',
                  border: '1px solid var(--border-default)',
                  color: 'var(--text-primary)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 4,
                  cursor: 'pointer',
                }}
                onClick={() => handleSwitchMonitor(mon.index)}
                title={`Jump cursor to Display ${idx + 1} (${mon.width}×${mon.height})`}
              >
                🖥️ Display {idx + 1} {mon.is_primary ? '(Main)' : ''}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Status strip */}
      {activeDevice && (
        <div style={{ fontSize: 11, color: 'var(--text-muted)', display: 'flex', justifyContent: 'space-between' }}>
          <span>
            {activeDevice.hostname} · {monitors.length > 1 ? `${monitors.length} Displays` : `${activeDevice.screen_width}×${activeDevice.screen_height}`}
          </span>
          <span style={{ color: activeDevice.online ? 'var(--success)' : 'var(--danger)' }}>
            {activeDevice.online ? '● Online' : '○ Offline'}
          </span>
        </div>
      )}

      {/* Trackpad surface */}
      <div
        ref={trackpadRef}
        className={`trackpad-surface${isActive ? ' active' : ''}`}
        style={{ flex: 1, minHeight: 200 }}
        aria-label="Trackpad"
        role="application"
      >
        <div className="trackpad-hint">
          {!isConnected
            ? '⚡ Not connected to backend'
            : !activeDeviceId
            ? '← Select a device above'
            : !activeDevice?.online
            ? '⊘ Device is offline'
            : 'Touch to control'}
        </div>
      </div>

      {/* Mouse buttons */}
      <div className="mouse-buttons" style={{ flexShrink: 0 }}>
        <button
          className={`mouse-btn${leftPressed ? ' pressed' : ''}`}
          onPointerDown={() => { setLeftPressed(true); sendMouse('mouse_down', 'left') }}
          onPointerUp={() => { setLeftPressed(false); sendMouse('mouse_up', 'left') }}
          onPointerLeave={() => { if (leftPressed) { setLeftPressed(false); sendMouse('mouse_up', 'left') } }}
        >
          ◀ Left
        </button>
        <button
          className={`mouse-btn-mid${midPressed ? ' pressed' : ''}`}
          onPointerDown={() => { setMidPressed(true); sendMouse('mouse_down', 'middle') }}
          onPointerUp={() => { setMidPressed(false); sendMouse('mouse_up', 'middle') }}
          onPointerLeave={() => { if (midPressed) { setMidPressed(false); sendMouse('mouse_up', 'middle') } }}
        >
          ●
        </button>
        <button
          className={`mouse-btn${rightPressed ? ' pressed' : ''}`}
          onPointerDown={() => { setRightPressed(true); sendMouse('mouse_down', 'right') }}
          onPointerUp={() => { setRightPressed(false); sendMouse('mouse_up', 'right') }}
          onPointerLeave={() => { if (rightPressed) { setRightPressed(false); sendMouse('mouse_up', 'right') } }}
        >
          Right ▶
        </button>
      </div>

      {/* Quick shortcuts */}
      <div style={{ flexShrink: 0 }}>
        <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.8px', marginBottom: 6 }}>
          Shortcuts
        </div>
        <div className="shortcut-grid">
          {SHORTCUTS.map(s => (
            <button key={s.label} className="shortcut-btn" onPointerDown={() => sendShortcut(s.keys)}>
              {s.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
