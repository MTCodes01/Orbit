/**
 * Global Orbit application state — React context + useReducer.
 *
 * This is the single source of truth for:
 * - WebSocket connection state
 * - Device list
 * - Active device selection
 * - Virtual layout
 * - Settings
 */

import React, {
  createContext,
  useContext,
  useEffect,
  useReducer,
  useRef,
  useCallback,
} from 'react'
import { OrbitWebSocket } from '../services/OrbitWebSocket'
import type { DeviceInfo, IncomingMessage, LayoutDevice } from '../types/protocol'

// ---------------------------------------------------------------------------
// State shape
// ---------------------------------------------------------------------------

export interface Settings {
  backendUrl: string
  sensitivity: number       // pointer speed multiplier 0.5–3.0
  acceleration: boolean
  scrollNatural: boolean    // "natural" (reverse) scroll
}

export interface OrbitState {
  connectionState: 'disconnected' | 'connecting' | 'connected' | 'error'
  latencyMs: number
  devices: DeviceInfo[]
  activeDeviceId: string | null
  layout: LayoutDevice[]
  layoutVersion: number
  settings: Settings
  pairingPending: Array<{ code: string; device_name: string }>
}

const DEFAULT_SETTINGS: Settings = {
  backendUrl: `ws://${window.location.hostname}:8000/ws/controller`,
  sensitivity: 1.2,
  acceleration: true,
  scrollNatural: true,
}

function getInitialSettings(): Settings {
  try {
    if (typeof window !== 'undefined' && window.localStorage && typeof window.localStorage.getItem === 'function') {
      const saved = window.localStorage.getItem('orbit-settings')
      if (saved) return { ...DEFAULT_SETTINGS, ...JSON.parse(saved) }
    }
  } catch (err) {
    // ignore
  }
  return DEFAULT_SETTINGS
}

const INITIAL_STATE: OrbitState = {
  connectionState: 'disconnected',
  latencyMs: 0,
  devices: [],
  activeDeviceId: null,
  layout: [],
  layoutVersion: 0,
  settings: getInitialSettings(),
  pairingPending: [],
}

// ---------------------------------------------------------------------------
// Actions
// ---------------------------------------------------------------------------

type Action =
  | { type: 'SET_CONNECTION_STATE'; state: OrbitState['connectionState'] }
  | { type: 'SET_LATENCY'; ms: number }
  | { type: 'SET_DEVICES'; devices: DeviceInfo[] }
  | { type: 'SET_DEVICE_ONLINE'; device_id: string }
  | { type: 'SET_DEVICE_OFFLINE'; device_id: string }
  | { type: 'REMOVE_DEVICE'; device_id: string }
  | { type: 'SET_ACTIVE_DEVICE'; device_id: string | null }
  | { type: 'SET_LAYOUT'; layout: LayoutDevice[]; version: number }
  | { type: 'UPDATE_SETTINGS'; settings: Partial<Settings> }
  | { type: 'ADD_PAIRING_PENDING'; code: string; device_name: string }
  | { type: 'REMOVE_PAIRING_PENDING'; code: string }

function reducer(state: OrbitState, action: Action): OrbitState {
  switch (action.type) {
    case 'SET_CONNECTION_STATE':
      return { ...state, connectionState: action.state }
    case 'SET_LATENCY':
      return { ...state, latencyMs: action.ms }
    case 'SET_DEVICES':
      return { ...state, devices: action.devices }
    case 'SET_DEVICE_ONLINE':
      return {
        ...state,
        devices: state.devices.map(d =>
          d.device_id === action.device_id ? { ...d, online: true } : d,
        ),
      }
    case 'SET_DEVICE_OFFLINE':
      return {
        ...state,
        devices: state.devices.map(d =>
          d.device_id === action.device_id ? { ...d, online: false } : d,
        ),
      }
    case 'REMOVE_DEVICE':
      return {
        ...state,
        devices: state.devices.filter(d => d.device_id !== action.device_id),
        activeDeviceId:
          state.activeDeviceId === action.device_id ? null : state.activeDeviceId,
      }
    case 'SET_ACTIVE_DEVICE':
      return { ...state, activeDeviceId: action.device_id }
    case 'SET_LAYOUT':
      return { ...state, layout: action.layout, layoutVersion: action.version }
    case 'UPDATE_SETTINGS': {
      const next = { ...state.settings, ...action.settings }
      localStorage.setItem('orbit-settings', JSON.stringify(next))
      return { ...state, settings: next }
    }
    case 'ADD_PAIRING_PENDING':
      return {
        ...state,
        pairingPending: [
          ...state.pairingPending.filter(p => p.code !== action.code),
          { code: action.code, device_name: action.device_name },
        ],
      }
    case 'REMOVE_PAIRING_PENDING':
      return {
        ...state,
        pairingPending: state.pairingPending.filter(p => p.code !== action.code),
      }
    default:
      return state
  }
}

