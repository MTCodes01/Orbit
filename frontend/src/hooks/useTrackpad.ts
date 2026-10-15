/**
 * Trackpad hook — translates touch/pointer events into Orbit input messages.
 *
 * Gesture recognition:
 * - 1-finger move → pointer_move (relative)
 * - 1-finger tap → left click
 * - 2-finger tap → right click
 * - 2-finger move → scroll
 * - Press-and-hold (500ms) → begin drag (mouse_down held)
 *
 * Touch restrictions:
 * - preventDefault() on all touchmove / pointerdown / contextmenu events
 *   scoped to the trackpad element only. Does not affect the rest of the app.
 */

import { useRef, useCallback } from 'react'

export interface TrackpadCallbacks {
  onPointerMove: (dx: number, dy: number) => void
  onMouseDown: (button: 'left' | 'right' | 'middle') => void
  onMouseUp: (button: 'left' | 'right' | 'middle') => void
  onScroll: (dx: number, dy: number) => void
}

interface Touch {
  id: number
  x: number
  y: number
}

const TAP_MAX_MOVE = 8         // px — tap cancelled if moved more
const TAP_MAX_DURATION = 250   // ms
const HOLD_DURATION = 500      // ms — hold for drag-start
const SCROLL_SCALE = 0.3

export function useTrackpad(
  callbacks: TrackpadCallbacks,
  sensitivity: number = 1.2,
  accelerationEnabled: boolean = true,
) {
  const touchesRef = useRef<Map<number, Touch>>(new Map())
  const prevCentroidRef = useRef<{ x: number; y: number } | null>(null)
  const touchStartRef = useRef<{ x: number; y: number; time: number } | null>(null)
  const holdTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const isDraggingRef = useRef(false)
  const gestureRef = useRef<'idle' | 'move' | 'scroll'>('idle')

  const clearHold = useCallback(() => {
    if (holdTimerRef.current) {
      clearTimeout(holdTimerRef.current)
      holdTimerRef.current = null
    }
  }, [])

  const onPointerDown = useCallback((e: PointerEvent) => {
    e.preventDefault()
    touchesRef.current.set(e.pointerId, { id: e.pointerId, x: e.clientX, y: e.clientY })

    if (touchesRef.current.size === 1) {
      touchStartRef.current = { x: e.clientX, y: e.clientY, time: Date.now() }
      gestureRef.current = 'idle'

      // Press-and-hold → drag
      holdTimerRef.current = setTimeout(() => {
        isDraggingRef.current = true
        callbacks.onMouseDown('left')
      }, HOLD_DURATION)
    }

    if (touchesRef.current.size >= 2) {
      clearHold()
      gestureRef.current = 'scroll'
    }

    // Centroid
    const pts = Array.from(touchesRef.current.values())
    prevCentroidRef.current = {
      x: pts.reduce((s, p) => s + p.x, 0) / pts.length,
      y: pts.reduce((s, p) => s + p.y, 0) / pts.length,
    }
  }, [callbacks, clearHold])

  const onPointerMove = useCallback((e: PointerEvent) => {
    e.preventDefault()
    if (!touchesRef.current.has(e.pointerId)) return
    touchesRef.current.set(e.pointerId, { id: e.pointerId, x: e.clientX, y: e.clientY })

    const pts = Array.from(touchesRef.current.values())
    const cx = pts.reduce((s, p) => s + p.x, 0) / pts.length
    const cy = pts.reduce((s, p) => s + p.y, 0) / pts.length

    if (!prevCentroidRef.current) {
      prevCentroidRef.current = { x: cx, y: cy }
      return
    }

    const rawDx = cx - prevCentroidRef.current.x
    const rawDy = cy - prevCentroidRef.current.y
    prevCentroidRef.current = { x: cx, y: cy }

    if (Math.abs(rawDx) < 0.3 && Math.abs(rawDy) < 0.3) return

    if (pts.length >= 2) {
      gestureRef.current = 'scroll'
      clearHold()
      callbacks.onScroll(rawDx * SCROLL_SCALE, rawDy * SCROLL_SCALE)
      return
    }

    if (pts.length === 1) {
      gestureRef.current = 'move'
      clearHold()

      // Apply acceleration
      let dx = rawDx * sensitivity
      let dy = rawDy * sensitivity
      if (accelerationEnabled) {
        const speed = Math.sqrt(dx * dx + dy * dy)
        const accel = Math.min(1 + speed * 0.04, 2.5)
        dx *= accel
        dy *= accel
      }

      callbacks.onPointerMove(dx, dy)
    }
  }, [callbacks, sensitivity, accelerationEnabled, clearHold])

  const onPointerUp = useCallback((e: PointerEvent) => {
    e.preventDefault()
    const hadTouch = touchesRef.current.has(e.pointerId)
    touchesRef.current.delete(e.pointerId)
    clearHold()

    if (!hadTouch) return

    const count = touchesRef.current.size

    if (count === 0) {
      if (isDraggingRef.current) {
        callbacks.onMouseUp('left')
        isDraggingRef.current = false
        return
      }

      const start = touchStartRef.current
      if (start && gestureRef.current === 'idle') {
        const dt = Date.now() - start.time
        const dx = e.clientX - start.x
        const dy = e.clientY - start.y
        const dist = Math.sqrt(dx * dx + dy * dy)
        if (dt < TAP_MAX_DURATION && dist < TAP_MAX_MOVE) {
          // Tap → left click
          callbacks.onMouseDown('left')
          setTimeout(() => callbacks.onMouseUp('left'), 30)
        }
      }

      prevCentroidRef.current = null
      touchStartRef.current = null
      gestureRef.current = 'idle'
    }
  }, [callbacks, clearHold])

  const onPointerCancel = useCallback((e: PointerEvent) => {
    touchesRef.current.delete(e.pointerId)
    clearHold()
    if (isDraggingRef.current) {
      callbacks.onMouseUp('left')
      isDraggingRef.current = false
    }
  }, [callbacks, clearHold])

  // Two-finger tap detection — contextmenu event on mobile
  const onContextMenu = useCallback((e: Event) => {
    e.preventDefault()
    callbacks.onMouseDown('right')
    setTimeout(() => callbacks.onMouseUp('right'), 30)
  }, [callbacks])

  return { onPointerDown, onPointerMove, onPointerUp, onPointerCancel, onContextMenu }
}
