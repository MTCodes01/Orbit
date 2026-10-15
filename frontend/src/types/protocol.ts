// Shared TypeScript types mirroring the protocol schema

export type MouseButton = 'left' | 'right' | 'middle'

export interface MonitorInfo {
  index: number
  width: number
  height: number
  x: number
  y: number
  is_primary: boolean
  dpi?: number
}

export interface DeviceCapabilities {
  supports_keyboard?: boolean
  supports_mouse?: boolean
  supports_scroll?: boolean
  supports_multi_monitor?: boolean
  monitor_count?: number
  monitors?: MonitorInfo[]
  [key: string]: unknown
}

export interface DeviceInfo {
  device_id: string
  friendly_name: string
  hostname: string
  os_info: string
  agent_version: string
  screen_width: number
  screen_height: number
  online: boolean
  last_seen_at: string | null
  layout_x: number | null
  layout_y: number | null
  capabilities: DeviceCapabilities
}

export interface LayoutDevice {
  device_id: string
  x: number
  y: number
  width: number
  height: number
}

export interface OrbitMessageBase {
  protocol_version: string
  type: string
  session_id?: string
  sequence?: number
  timestamp_ms?: number
}

export interface DeviceListMessage extends OrbitMessageBase {
  type: 'device_list'
  devices: DeviceInfo[]
}

export interface DeviceOnlineMessage extends OrbitMessageBase {
  type: 'device_online'
  device_id: string
}

export interface DeviceOfflineMessage extends OrbitMessageBase {
  type: 'device_offline'
  device_id: string
}

export interface DeviceRevokedMessage extends OrbitMessageBase {
  type: 'device_revoked'
  device_id: string
}

export interface PairPendingMessage extends OrbitMessageBase {
  type: 'pair_pending'
  code: string
  device_name: string
}

export interface TopologyUpdateMessage extends OrbitMessageBase {
  type: 'topology_update'
  version: number
  layout: LayoutDevice[]
}

export interface ErrorMessage extends OrbitMessageBase {
  type: 'error'
  code: string
  message: string
}

export interface LatencyPongMessage extends OrbitMessageBase {
  type: 'latency_pong'
  ping_id: string
  sent_ms: number
  received_ms: number
}

export type IncomingMessage =
  | DeviceListMessage
  | DeviceOnlineMessage
  | DeviceOfflineMessage
  | DeviceRevokedMessage
  | PairPendingMessage
  | TopologyUpdateMessage
  | ErrorMessage
  | LatencyPongMessage
  | OrbitMessageBase