// ---------------------------------------------------------------------------
// Context
// ---------------------------------------------------------------------------

interface OrbitContextValue {
  state: OrbitState
  ws: OrbitWebSocket | null
  dispatch: React.Dispatch<Action>
  setActiveDevice: (id: string | null) => void
  updateSettings: (s: Partial<Settings>) => void
  sendInput: (msg: object) => void
}

const OrbitContext = createContext<OrbitContextValue | null>(null)

export function OrbitProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(reducer, INITIAL_STATE)
  const wsRef = useRef<OrbitWebSocket | null>(null)

  // Connect / reconnect when backendUrl changes
  useEffect(() => {
    const ws = new OrbitWebSocket(state.settings.backendUrl)
    wsRef.current = ws

    const unsubState = ws.onStateChange(s => {
      dispatch({ type: 'SET_CONNECTION_STATE', state: s })
    })

    const unsubMsg = ws.onMessage((msg: IncomingMessage) => {
      switch (msg.type) {
        case 'device_list':
          if ('devices' in msg) dispatch({ type: 'SET_DEVICES', devices: msg.devices })
          break
        case 'device_online':
          if ('device_id' in msg) dispatch({ type: 'SET_DEVICE_ONLINE', device_id: msg.device_id as string })
          break
        case 'device_offline':
          if ('device_id' in msg) dispatch({ type: 'SET_DEVICE_OFFLINE', device_id: msg.device_id as string })
          break
        case 'device_revoked':
          if ('device_id' in msg) dispatch({ type: 'REMOVE_DEVICE', device_id: msg.device_id as string })
          break
        case 'topology_update':
          if ('layout' in msg && 'version' in msg) {
            dispatch({ type: 'SET_LAYOUT', layout: msg.layout as LayoutDevice[], version: msg.version as number })
          }
          break
        case 'latency_pong':
          dispatch({ type: 'SET_LATENCY', ms: ws.latencyMs })
          break
        case 'pair_pending':
          if ('code' in msg && 'device_name' in msg) {
            dispatch({ type: 'ADD_PAIRING_PENDING', code: msg.code as string, device_name: msg.device_name as string })
          }
          break
        case 'pair_resolved':
          if ('code' in msg) {
            dispatch({ type: 'REMOVE_PAIRING_PENDING', code: msg.code as string })
          }
          break
        case 'cursor_handoff_success':
          if ('to_device_id' in msg) {
            dispatch({ type: 'SET_ACTIVE_DEVICE', device_id: msg.to_device_id as string })
          }
          break
      }
    })

    ws.connect()

    return () => {
      unsubState()
      unsubMsg()
      ws.disconnect()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state.settings.backendUrl])

  // Notify backend when active device changes
  const setActiveDevice = useCallback((id: string | null) => {
    dispatch({ type: 'SET_ACTIVE_DEVICE', device_id: id })
    wsRef.current?.send({ type: 'active_device', device_id: id })
  }, [])

  const updateSettings = useCallback((s: Partial<Settings>) => {
    dispatch({ type: 'UPDATE_SETTINGS', settings: s })
  }, [])

  const sendInput = useCallback((msg: object) => {
    wsRef.current?.send(msg)
  }, [])

  return (
    <OrbitContext.Provider value={{ state, ws: wsRef.current, dispatch, setActiveDevice, updateSettings, sendInput }}>
      {children}
    </OrbitContext.Provider>
  )
}

export function useOrbit(): OrbitContextValue {
  const ctx = useContext(OrbitContext)
  if (!ctx) throw new Error('useOrbit must be used within OrbitProvider')
  return ctx
}
