"""
Orbit Protocol — Versioned Message Schemas
Version: 1.0.0

This file is the single source of truth for every WebSocket message
exchanged between the PWA, coordinator backend, and Windows agents.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field
import uuid

PROTOCOL_VERSION = "1.0.0"


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class MessageType(str, Enum):
    # Pairing & auth
    PAIR_REQUEST       = "pair_request"
    PAIR_CHALLENGE     = "pair_challenge"
    PAIR_RESPONSE      = "pair_response"
    PAIR_SUCCESS       = "pair_success"
    PAIR_REJECTED      = "pair_rejected"

    AUTH_REQUEST       = "auth_request"
    AUTH_SUCCESS       = "auth_success"
    AUTH_FAILED        = "auth_failed"

    # Device lifecycle
    DEVICE_REGISTER    = "device_register"
    DEVICE_INFO        = "device_info"
    DEVICE_ONLINE      = "device_online"
    DEVICE_OFFLINE     = "device_offline"
    DEVICE_LIST        = "device_list"
    DEVICE_REVOKED     = "device_revoked"

    # Session
    SESSION_START      = "session_start"
    SESSION_END        = "session_end"
    ACTIVE_DEVICE      = "active_device"

    # Input — pointer
    POINTER_MOVE       = "pointer_move"
    MOUSE_DOWN         = "mouse_down"
    MOUSE_UP           = "mouse_up"
    SCROLL             = "scroll"

    # Input — keyboard
    KEY_DOWN           = "key_down"
    KEY_UP             = "key_up"
    TEXT_INPUT         = "text_input"
    SHORTCUT           = "shortcut"

    # Topology
    TOPOLOGY_UPDATE    = "topology_update"
    TOPOLOGY_ACK       = "topology_ack"
    CURSOR_HANDOFF     = "cursor_handoff"

    # Health
    HEARTBEAT          = "heartbeat"
    HEARTBEAT_ACK      = "heartbeat_ack"
    LATENCY_PING       = "latency_ping"
    LATENCY_PONG       = "latency_pong"

    # Errors & diagnostics
    ERROR              = "error"
    DIAGNOSTIC         = "diagnostic"
    CAPABILITY_NEG     = "capability_negotiation"


class MouseButton(str, Enum):
    LEFT   = "left"
    RIGHT  = "right"
    MIDDLE = "middle"


class ConnectionRole(str, Enum):
    CONTROLLER = "controller"   # PWA
    AGENT      = "agent"        # Laptop agent


# ---------------------------------------------------------------------------
# Base envelope
# ---------------------------------------------------------------------------

class OrbitMessage(BaseModel):
    protocol_version: str = PROTOCOL_VERSION
    type: MessageType
    session_id: Optional[str] = None
    sequence: Optional[int] = None
    timestamp_ms: Optional[int] = None   # Unix epoch milliseconds

    model_config = {"extra": "forbid"}


# ---------------------------------------------------------------------------
# Pairing & Authentication
# ---------------------------------------------------------------------------

class PairRequestPayload(BaseModel):
    pairing_code: str
    device_name: str
    hostname: str
    os_info: str
    agent_version: str
    screen_width: int
    screen_height: int


class PairRequest(OrbitMessage):
    type: Literal[MessageType.PAIR_REQUEST] = MessageType.PAIR_REQUEST
    payload: PairRequestPayload


class PairChallengePayload(BaseModel):
    challenge_token: str
    expires_in_seconds: int


class PairChallenge(OrbitMessage):
    type: Literal[MessageType.PAIR_CHALLENGE] = MessageType.PAIR_CHALLENGE
    payload: PairChallengePayload


class PairResponsePayload(BaseModel):
    challenge_token: str
    approved: bool


class PairResponse(OrbitMessage):
    type: Literal[MessageType.PAIR_RESPONSE] = MessageType.PAIR_RESPONSE
    payload: PairResponsePayload


class PairSuccessPayload(BaseModel):
    device_id: str
    device_secret: str   # Stored securely on agent side; never logged


class PairSuccess(OrbitMessage):
    type: Literal[MessageType.PAIR_SUCCESS] = MessageType.PAIR_SUCCESS
    payload: PairSuccessPayload


class PairRejected(OrbitMessage):
    type: Literal[MessageType.PAIR_REJECTED] = MessageType.PAIR_REJECTED
    reason: str


class AuthRequestPayload(BaseModel):
    device_id: str
    device_secret: str   # Should be transmitted over TLS/WSS only


class AuthRequest(OrbitMessage):
    type: Literal[MessageType.AUTH_REQUEST] = MessageType.AUTH_REQUEST
    payload: AuthRequestPayload


class AuthSuccess(OrbitMessage):
    type: Literal[MessageType.AUTH_SUCCESS] = MessageType.AUTH_SUCCESS
    session_token: str


class AuthFailed(OrbitMessage):
    type: Literal[MessageType.AUTH_FAILED] = MessageType.AUTH_FAILED
    reason: str


# ---------------------------------------------------------------------------
# Device information
# ---------------------------------------------------------------------------

class MonitorInfo(BaseModel):
    index: int
    width: int
    height: int
    x: int = 0
    y: int = 0
    is_primary: bool = False
    dpi: Optional[float] = None


class DeviceCapabilities(BaseModel):
    supports_keyboard: bool = True
    supports_mouse: bool = True
    supports_scroll: bool = True
    supports_multi_monitor: bool = False
    monitor_count: int = 1
    monitors: List[MonitorInfo] = Field(default_factory=list)


class DeviceRegisterPayload(BaseModel):
    device_id: str
    friendly_name: str
    hostname: str
    os_info: str
    agent_version: str
    screen_width: int
    screen_height: int
    capabilities: DeviceCapabilities


class DeviceRegister(OrbitMessage):
    type: Literal[MessageType.DEVICE_REGISTER] = MessageType.DEVICE_REGISTER
    payload: DeviceRegisterPayload


class DeviceInfo(BaseModel):
    """Snapshot sent in device-list responses."""
    device_id: str
    friendly_name: str
    hostname: str
    os_info: str
    agent_version: str
    screen_width: int
    screen_height: int
    online: bool
    last_seen_ms: Optional[int] = None
    layout_x: Optional[float] = None
    layout_y: Optional[float] = None
    capabilities: Optional[DeviceCapabilities] = None


class DeviceList(OrbitMessage):
    type: Literal[MessageType.DEVICE_LIST] = MessageType.DEVICE_LIST
    devices: List[DeviceInfo]


class DeviceOnline(OrbitMessage):
    type: Literal[MessageType.DEVICE_ONLINE] = MessageType.DEVICE_ONLINE
    device_id: str


class DeviceOffline(OrbitMessage):
    type: Literal[MessageType.DEVICE_OFFLINE] = MessageType.DEVICE_OFFLINE
    device_id: str


class DeviceRevoked(OrbitMessage):
    type: Literal[MessageType.DEVICE_REVOKED] = MessageType.DEVICE_REVOKED
    device_id: str


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------

class SessionStart(OrbitMessage):
    type: Literal[MessageType.SESSION_START] = MessageType.SESSION_START
    target_device_id: str
    controller_session_token: str


class SessionEnd(OrbitMessage):
    type: Literal[MessageType.SESSION_END] = MessageType.SESSION_END
    target_device_id: str


class ActiveDevice(OrbitMessage):
    type: Literal[MessageType.ACTIVE_DEVICE] = MessageType.ACTIVE_DEVICE
    device_id: Optional[str]  # None = no active device


# ---------------------------------------------------------------------------
# Input — Pointer
# ---------------------------------------------------------------------------

class PointerMove(OrbitMessage):
    type: Literal[MessageType.POINTER_MOVE] = MessageType.POINTER_MOVE
    target_device_id: str
    dx: float   # Relative movement, pixels
    dy: float


class MouseDown(OrbitMessage):
    type: Literal[MessageType.MOUSE_DOWN] = MessageType.MOUSE_DOWN
    target_device_id: str
    button: MouseButton


class MouseUp(OrbitMessage):
    type: Literal[MessageType.MOUSE_UP] = MessageType.MOUSE_UP
    target_device_id: str
    button: MouseButton


class Scroll(OrbitMessage):
    type: Literal[MessageType.SCROLL] = MessageType.SCROLL
    target_device_id: str
    dx: float   # Horizontal scroll (positive = right)
    dy: float   # Vertical scroll (positive = down)


# ---------------------------------------------------------------------------
# Input — Keyboard
# ---------------------------------------------------------------------------

class KeyDown(OrbitMessage):
    type: Literal[MessageType.KEY_DOWN] = MessageType.KEY_DOWN
    target_device_id: str
    key: str        # Canonical key name, e.g. "ctrl", "a", "F5"
    code: Optional[str] = None


class KeyUp(OrbitMessage):
    type: Literal[MessageType.KEY_UP] = MessageType.KEY_UP
    target_device_id: str
    key: str
    code: Optional[str] = None


class TextInput(OrbitMessage):
    type: Literal[MessageType.TEXT_INPUT] = MessageType.TEXT_INPUT
    target_device_id: str
    text: str        # Unicode text chunk


class Shortcut(OrbitMessage):
    type: Literal[MessageType.SHORTCUT] = MessageType.SHORTCUT
    target_device_id: str
    keys: List[str]   # Ordered list, e.g. ["ctrl", "c"]


# ---------------------------------------------------------------------------
# Topology
# ---------------------------------------------------------------------------

class LayoutDevice(BaseModel):
    device_id: str
    x: float          # Virtual desktop X (logical pixels)
    y: float          # Virtual desktop Y
    width: float      # Logical screen width
    height: float     # Logical screen height


class TopologyUpdate(OrbitMessage):
    type: Literal[MessageType.TOPOLOGY_UPDATE] = MessageType.TOPOLOGY_UPDATE
    version: int
    layout: List[LayoutDevice]


class TopologyAck(OrbitMessage):
    type: Literal[MessageType.TOPOLOGY_ACK] = MessageType.TOPOLOGY_ACK
    version: int
    accepted: bool
    reason: Optional[str] = None


class CursorHandoff(OrbitMessage):
    type: Literal[MessageType.CURSOR_HANDOFF] = MessageType.CURSOR_HANDOFF
    from_device_id: str
    to_device_id: str
    cursor_x: float    # Target screen X (absolute, on destination device)
    cursor_y: float    # Target screen Y


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class Heartbeat(OrbitMessage):
    type: Literal[MessageType.HEARTBEAT] = MessageType.HEARTBEAT
    device_id: Optional[str] = None


class HeartbeatAck(OrbitMessage):
    type: Literal[MessageType.HEARTBEAT_ACK] = MessageType.HEARTBEAT_ACK


class LatencyPing(OrbitMessage):
    type: Literal[MessageType.LATENCY_PING] = MessageType.LATENCY_PING
    ping_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    sent_ms: int


class LatencyPong(OrbitMessage):
    type: Literal[MessageType.LATENCY_PONG] = MessageType.LATENCY_PONG
    ping_id: str
    sent_ms: int
    received_ms: int


# ---------------------------------------------------------------------------
# Errors & Diagnostics
# ---------------------------------------------------------------------------

class ErrorMessage(OrbitMessage):
    type: Literal[MessageType.ERROR] = MessageType.ERROR
    code: str
    message: str
    detail: Optional[Dict[str, Any]] = None


class DiagnosticPayload(BaseModel):
    level: str   # "debug" | "info" | "warning" | "error"
    component: str
    message: str
    data: Optional[Dict[str, Any]] = None


class Diagnostic(OrbitMessage):
    type: Literal[MessageType.DIAGNOSTIC] = MessageType.DIAGNOSTIC
    payload: DiagnosticPayload


class CapabilityNegotiation(OrbitMessage):
    type: Literal[MessageType.CAPABILITY_NEG] = MessageType.CAPABILITY_NEG
    role: ConnectionRole
    protocol_version: str = PROTOCOL_VERSION
    supported_message_types: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Union for discriminated deserialization
# ---------------------------------------------------------------------------

AnyOrbitMessage = Union[
    PairRequest, PairChallenge, PairResponse, PairSuccess, PairRejected,
    AuthRequest, AuthSuccess, AuthFailed,
    DeviceRegister, DeviceList, DeviceOnline, DeviceOffline, DeviceRevoked,
    SessionStart, SessionEnd, ActiveDevice,
    PointerMove, MouseDown, MouseUp, Scroll,
    KeyDown, KeyUp, TextInput, Shortcut,
    TopologyUpdate, TopologyAck, CursorHandoff,
    Heartbeat, HeartbeatAck, LatencyPing, LatencyPong,
    ErrorMessage, Diagnostic, CapabilityNegotiation,
]


def parse_message(data: Dict[str, Any]) -> AnyOrbitMessage:
    """Deserialize a raw dict into the appropriate typed message."""
    msg_type = data.get("type")
    type_map = {m.default: m for m in [
        PairRequest, PairChallenge, PairResponse, PairSuccess, PairRejected,
        AuthRequest, AuthSuccess, AuthFailed,
        DeviceRegister, DeviceList, DeviceOnline, DeviceOffline, DeviceRevoked,
        SessionStart, SessionEnd, ActiveDevice,
        PointerMove, MouseDown, MouseUp, Scroll,
        KeyDown, KeyUp, TextInput, Shortcut,
        TopologyUpdate, TopologyAck, CursorHandoff,
        Heartbeat, HeartbeatAck, LatencyPing, LatencyPong,
        ErrorMessage, Diagnostic, CapabilityNegotiation,
    ] for m in [getattr(m.model_fields.get("type"), None)] if m is not None}

    # Simple type-based dispatch
    _map: Dict[str, Any] = {
        MessageType.PAIR_REQUEST:    PairRequest,
        MessageType.PAIR_CHALLENGE:  PairChallenge,
        MessageType.PAIR_RESPONSE:   PairResponse,
        MessageType.PAIR_SUCCESS:    PairSuccess,
        MessageType.PAIR_REJECTED:   PairRejected,
        MessageType.AUTH_REQUEST:    AuthRequest,
        MessageType.AUTH_SUCCESS:    AuthSuccess,
        MessageType.AUTH_FAILED:     AuthFailed,
        MessageType.DEVICE_REGISTER: DeviceRegister,
        MessageType.DEVICE_LIST:     DeviceList,
        MessageType.DEVICE_ONLINE:   DeviceOnline,
        MessageType.DEVICE_OFFLINE:  DeviceOffline,
        MessageType.DEVICE_REVOKED:  DeviceRevoked,
        MessageType.SESSION_START:   SessionStart,
        MessageType.SESSION_END:     SessionEnd,
        MessageType.ACTIVE_DEVICE:   ActiveDevice,
        MessageType.POINTER_MOVE:    PointerMove,
        MessageType.MOUSE_DOWN:      MouseDown,
        MessageType.MOUSE_UP:        MouseUp,
        MessageType.SCROLL:          Scroll,
        MessageType.KEY_DOWN:        KeyDown,
        MessageType.KEY_UP:          KeyUp,
        MessageType.TEXT_INPUT:      TextInput,
        MessageType.SHORTCUT:        Shortcut,
        MessageType.TOPOLOGY_UPDATE: TopologyUpdate,
        MessageType.TOPOLOGY_ACK:    TopologyAck,
        MessageType.CURSOR_HANDOFF:  CursorHandoff,
        MessageType.HEARTBEAT:       Heartbeat,
        MessageType.HEARTBEAT_ACK:   HeartbeatAck,
        MessageType.LATENCY_PING:    LatencyPing,
        MessageType.LATENCY_PONG:    LatencyPong,
        MessageType.ERROR:           ErrorMessage,
        MessageType.DIAGNOSTIC:      Diagnostic,
        MessageType.CAPABILITY_NEG:  CapabilityNegotiation,
    }
    cls = _map.get(msg_type)
    if cls is None:
        raise ValueError(f"Unknown message type: {msg_type}")
    return cls.model_validate(data)
