import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useOrbit } from '../store/OrbitContext'

export default function DeviceDetailPage() {
  const { deviceId } = useParams<{ deviceId: string }>()
  const { state, setActiveDevice } = useOrbit()
  const navigate = useNavigate()
  const device = state.devices.find(d => d.device_id === deviceId)
  const [newName, setNewName] = useState('')
  const [renaming, setRenaming] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)

  useEffect(() => {
    if (device) setNewName(device.friendly_name)
  }, [device])

  if (!device) {
    return (
      <div className="empty-state" style={{ height: '100%' }}>
        <div className="empty-state-icon">🔍</div>
        <div className="empty-state-title">Device not found</div>
        <button className="btn btn-secondary" onClick={() => navigate('/devices')}>← Back</button>
      </div>
    )
  }

  const handleRename = async () => {
    if (!newName.trim() || newName === device.friendly_name) return
    setRenaming(true)
    try {
      const resp = await fetch(`/api/v1/devices/${deviceId}/rename`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ friendly_name: newName.trim() }),
      })
      if (resp.ok) {
        navigate('/devices')
      }
    } finally {
      setRenaming(false)
    }
  }

  const handleUnpair = async () => {
    const resp = await fetch(`/api/v1/devices/${deviceId}`, { method: 'DELETE' })
    if (resp.ok) {
      if (state.activeDeviceId === deviceId) setActiveDevice(null)
      navigate('/devices')
    }
  }

  return (
    <div style={{ padding: '12px', display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* Back */}
      <button onClick={() => navigate('/devices')} style={{ color: 'var(--text-muted)', fontSize: 13, textAlign: 'left', padding: 0 }}>
        ← Devices
      </button>

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <div style={{
          width: 48, height: 48, borderRadius: 12,
          background: 'var(--bg-elevated)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 24,
        }}>
          💻
        </div>
        <div>
          <h1 style={{ fontSize: 18, fontWeight: 700 }}>{device.friendly_name}</h1>
          <div style={{ fontSize: 12, color: device.online ? 'var(--success)' : 'var(--text-muted)' }}>
            {device.online ? '● Online' : '○ Offline'}
          </div>
        </div>
      </div>

      {/* Info */}
      <div className="card">
        <div className="card-header">Device Info</div>
        {[
          ['Hostname', device.hostname],
          ['OS', device.os_info || 'Windows'],
          ['Agent Version', device.agent_version || '—'],
          ['Resolution', `${device.screen_width}×${device.screen_height}`],
          ['Device ID', device.device_id],
          ['Last Seen', device.last_seen_at ? new Date(device.last_seen_at).toLocaleString() : 'Never'],
          ['Layout Position', device.layout_x != null ? `${device.layout_x}, ${device.layout_y}` : 'Not placed'],
        ].map(([label, value]) => (
          <div key={label} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid var(--border-subtle)', fontSize: 13 }}>
            <span style={{ color: 'var(--text-muted)' }}>{label}</span>
            <span style={{ fontFamily: label === 'Device ID' ? 'var(--font-mono)' : undefined, fontSize: label === 'Device ID' ? 10 : 13, maxWidth: '60%', textAlign: 'right', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              {value}
            </span>
          </div>
        ))}
      </div>

      {/* Connected Displays */}
      {device.capabilities?.monitors && device.capabilities.monitors.length > 0 && (
        <div className="card">
          <div className="card-header">Connected Displays ({device.capabilities.monitors.length})</div>
          {device.capabilities.monitors.map((mon, idx) => (
            <div
              key={mon.index}
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '8px 0',
                borderBottom: '1px solid var(--border-subtle)',
                fontSize: 13,
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span>🖥️ Display {idx + 1}</span>
                {mon.is_primary && (
                  <span style={{ fontSize: 10, padding: '2px 6px', borderRadius: 4, background: 'rgba(56, 189, 248, 0.15)', color: '#38bdf8' }}>
                    Primary
                  </span>
                )}
              </div>
              <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>
                {mon.width}×{mon.height} (pos: {mon.x}, {mon.y})
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Rename */}
      <div className="card">
        <div className="card-header">Rename Device</div>
        <div style={{ display: 'flex', gap: 8 }}>
          <input
            className="input-field"
            value={newName}
            onChange={e => setNewName(e.target.value)}
            placeholder="Friendly name"
            maxLength={64}
            id="rename-input"
          />
          <button className="btn btn-primary" onClick={handleRename} id="rename-btn" disabled={renaming}>
            {renaming ? 'Saving...' : 'Save'}
          </button>
        </div>
      </div>

      {/* Actions */}
      <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <div className="card-header">Actions</div>
        {state.activeDeviceId === deviceId ? (
          <button className="btn btn-secondary" onClick={() => setActiveDevice(null)} id="release-control-btn">
            Release Control
          </button>
        ) : device.online ? (
          <button className="btn btn-primary" onClick={() => { setActiveDevice(deviceId!); navigate('/trackpad') }} id="control-device-btn">
            Control Device
          </button>
        ) : null}

        {!confirmDelete ? (
          <button className="btn btn-danger" onClick={() => setConfirmDelete(true)} id="unpair-btn">
            Unpair Device
          </button>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <p style={{ fontSize: 13, color: 'var(--danger)', textAlign: 'center' }}>
              This will revoke the device's authorization. Are you sure?
            </p>
            <div style={{ display: 'flex', gap: 8 }}>
              <button className="btn btn-secondary" style={{ flex: 1 }} onClick={() => setConfirmDelete(false)}>Cancel</button>
              <button className="btn btn-danger" style={{ flex: 1 }} onClick={handleUnpair} id="confirm-unpair-btn">Delete</button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
