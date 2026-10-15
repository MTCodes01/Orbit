import { useNavigate } from 'react-router-dom'
import { useOrbit } from '../store/OrbitContext'

export default function DevicesPage() {
  const { state, setActiveDevice } = useOrbit()
  const { devices, activeDeviceId, connectionState } = state
  const navigate = useNavigate()

  return (
    <div style={{ padding: '16px 12px', display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h1 style={{ fontSize: 20, fontWeight: 700 }}>Devices</h1>
          <p style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 2 }}>
            {devices.filter(d => d.online).length} of {devices.length} online
          </p>
        </div>
        <button
          className="btn btn-primary"
          onClick={() => navigate('/pairing')}
          style={{ fontSize: 13, padding: '8px 14px' }}
          id="pair-new-device-btn"
        >
          + Pair
        </button>
      </div>

      {/* Device list */}
      {devices.length === 0 ? (
        <div className="empty-state" style={{ minHeight: 300 }}>
          <div className="empty-state-icon">💻</div>
          <div className="empty-state-title">No paired devices</div>
          <div className="empty-state-desc">
            Run the Orbit agent on a Windows laptop, then tap Pair to connect it.
          </div>
          <button className="btn btn-primary" onClick={() => navigate('/pairing')} style={{ marginTop: 8 }}>
            Pair first device
          </button>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {devices.map((d, idx) => (
            <div
              key={d.device_id}
              className={`card${activeDeviceId === d.device_id ? '' : ''}`}
              style={{
                border: `1px solid ${activeDeviceId === d.device_id ? 'var(--accent)' : 'var(--border-subtle)'}`,
                background: activeDeviceId === d.device_id ? 'rgba(99,102,241,0.05)' : 'var(--bg-surface)',
                cursor: 'pointer',
              }}
              onClick={() => navigate(`/devices/${d.device_id}`)}
              id={`device-card-${idx}`}
            >
              <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12 }}>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span
                      style={{
                        width: 8, height: 8, borderRadius: '50%', flexShrink: 0,
                        background: d.online ? 'var(--success)' : 'var(--text-muted)',
                        boxShadow: d.online ? '0 0 6px var(--success)' : 'none',
                      }}
                    />
                    <span style={{ fontWeight: 600, fontSize: 15, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {d.friendly_name}
                    </span>
                    {activeDeviceId === d.device_id && (
                      <span style={{ fontSize: 10, background: 'var(--accent-dim)', color: 'var(--accent)', padding: '2px 6px', borderRadius: 99, fontWeight: 600 }}>
                        ACTIVE
                      </span>
                    )}
                  </div>
                  <div style={{ marginTop: 4, fontSize: 12, color: 'var(--text-muted)' }}>
                    {d.hostname} · {d.screen_width}×{d.screen_height} · {d.os_info || 'Windows'}
                  </div>
                  <div style={{ marginTop: 2, fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                    v{d.agent_version || '—'} · {d.last_seen_at ? `Seen ${new Date(d.last_seen_at).toLocaleTimeString()}` : 'Never seen'}
                  </div>
                </div>
                <div style={{ display: 'flex', gap: 8, flexShrink: 0 }}>
                  {d.online && (
                    <button
                      className={`btn ${activeDeviceId === d.device_id ? 'btn-secondary' : 'btn-primary'}`}
                      style={{ fontSize: 12, padding: '6px 12px' }}
                      onClick={e => {
                        e.stopPropagation()
                        setActiveDevice(activeDeviceId === d.device_id ? null : d.device_id)
                      }}
                      id={`control-btn-${idx}`}
                    >
                      {activeDeviceId === d.device_id ? 'Release' : 'Control'}
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Connection hint */}
      {connectionState !== 'connected' && (
        <div className="card" style={{ background: 'rgba(239,68,68,0.08)', borderColor: 'rgba(239,68,68,0.2)' }}>
          <div style={{ fontSize: 13, color: 'var(--danger)', textAlign: 'center' }}>
            ⚠ Not connected to Orbit backend. Devices shown may be stale.
          </div>
        </div>
      )}
    </div>
  )
}
