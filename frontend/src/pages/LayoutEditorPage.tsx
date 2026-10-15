/**
 * Virtual Display Layout Editor
 *
 * Uses SVG + drag via pointer events to arrange laptop rectangles.
 * Maintains two coordinate systems:
 *   - Virtual desktop (logical pixels, stored in backend)
 *   - Canvas (scaled for display in the editor)
 *
 * Drag uses pointer capture for reliable tracking across element bounds.
 */

import { useState, useRef, useCallback, useEffect } from 'react'
import { useOrbit } from '../store/OrbitContext'
import type { LayoutDevice } from '../types/protocol'

const CANVAS_H = 220
const SCALE = 0.08          // virtual pixels → canvas pixels
const SNAP_GRID = 10        // snap to 10px virtual grid

interface EditorRect extends LayoutDevice {
  friendly_name: string
  online: boolean
  screen_width: number
  screen_height: number
}

function snapTo(v: number): number {
  return Math.round(v / SNAP_GRID) * SNAP_GRID
}

export default function LayoutEditorPage() {
  const { state } = useOrbit()
  const { devices, layout: savedLayout, layoutVersion } = state

  const [rects, setRects] = useState<EditorRect[]>([])
  const [selected, setSelected] = useState<string | null>(null)
  const [dirty, setDirty] = useState(false)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const panOffset = { x: 20, y: 20 }

  const svgRef = useRef<SVGSVGElement>(null)
  const dragging = useRef<{ id: string; startVX: number; startVY: number; startPX: number; startPY: number } | null>(null)

  // Initialize rects from saved layout + device info
  useEffect(() => {
    const next: EditorRect[] = devices.map((d, idx) => {
      const saved = savedLayout.find(l => l.device_id === d.device_id)
      return {
        device_id: d.device_id,
        friendly_name: d.friendly_name,
        online: d.online,
        screen_width: d.screen_width,
        screen_height: d.screen_height,
        x: saved?.x ?? (idx * 1980),
        y: saved?.y ?? 0,
        width: saved?.width ?? d.screen_width,
        height: saved?.height ?? d.screen_height,
      }
    })
    setRects(next)
    setDirty(false)
  }, [devices, savedLayout, layoutVersion])

  const toCanvas = useCallback((vx: number, vy: number) => ({
    cx: vx * SCALE + panOffset.x,
    cy: vy * SCALE + panOffset.y,
  }), [panOffset.x, panOffset.y])

  const handleRectPointerDown = useCallback((e: React.PointerEvent, id: string) => {
    e.preventDefault()
    e.stopPropagation()
    setSelected(id)
    const rect = rects.find(r => r.device_id === id)!
    dragging.current = {
      id,
      startVX: rect.x,
      startVY: rect.y,
      startPX: e.clientX,
      startPY: e.clientY,
    };
    (e.target as SVGElement).setPointerCapture(e.pointerId)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rects])

  const handlePointerMove = useCallback((e: React.PointerEvent) => {
    if (!dragging.current) return
    const { id, startVX, startVY, startPX, startPY } = dragging.current
    const dPX = e.clientX - startPX
    const dPY = e.clientY - startPY
    const dVX = dPX / SCALE
    const dVY = dPY / SCALE
    const newVX = snapTo(startVX + dVX)
    const newVY = snapTo(startVY + dVY)

    setRects(prev => prev.map(r =>
      r.device_id === id ? { ...r, x: newVX, y: newVY } : r
    ))
    setDirty(true)
  }, [])

  const handlePointerUp = useCallback(() => {
    dragging.current = null
  }, [])

  const handleSave = async () => {
    setSaving(true)
    try {
      const payload = {
        layout: rects.map(r => ({
          device_id: r.device_id,
          x: r.x, y: r.y,
          width: r.width, height: r.height,
        })),
      }
      const resp = await fetch('/api/v1/layout/', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (resp.ok) {
        setDirty(false)
        setSaved(true)
        setTimeout(() => setSaved(false), 2000)
      }
    } finally {
      setSaving(false)
    }
  }

  const handleReset = () => {
    const next: EditorRect[] = devices.map((d, idx) => ({
      device_id: d.device_id,
      friendly_name: d.friendly_name,
      online: d.online,
      screen_width: d.screen_width,
      screen_height: d.screen_height,
      x: idx * 1980, y: 0,
      width: d.screen_width, height: d.screen_height,
    }))
    setRects(next)
    setDirty(true)
  }

  const selectedRect = rects.find(r => r.device_id === selected)

  return (
    <div style={{ padding: '12px', display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h1 style={{ fontSize: 20, fontWeight: 700 }}>Display Layout</h1>
          <p style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 2 }}>
            Drag laptops to arrange their virtual positions
          </p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="btn btn-secondary" onClick={handleReset} style={{ fontSize: 12, padding: '6px 10px' }}>
            Reset
          </button>
          <button
            className={`btn ${dirty ? 'btn-primary' : 'btn-secondary'}`}
            onClick={handleSave}
            disabled={!dirty || saving}
            style={{ fontSize: 12, padding: '6px 14px' }}
            id="save-layout-btn"
          >
            {saving ? 'Saving…' : saved ? '✓ Saved' : 'Apply'}
          </button>
        </div>
      </div>

      {/* SVG Canvas */}
      <div
        className="layout-canvas"
        style={{ width: '100%', height: CANVAS_H, position: 'relative' }}
      >
        <svg
          ref={svgRef}
          width="100%"
          height={CANVAS_H}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
          onPointerLeave={handlePointerUp}
          style={{ display: 'block' }}
        >
          {/* Grid dots */}
          <defs>
            <pattern id="grid" width={20} height={20} patternUnits="userSpaceOnUse">
              <circle cx={1} cy={1} r={0.8} fill="rgba(255,255,255,0.06)" />
            </pattern>
          </defs>
          <rect width="100%" height={CANVAS_H} fill="url(#grid)" />

          {rects.map((r, idx) => {
            const { cx, cy } = toCanvas(r.x, r.y)
            const cw = r.width * SCALE
            const ch = r.height * SCALE
            const isSelected = r.device_id === selected

            return (
              <g
                key={r.device_id}
                onPointerDown={e => handleRectPointerDown(e, r.device_id)}
                style={{ cursor: 'grab' }}
              >
                {/* Drop shadow */}
                <rect
                  x={cx + 2} y={cy + 2}
                  width={cw} height={ch}
                  rx={4}
                  fill="rgba(0,0,0,0.4)"
                />
                {/* Main rect */}
                <rect
                  x={cx} y={cy}
                  width={cw} height={ch}
                  rx={4}
                  fill={r.online ? 'rgba(28,28,31,0.95)' : 'rgba(20,20,22,0.6)'}
                  stroke={isSelected ? '#6366f1' : r.online ? 'rgba(255,255,255,0.12)' : 'rgba(255,255,255,0.06)'}
                  strokeWidth={isSelected ? 2 : 1}
                  strokeDasharray={r.online ? undefined : '4,3'}
                  style={{ filter: isSelected ? 'drop-shadow(0 0 8px rgba(99,102,241,0.5))' : undefined }}
                />
                {/* Display number */}
                <text
                  x={cx + cw / 2} y={cy + ch / 2 - 8}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fill={isSelected ? '#818cf8' : r.online ? '#6b6b7b' : '#3d3d45'}
                  fontSize={Math.min(cw * 0.3, 20)}
                  fontWeight={700}
                  style={{ userSelect: 'none' }}
                >
                  {idx + 1}
                </text>
                {/* Name */}
                <text
                  x={cx + cw / 2} y={cy + ch / 2 + 8}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fill={r.online ? '#9898a8' : '#3d3d45'}
                  fontSize={Math.min(cw * 0.1, 9)}
                  style={{ userSelect: 'none' }}
                >
                  {r.friendly_name.length > 12 ? r.friendly_name.slice(0, 12) + '…' : r.friendly_name}
                </text>
                {/* Offline badge */}
                {!r.online && (
                  <text x={cx + cw / 2} y={cy + 10} textAnchor="middle" fill="#3d3d45" fontSize={7} style={{ userSelect: 'none' }}>
                    OFFLINE
                  </text>
                )}
              </g>
            )
          })}
        </svg>

        {devices.length === 0 && (
          <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', pointerEvents: 'none' }}>
            <div style={{ textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>
              Pair devices first to see them here
            </div>
          </div>
        )}
      </div>

      {/* Selected device info */}
      {selectedRect && (
        <div className="card fade-in">
          <div className="card-header">Selected: {selectedRect.friendly_name}</div>
          <div style={{ display: 'flex', gap: 12, fontSize: 12, color: 'var(--text-muted)' }}>
            <span>Resolution: {selectedRect.screen_width}×{selectedRect.screen_height}</span>
            <span>Position: {Math.round(selectedRect.x)}, {Math.round(selectedRect.y)}</span>
            <span style={{ color: selectedRect.online ? 'var(--success)' : 'var(--danger)' }}>
              {selectedRect.online ? '● Online' : '○ Offline'}
            </span>
          </div>
        </div>
      )}

      {/* Legend */}
      <div style={{ display: 'flex', gap: 16, fontSize: 11, color: 'var(--text-muted)' }}>
        <span>● Online</span>
        <span style={{ opacity: 0.4 }}>○ - - Offline (position preserved)</span>
      </div>

      {/* Topology version */}
      <div style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
        Layout version: {layoutVersion}
      </div>
    </div>
  )
}
