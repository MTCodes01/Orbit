/**
 * Pairing page — displays a short-lived code that the agent enters on first run.
 * Also shows pending pairing requests that need user approval.
 */

import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useOrbit } from '../store/OrbitContext'

interface PendingPair {
  code: string
  device_name: string
  hostname: string
  os_info: string
  agent_version: string
  screen_width: number
  screen_height: number
}

export default function PairingPage() {
  const { state, dispatch } = useOrbit()
  const { pairingPending } = state
  const navigate = useNavigate()

  const [code, setCode] = useState<string | null>(null)
  const [expiresIn, setExpiresIn] = useState(0)
  const [loading, setLoading] = useState(false)
  const [pendingList, setPendingList] = useState<PendingPair[]>([])

  const generateCode = async () => {
    setLoading(true)
    try {
      const resp = await fetch('/api/v1/pairing/generate', { method: 'POST' })
      if (resp.ok) {
        const data = await resp.json()
        setCode(data.code)
        setExpiresIn(data.expires_in_seconds)
      }
    } finally {
      setLoading(false)
    }
  }

  // Countdown timer
  useEffect(() => {
    if (expiresIn <= 0) return
    const t = setInterval(() => {
      setExpiresIn(prev => {
        if (prev <= 1) { clearInterval(t); setCode(null); return 0 }
        return prev - 1
      })
    }, 1000)
    return () => clearInterval(t)
  }, [expiresIn])

  // Poll for pending pairs
  const fetchPending = async () => {
    try {
      const resp = await fetch('/api/v1/pairing/pending')
      if (resp.ok) setPendingList(await resp.json())
    } catch {}
  }

  useEffect(() => {
    fetchPending()
    const t = setInterval(fetchPending, 5000)
    return () => clearInterval(t)
  }, [])

  const handleApprove = async (code: string) => {
    const resp = await fetch('/api/v1/pairing/approve', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code }),
    })
    if (resp.ok) {
      dispatch({ type: 'REMOVE_PAIRING_PENDING', code })
      setPendingList(prev => prev.filter(p => p.code !== code))
      navigate('/devices')
    }
  }

  const handleReject = async (code: string) => {
    await fetch('/api/v1/pairing/reject', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code }),
    })
    dispatch({ type: 'REMOVE_PAIRING_PENDING', code })
    setPendingList(prev => prev.filter(p => p.code !== code))
  }

  const allPending = [
    ...pendingList,
    ...pairingPending.filter(p => !pendingList.find(pl => pl.code === p.code)).map(p => ({
      code: p.code,
      device_name: p.device_name,
      hostname: '', os_info: '', agent_version: '',
      screen_width: 0, screen_height: 0,
    })),
  ]

  return (
    <div style={{ padding: '16px 12px', display: 'flex', flexDirection: 'column', gap: 20 }}>
      <div>
        <h1 style={{ fontSize: 20, fontWeight: 700 }}>Pair a Device</h1>
        <p style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 4 }}>
          Generate a code, then enter it in the Orbit agent on your Windows laptop.
        </p>
      </div>

      {/* Pairing code display */}
      <div className="card" style={{ textAlign: 'center' }}>
        {!code ? (
          <button
            className="btn btn-primary"
            style={{ width: '100%', padding: '14px' }}
            onClick={generateCode}
            disabled={loading}
            id="generate-code-btn"
          >
            {loading ? 'Generating…' : 'Generate Pairing Code'}
          </button>
        ) : (
          <>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 12 }}>
              Enter this code in the Orbit agent:
            </div>
            <div className="pairing-code-display" id="pairing-code">{code}</div>
            <div style={{ marginTop: 12, fontSize: 12, color: expiresIn < 30 ? 'var(--danger)' : 'var(--text-muted)' }}>
              Expires in {expiresIn}s
            </div>
            <button
              className="btn btn-secondary"
              onClick={generateCode}
              style={{ marginTop: 16, width: '100%' }}
            >
              Generate New Code
            </button>
          </>
        )}
      </div>

      {/* Pending approvals */}
      {allPending.length > 0 && (
        <div>
          <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 10 }}>
            Pending Approval ({allPending.length})
          </h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {allPending.map(p => (
              <div key={p.code} className="card" style={{ borderColor: 'rgba(99,102,241,0.3)' }}>
                <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 4 }}>{p.device_name}</div>
                {p.hostname && (
                  <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 12 }}>
                    {p.hostname} · {p.os_info} · {p.screen_width}×{p.screen_height}
                  </div>
                )}
                <div style={{ display: 'flex', gap: 10 }}>
                  <button
                    className="btn btn-danger"
                    style={{ flex: 1 }}
                    onClick={() => handleReject(p.code)}
                    id={`reject-${p.code}`}
                  >
                    Reject
                  </button>
                  <button
                    className="btn btn-primary"
                    style={{ flex: 1 }}
                    onClick={() => handleApprove(p.code)}
                    id={`approve-${p.code}`}
                  >
                    Approve
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Instructions */}
      <div className="card" style={{ background: 'var(--bg-elevated)' }}>
        <div className="card-header">How to pair</div>
        {[
          'Download and run orbit-agent.exe on the Windows laptop',
          'On first run, the agent will ask for the backend URL',
          'Enter: http://<your-server-ip>:8000',
          'The agent will request a pairing code — enter the code shown above',
          'Approve the request on this screen',
          'The laptop will appear in your Devices list',
        ].map((step, i) => (
          <div key={i} style={{ display: 'flex', gap: 10, padding: '6px 0', borderBottom: i < 5 ? '1px solid var(--border-subtle)' : undefined }}>
            <span style={{ color: 'var(--accent)', fontWeight: 600, minWidth: 20 }}>{i + 1}.</span>
            <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{step}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
