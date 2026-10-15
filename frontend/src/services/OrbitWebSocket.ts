/**
 * OrbitWebSocket — resilient WebSocket client with exponential backoff reconnection.
 *
 * Design decisions:
 * - Reconnect on any close/error (not just network loss).
 * - Bounded backoff: 500ms → 2s → 4s → 8s → 16s → 30s max.
 * - Jitter on reconnect to avoid thundering herd when backend restarts.
 * - Observers are notified of state changes and incoming messages.
 * - High-frequency pointer_move messages are coalesced (only latest buffered).
 *   Key-down/up and mouse-button messages are never coalesced.
 */

import type { IncomingMessage } from '../types/protocol'

type ConnectionState = 'disconnected' | 'connecting' | 'connected' | 'error'

type StateListener = (state: ConnectionState) => void
type MessageListener = (msg: IncomingMessage) => void

const MAX_BACKOFF_MS = 30_000
const BASE_BACKOFF_MS = 500

export class OrbitWebSocket {
  private ws: WebSocket | null = null
  private url: string
  private state: ConnectionState = 'disconnected'
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private reconnectAttempts = 0
  private destroyed = false

  // Pending coalesced pointer_move (only ever one in flight)
  private pendingPointerMove: string | null = null
  private pointerMoveRaf: number | null = null

  private stateListeners: Set<StateListener> = new Set()
  private messageListeners: Set<MessageListener> = new Set()

  // Ping / latency tracking
  private pingInterval: ReturnType<typeof setInterval> | null = null
  public latencyMs: number = 0

  constructor(url: string) {
    this.url = url
  }

  // ---------------------------------------------------------------------------
  // Public API
  // ---------------------------------------------------------------------------

  connect() {
    if (this.destroyed) return
    this._clearReconnectTimer()
    this._setState('connecting')

    try {
      this.ws = new WebSocket(this.url)
    } catch (err) {
      this._setState('error')
      this._scheduleReconnect()
      return
    }

    this.ws.onopen = () => {
      this.reconnectAttempts = 0
      this._setState('connected')
      this._startPingLoop()
    }

    this.ws.onmessage = (ev: MessageEvent) => {
      try {
        const msg = JSON.parse(ev.data) as IncomingMessage
        this._handleMessage(msg)
      } catch {
        // ignore malformed messages
      }
    }

    this.ws.onclose = () => {
      this._setState('disconnected')
      this._stopPingLoop()
      if (!this.destroyed) this._scheduleReconnect()
    }

    this.ws.onerror = () => {
      this._setState('error')
    }
  }

  disconnect() {
    this.destroyed = true
    this._clearReconnectTimer()
    this._stopPingLoop()
    if (this.ws) {
      this.ws.onopen = null
      this.ws.onmessage = null
      this.ws.onclose = null
      this.ws.onerror = null
      this.ws.close()
      this.ws = null
    }
    this._setState('disconnected')
  }

  /** Reconnect on demand (e.g., after settings change). */
  reconnect() {
    this.destroyed = false
    this.reconnectAttempts = 0
    if (this.ws) {
      this.ws.close()
    }
    this.connect()
  }

  send(data: object) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data))
    }
  }

  /**
   * Send a pointer_move, coalescing rapid events via requestAnimationFrame.
   * Other message types must use send() directly.
   */
  sendPointerMove(target_device_id: string, dx: number, dy: number) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return

    // Accumulate deltas into a single pending message
    if (this.pendingPointerMove) {
      const prev = JSON.parse(this.pendingPointerMove)
      dx += prev.dx
      dy += prev.dy
    }

    this.pendingPointerMove = JSON.stringify({
      type: 'pointer_move',
      protocol_version: '1.0.0',
      target_device_id,
      dx,
      dy,
      timestamp_ms: Date.now(),
    })

    if (this.pointerMoveRaf === null) {
      this.pointerMoveRaf = requestAnimationFrame(() => {
        if (this.pendingPointerMove && this.ws?.readyState === WebSocket.OPEN) {
          this.ws.send(this.pendingPointerMove)
        }
        this.pendingPointerMove = null
        this.pointerMoveRaf = null
      })
    }
  }

  getState(): ConnectionState {
    return this.state
  }

  onStateChange(fn: StateListener): () => void {
    this.stateListeners.add(fn)
    return () => this.stateListeners.delete(fn)
  }

  onMessage(fn: MessageListener): () => void {
    this.messageListeners.add(fn)
    return () => this.messageListeners.delete(fn)
  }

  // ---------------------------------------------------------------------------
  // Private helpers
  // ---------------------------------------------------------------------------

  private _setState(s: ConnectionState) {
    this.state = s
    this.stateListeners.forEach(fn => fn(s))
  }

  private _handleMessage(msg: IncomingMessage) {
    if (msg.type === 'latency_pong') {
      const pong = msg as { type: string; sent_ms: number }
      this.latencyMs = Date.now() - pong.sent_ms
    }
    this.messageListeners.forEach(fn => fn(msg))
  }

  private _scheduleReconnect() {
    this._clearReconnectTimer()
    const backoff = Math.min(
      BASE_BACKOFF_MS * Math.pow(2, this.reconnectAttempts),
      MAX_BACKOFF_MS,
    )
    const jitter = Math.random() * 500
    this.reconnectAttempts++
    this.reconnectTimer = setTimeout(() => {
      if (!this.destroyed) this.connect()
    }, backoff + jitter)
  }

  private _clearReconnectTimer() {
    if (this.reconnectTimer !== null) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
  }

  private _startPingLoop() {
    this._stopPingLoop()
    this.pingInterval = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({
          type: 'latency_ping',
          protocol_version: '1.0.0',
          ping_id: crypto.randomUUID(),
          sent_ms: Date.now(),
        }))
      }
    }, 5000)
  }

  private _stopPingLoop() {
    if (this.pingInterval !== null) {
      clearInterval(this.pingInterval)
      this.pingInterval = null
    }
  }
}
