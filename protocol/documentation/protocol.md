# Orbit Protocol Documentation

## Version: 1.0.0

All WebSocket messages share a common envelope:

```json
{
  "protocol_version": "1.0.0",
  "type": "<MessageType>",
  "session_id": "<optional string>",
  "sequence": "<optional int>",
  "timestamp_ms": "<optional unix ms>"
}
```

## Connection Roles

| Role       | Description                    |
|------------|--------------------------------|
| controller | PWA (mobile phone browser)     |
| agent      | Windows laptop agent process   |

## Message Flow

### Pairing a new agent
```
Agent → Backend: pair_request  { pairing_code, device_name, hostname, ... }
Backend → PWA:   pair_challenge { challenge_token, expires_in_seconds }
PWA → Backend:   pair_response  { challenge_token, approved: true }
Backend → Agent: pair_success   { device_id, device_secret }
```

### Authenticating a known agent
```
Agent → Backend: auth_request  { device_id, device_secret }
Backend → Agent: auth_success  { session_token }
Agent → Backend: device_register { full device info and capabilities }
Backend → PWA:   device_online { device_id }
Backend → all:   device_list   [ updated list ]
```

### Controlling a laptop
```
PWA → Backend: session_start    { target_device_id }
Backend → Agent: session_start
PWA → Backend: pointer_move / mouse_down / mouse_up / scroll / key_down / key_up / text_input
Backend → Agent: (same events, forwarded)
PWA → Backend: session_end
Backend → Agent: session_end    (agent cleans up held key/button state)
```

### Heartbeat
```
Agent  → Backend: heartbeat { device_id }
Backend → Agent: heartbeat_ack
```

## Key Naming Convention

Special keys use lowercase strings:
- Modifier keys: `ctrl`, `shift`, `alt`, `meta` (Windows key)
- Navigation: `escape`, `enter`, `tab`, `backspace`, `delete`
- Arrows: `arrowleft`, `arrowright`, `arrowup`, `arrowdown`
- Function: `F1`–`F12`
- Other: `home`, `end`, `pageup`, `pagedown`, `insert`, `space`

Regular printable characters use their single Unicode character (e.g., `"a"`, `"A"`, `"5"`, `"@"`).

## Error Codes

| Code                  | Description                           |
|-----------------------|---------------------------------------|
| `auth_failed`         | Invalid device_id or device_secret    |
| `session_not_found`   | No active session for target device   |
| `device_not_found`    | Target device_id unknown              |
| `device_offline`      | Target device is disconnected         |
| `device_revoked`      | Device authorization revoked          |
| `invalid_message`     | Schema validation failure             |
| `pairing_expired`     | Pairing code no longer valid          |
| `pairing_rejected`    | User rejected pairing request         |
| `rate_limited`        | Too many requests                     |
| `unauthorized`        | Missing or invalid session token      |
