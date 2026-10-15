import { useState } from 'react'
import { useOrbit } from '../store/OrbitContext'

export default function SettingsPage() {
  const { state, updateSettings } = useOrbit()
  const { settings, connectionState, latencyMs } = state

  const [backendUrl, setBackendUrl] = useState(settings.backendUrl)

  const handleUrlSave = () => {
    updateSettings({ backendUrl })
  }

  return (
    <div style={{ padding: '16px 12px', display: 'flex', flexDirection: 'column', gap: 20, overflowY: 'auto' }}>
      <h1 style={{ fontSize: 20, fontWeight: 700 }}>Settings</h1>

      {/* Connection */}
      <div className="card">
        <div className="card-header">Connection</div>
        <div className="settings-row">
          <div>
            <div className="settings-label">Backend URL</div>
            <div className="settings-desc">WebSocket URL of the Orbit coordinator</div>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
          <input
            className="input-field"
            value={backendUrl}
            onChange={e => setBackendUrl(e.target.value)}
            placeholder="ws://192.168.1.x:8000/ws/controller"
            id="backend-url-input"
          />
          <button className="btn btn-primary" onClick={handleUrlSave} id="save-url-btn">
            Save
          </button>
        </div>
        <div style={{ marginTop: 10, display: 'flex', gap: 16 }}>
          <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
            Status: <span style={{ color: connectionState === 'connected' ? 'var(--success)' : 'var(--danger)' }}>
              {connectionState}
            </span>
          </div>
          {latencyMs > 0 && (
            <div style={{ fontSize: 12, fontFamily: 'var(--font-mono)', color: latencyMs < 30 ? 'var(--success)' : latencyMs < 80 ? 'var(--warning)' : 'var(--danger)' }}>
              RTT: {latencyMs}ms
            </div>
          )}
        </div>
      </div>

      {/* Pointer */}
      <div className="card">
        <div className="card-header">Pointer</div>
        <div className="settings-row">
          <div>
            <div className="settings-label">Sensitivity</div>
            <div className="settings-desc">Pointer speed multiplier ({settings.sensitivity.toFixed(1)}×)</div>
          </div>
        </div>
        <input
          type="range"
          min={0.5} max={3.0} step={0.1}
          value={settings.sensitivity}
          onChange={e => updateSettings({ sensitivity: parseFloat(e.target.value) })}
          style={{ width: '100%', accentColor: 'var(--accent)', marginBottom: 8 }}
          id="sensitivity-slider"
        />
        <div className="settings-row">
          <div>
            <div className="settings-label">Acceleration</div>
            <div className="settings-desc">Faster movement amplifies pointer speed</div>
          </div>
          <label className="toggle">
            <input
              type="checkbox"
              checked={settings.acceleration}
              onChange={e => updateSettings({ acceleration: e.target.checked })}
              id="acceleration-toggle"
            />
            <span className="toggle-slider" />
          </label>
        </div>
        <div className="settings-row">
          <div>
            <div className="settings-label">Natural Scroll</div>
            <div className="settings-desc">Scroll content in gesture direction</div>
          </div>
          <label className="toggle">
            <input
              type="checkbox"
              checked={settings.scrollNatural}
              onChange={e => updateSettings({ scrollNatural: e.target.checked })}
              id="natural-scroll-toggle"
            />
            <span className="toggle-slider" />
          </label>
        </div>
      </div>

      {/* Diagnostics */}
      <div className="card">
        <div className="card-header">Diagnostics</div>
        <div className="settings-row">
          <div>
            <div className="settings-label">Connected Devices</div>
          </div>
          <span style={{ fontSize: 14, fontFamily: 'var(--font-mono)' }}>
            {state.devices.filter(d => d.online).length} / {state.devices.length}
          </span>
        </div>
        <div className="settings-row">
          <div>
            <div className="settings-label">Layout Version</div>
          </div>
          <span style={{ fontSize: 14, fontFamily: 'var(--font-mono)' }}>
            {state.layoutVersion}
          </span>
        </div>
        <div className="settings-row">
          <div>
            <div className="settings-label">Active Device</div>
          </div>
          <span style={{ fontSize: 12, fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
            {state.activeDeviceId?.slice(0, 8) ?? 'none'}
          </span>
        </div>
      </div>

      {/* About */}
      <div className="card" style={{ textAlign: 'center' }}>
        <div style={{ fontSize: 24, marginBottom: 8 }}>🪐</div>
        <div style={{ fontWeight: 700, fontSize: 16 }}>Orbit</div>
        <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>
          Universal Multi-Laptop Remote Control<br />
          Version 1.0.0 · Protocol 1.0.0
        </div>
      </div>
    </div>
  )
}
