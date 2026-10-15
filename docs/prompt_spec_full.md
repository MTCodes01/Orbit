<USER_REQUEST>
# Orbit — Universal Multi-Laptop Control System

## 1. Project Overview

Build **Orbit**, a secure, low-latency, multi-device remote-control system that allows a user to control multiple independent laptops through a mobile-first Progressive Web App (PWA).

Orbit should make multiple laptops feel like a single, continuous virtual workstation. A phone acts as the universal input device, providing a trackpad, keyboard, mouse buttons, shortcuts, and multi-device navigation.

Every laptop runs a lightweight background agent distributed as a standalone Windows executable (`.exe`). The agent automatically connects to the backend, registers its device identity, and makes the laptop available in the mobile controller.

The user must be able to visually arrange laptops in a virtual display layout, similar to Windows Settings → System → Display → Rearrange your displays. The layout determines how cursor movement transitions between adjacent laptops.

This is a real, functional software project, not just a UI mockup.

### Core goals

- Control multiple Windows laptops from a phone.
- Use the phone's native keyboard for text entry.
- Support mouse movement, scrolling, dragging, and left/right/middle clicks.
- Automatically register and manage connected laptops.
- Package the laptop agent into a standalone `.exe`.
- Provide a Windows-style, editable multi-display layout.
- Implement seamless cursor handoff between adjacent laptop screens.
- Persist devices, settings, and layouts in a backend database.
- Prioritize low latency, reliability, and security.
- Support local-network operation first, with an architecture extensible to secure remote access.

## 2. System Architecture

Build three primary components.

### A. Orbit Mobile PWA

The user-facing controller, built with React and TypeScript.

Responsibilities:
- Trackpad and mouse input.
- Native phone keyboard integration.
- Keyboard shortcuts and special keys.
- Device selection and management.
- Virtual display layout editing.
- Connection status and diagnostics.
- Communication with the backend over WebSockets and HTTPS.

### B. Orbit Agent

A lightweight application running on each controlled laptop.

Responsibilities:
- Device pairing and registration.
- Secure authentication.
- Real-time communication with the backend.
- Mouse and keyboard input injection.
- Reporting screen dimensions and capabilities.
- Connection health and automatic reconnection.
- Background execution and optional startup at user login.
- Safe input-state cleanup and diagnostic logging.

The initial target is Windows 10 and Windows 11. Design the agent around platform-independent interfaces so Linux and macOS agents can be implemented later.

### C. Orbit Coordinator Backend

A centralized service built with FastAPI.

Responsibilities:
- Device identity and authentication.
- Pairing and registration.
- WebSocket connection management.
- Real-time input routing.
- Active-device coordination.
- Virtual display topology management.
- Database persistence.
- Connection health monitoring.
- Device and layout synchronization.
- Security enforcement and diagnostics.

The backend is the authoritative source for registered device identities and saved virtual display layouts.

## 3. Technology Stack

Use the following stack unless repository constraints justify a documented alternative.

### Frontend
- React
- TypeScript
- Vite
- React Router
- PWA support
- WebSockets
- Responsive CSS or a suitable component styling system

### Backend
- Python 3
- FastAPI
- Uvicorn
- Pydantic for request and event validation
- WebSockets
- SQLAlchemy or an equivalent maintainable persistence layer
- Alembic database migrations
- SQLite for initial development, with PostgreSQL compatibility for production

### Windows Agent
- Python 3
- PyInstaller or an equivalent executable packager
- Appropriate Windows native APIs for input injection
- A reliable asynchronous networking library
- Windows-supported secure credential storage
- System tray support for connection status and controls

### Testing and Tooling
- pytest for backend and agent tests
- Vitest and React Testing Library for frontend tests
- Playwright for browser-level testing where appropriate
- Ruff or equivalent Python linting
- ESLint and TypeScript checks
- Git-based incremental development

Keep dependencies minimal. Avoid unnecessary microservices, message brokers, or complex infrastructure in the initial version.

## 4. Orbit Mobile PWA — User Interface

Design a polished, dark, minimal interface that feels like a native remote-control application.

### Design principles

- Near-black and charcoal backgrounds.
- One restrained accent color.
- High-contrast text and controls.
- Compact status indicators.
- Rounded surfaces without excessive glassmorphism.
- Smooth, subtle animations.
- Large touch targets.
- Minimal visual clutter.
- Excellent responsiveness on mobile screens.
- Clear loading, connecting, offline, error, and empty states.

The trackpad must be the primary focus of the controller screen.

### Required screens

1. Onboarding and device pairing.
2. Connected-device dashboard.
3. Main trackpad controller.
4. Keyboard and shortcut controls.
5. Virtual display layout editor.
6. Device details and management.
7. Settings and diagnostics.

### Main controller layout

Include:
- A large trackpad surface.
- Dedicated left, right, and middle mouse buttons.
- A device selector.
- Connection and latency indicators.
- Keyboard/text-entry access.
- Quick shortcut buttons.
- Scroll and drag controls.
- An emergency-stop or disconnect control.

The UI must adapt to different mobile viewport sizes, orientations, and browser safe areas.

Do not include buttons that appear functional but have no implementation.

## 5. Trackpad and Mouse Input

Implement a touch-based trackpad that translates phone gestures into mouse events.

### Required behavior

- Single tap: left click.
- Two-finger tap: right click.
- Two-finger movement: scrolling.
- Pointer movement: relative cursor movement.
- Press-and-hold: configurable drag behavior.
- Dedicated left-click, right-click, and middle-click buttons.
- Adjustable pointer sensitivity.
- Adjustable acceleration.
- Configurable gesture thresholds.
- Reliable dragging and mouse-button state.
- Smooth pointer movement with low perceived latency.

Support multi-touch gestures using appropriate browser touch or pointer events.

Prevent unwanted browser scrolling, selection, zooming, and pull-to-refresh while interacting with the trackpad. Apply touch restrictions only to the intended controller surface, not the entire application.

Use appropriate batching or coalescing for high-frequency pointer events. Never coalesce away required mouse-button releases.

Handle interruptions such as:
- Browser losing focus.
- Phone locking.
- Network disconnection.
- Controller screen changes.
- Agent termination.

All held mouse buttons must be released safely when the control session ends.

## 6. Keyboard and Native Phone Keyboard

Allow users to type using the phone's built-in keyboard.

### Text entry

Implement a dedicated text-entry component that:
- Opens the native mobile keyboard when focused.
- Sends text to the selected laptop.
- Handles Unicode text where supported.
- Supports newlines, backspace, and deletion.
- Handles composition events for mobile input methods.
- Avoids sending duplicate characters.
- Does not steal focus unnecessarily during trackpad interaction.

Do not assume mobile browsers expose every key event. Use a text-input protocol for ordinary text and a separate key-event protocol for special keys.

### Special keys

Support:
- Ctrl
- Alt
- Shift
- Windows/Meta
- Escape
- Enter
- Tab
- Backspace
- Delete
- Arrow keys
- Home and End
- Page Up and Page Down
- F1–F12
- Insert
- Space
- Common navigation and editing keys

### Shortcut controls

Provide configurable shortcuts for:
- Ctrl+C
- Ctrl+V
- Ctrl+X
- Ctrl+Z
- Ctrl+A
- Alt+Tab
- Alt+F4
- Win+D
- Win+L
- Ctrl+Shift+Esc

Support modifier locking so the user can activate combinations without having to press all modifiers simultaneously.

Use explicit key-down and key-up messages. Provide a cleanup mechanism that releases held modifiers after interruption.

Document shortcuts that may be restricted by Windows or require special handling.

## 7. Orbit Windows Agent — Standalone EXE

The laptop agent is a core part of Orbit.

Build it so users can run a packaged `.exe` without installing Python or manually configuring a development environment.

### Packaging

Use PyInstaller or an equivalent tool to generate a distributable Windows executable.

Provide:
- A reproducible build script.
- Dependency bundling.
- Version information.
- Clear build instructions.
- Error logs and diagnostic mode.
- A version-checking mechanism.
- A documented update strategy.

Test the packaged executable on a clean Windows environment without Python installed.

### First-run behavior

When launched for the first time, the agent should:

1. Load any existing configuration.
2. Ask for the backend URL if it has not been configured.
3. Connect securely to the backend.
4. Begin a pairing flow.
5. Request approval through the authenticated PWA or use a short-lived pairing code.
6. Receive a unique device ID and credentials after successful pairing.
7. Store credentials securely.
8. Register the laptop with the backend.
9. Report device information and screen dimensions.
10. Appear automatically in the PWA's connected-device list.

Subsequent launches must reuse the existing device identity instead of creating duplicate database records.

### Device information

Report:
- Unique device ID.
- Friendly name.
- Hostname.
- Operating system.
- Agent version.
- Primary screen dimensions.
- Supported display capabilities.
- Supported input capabilities.
- Connection status.
- Last successful connection.

For multiple physical monitors connected to one laptop, report display information where supported. Keep the initial cursor-handoff model focused on the configured laptop-level display surface, and document any limitations around multiple local monitors.

### Background operation

Provide:
- Optional system tray icon.
- Connection status.
- Open-settings action.
- Reconnect action.
- Disconnect action.
- Exit action.
- Log access.
- Visible remote-control status.
- Optional startup at Windows user login.

Startup must be explicitly enabled by the user. Prefer a per-user startup mechanism that does not require administrator privileges.

Do not silently install persistence mechanisms or require elevated privileges without justification.

The agent must support graceful shutdown and release held keys and mouse buttons.

### Installation and removal

Initially provide a portable `.exe`.

Optionally provide an installer in a later phase for:
- Start menu shortcuts.
- Desktop shortcuts.
- Optional startup integration.
- Configuration preservation.
- Clean uninstallation.
- Version upgrades.

Provide a clear way to revoke the device's authorization and remove its registration.

## 8. Automatic Device Registration and Database

Implement reliable device registration and lifecycle management.

### Stable identity

Each successfully paired agent receives a unique device ID.

Never identify devices solely by hostname or IP address. Both can change.

### Device database model

Store at least:
- Device ID.
- Friendly name.
- Hostname.
- Operating system.
- Agent version.
- Screen dimensions and capabilities.
- Authentication or pairing status.
- Creation timestamp.
- Last-seen timestamp.
- Online/offline status.
- Last-known layout position.
- Device-specific configuration.

Store authentication secrets using appropriate security practices rather than plaintext credentials.

### Registration behavior

On every authenticated agent connection:
1. Validate device credentials.
2. Find the existing device record.
3. Update device metadata.
4. Update last-seen information.
5. Mark the device online.
6. Synchronize configuration and topology version.
7. Notify connected PWA clients.

Use an upsert or equivalent transaction-safe operation.

### Offline behavior

When an agent disconnects or its heartbeat expires:
- Mark it offline.
- Notify connected clients.
- Retain its database record.
- Preserve its layout position.
- Keep its friendly name and configuration.

When it reconnects, restore its saved configuration without duplicate registration.

Only remove a device when the user explicitly unpairs or deletes it.

Implement heartbeat monitoring and sensible connection timeouts.

## 9. Device Discovery and Pairing

Support easy pairing of new laptops.

### Initial deployment

Assume the phone and laptops are on the same LAN.

Provide:
- Manual backend URL configuration.
- Optional local-network discovery.
- QR-code or short-lived pairing-code flow.
- User approval for new devices.
- Clear connection diagnostics.
- Automatic reconnection.

Do not assume multicast or broadcast discovery is available on every Wi-Fi network.

Provide a reliable manual connection fallback.

If discovery finds an unknown agent, it must not automatically authorize remote control. Registration and authorization are separate operations.

### Future remote access

Design the network layer to support a private overlay network, such as Tailscale, or an authenticated relay.

Do not expose unauthenticated input-control services to the public internet.

Avoid hardcoding private IP addresses, credentials, or deployment-specific URLs.

## 10. Windows-Style Virtual Display Layout Editor

This is one of Orbit's defining features.

Implement an interactive layout editor inspired by Windows Settings → System → Display.

The editor represents each registered laptop as a draggable rectangle. Rectangle placement determines the virtual spatial relationship between laptops.

### Layout interface

Display:
- One rectangle for each registered laptop.
- A unique display number.
- Friendly device name.
- Screen resolution.
- Online/offline status.
- Selected-device highlighting.
- Visible neighboring boundaries.
- Zoom and pan controls.
- An Apply button.
- Cancel/discard changes.
- Reset layout.
- A way to inspect and edit display properties.

Use a canvas, SVG, or another suitable interactive rendering approach.

Users must be able to drag rectangles freely to create arrangements such as:

- A beside B.
- C above B.
- D below A.
- Partially overlapping display edges.

Do not force all displays into a horizontal row or a simple grid.

### Coordinate representation

Maintain two coordinate systems:

1. **Virtual desktop coordinates:** Actual logical position and dimensions of each laptop in the shared topology.
2. **Editor canvas coordinates:** Scaled and translated positions used for rendering and dragging rectangles in the UI.

Keep these systems separate.

The editor should scale rectangles proportionally to their screen dimensions, while keeping labels and controls readable.

Support different resolutions and aspect ratios.

Store each display's logical width, height, virtual X position, virtual Y position, and any required coordinate-scale information.

If the agent can report additional monitor information, model it explicitly rather than inferring it from the rendered rectangle.

### Layout editing workflow

1. Load the latest saved layout.
2. Allow the user to rearrange displays.
3. Preview changes locally.
4. Validate the proposed topology.
5. Apply the changes.
6. Save the layout transactionally in the backend.
7. Update the authoritative topology version.
8. Notify relevant connected agents and PWA clients.
9. Recalculate display adjacency and handoff boundaries.
10. Confirm the applied layout in the UI.

Provide clear handling for conflicts, validation failures, and disconnected devices.

### Offline devices

Offline laptops must remain visible in the layout with an offline indicator.

Their positions must be preserved.

When they reconnect, restore their existing position rather than inserting duplicate displays.

## 11. Virtual Coordinate Mapping and Cursor Handoff

Implement the topology engine independently from the UI.

The engine must calculate:
- Which displays are adjacent.
- Which edges overlap.
- Which transitions are valid.
- Coordinate transformations between displays.
- Cursor handoff targets.
- Behavior when neighboring displays are offline.

### Cursor handoff

Example:

Laptop A is placed left of Laptop B.

When the cursor reaches the configured right edge of Laptop A:
1. Detect whether Laptop B occupies the relevant neighboring edge.
2. Calculate the cursor's position relative to the overlap.
3. Transfer active control to Laptop B.
4. Translate the cursor position into Laptop B's screen coordinate system.
5. Continue sending pointer movement to Laptop B.
6. Support reverse handoff when moving back across the boundary.

Support all four directions:
- Left to right.
- Right to left.
- Top to bottom.
- Bottom to top.

Support partial edge overlap, different screen resolutions, and configurable edge sensitivity.

Prevent accidental repeated switching at a boundary through suitable transition state and hysteresis.

If the destination is offline:
- Do not route input to it.
- Keep the controller in a defined, recoverable state.
- Do not leave any key or button held.
- Provide a clear indication that handoff was unavailable.

### Important operating-system distinction

Orbit coordinates control across independent operating-system desktops. It does not automatically create a native extended Windows desktop.

Implement and describe the limitations accurately. Do not claim that application windows, keyboard focus, clipboard contents, or operating-system sessions transfer automatically between laptops.

Treat seamless input handoff as the initial objective.

## 12. Backend APIs and WebSocket Protocol

Define a versioned, validated protocol shared by the PWA, backend, and agents.

### Required message types

Include:
- Device pairing.
- Device authentication.
- Device registration.
- Device metadata updates.
- Heartbeats.
- Input session establishment.
- Pointer movement.
- Mouse-button down/up.
- Scroll events.
- Keyboard key-down/key-up.
- Text input.
- Shortcut commands.
- Active-device changes.
- Topology updates.
- Device online/offline updates.
- Latency measurements.
- Errors and diagnostics.
- Protocol and capability negotiation.

Each message must include the required metadata, such as:
- Protocol version.
- Message type.
- Session ID.
- Target device ID.
- Sequence number when necessary.
- Validated payload.

Use Pydantic or an equivalent schema-validation layer.

### Real-time behavior

Optimize pointer movement for low latency.

Coalesce redundant pointer movement where appropriate, but preserve event ordering where required.

Never silently drop essential key-up or mouse-button-up events.

Use acknowledgments or reconciliation for critical state transitions without introducing unnecessary round trips for every movement event.

Handle reconnects, stale sessions, duplicate messages, and invalid targets safely.

### REST endpoints

Define documented endpoints for:
- Health checks.
- Device listing.
- Device details.
- Device pairing.
- Device unpairing.
- Device renaming.
- Layout retrieval.
- Layout updates.
- Agent configuration.
- Diagnostics where appropriate.

Use proper authentication and authorization for protected endpoints.

## 13. Security Model

Treat remote input as a privileged capability.

Implement:
- Secure device pairing.
- Per-device authentication.
- User-approved authorization.
- Short-lived pairing codes.
- Credential rotation or revocation.
- Input authorization per active session.
- Rate limiting for pairing and authentication.
- Schema validation.
- Safe error responses.
- Protection against unauthorized cross-device control.
- Secure credential storage.
- An emergency-stop control.
- Clear indication of active remote control.
- Device revocation and unpairing.

Use TLS/WSS where appropriate, especially for remote access.

Do not implement arbitrary shell execution or unrestricted remote command execution.

Do not expose sensitive credentials in logs.

Use the principle of least privilege. Document any Windows permission limitations affecting particular shortcuts or elevated applications.

## 14. Connection Health and Recovery

Implement a resilient connection lifecycle.

The PWA and agent should:
- Detect disconnected WebSockets.
- Reconnect with bounded exponential backoff and jitter.
- Resume authenticated sessions where appropriate.
- Revalidate authorization after reconnecting.
- Exchange heartbeats.
- Report latency and errors.
- Synchronize the latest configuration.
- Recover the active-device state.
- Release held input state when session ownership is lost.

Distinguish between:
- Agent process stopped.
- Laptop offline.
- Network disconnected.
- Backend unavailable.
- Authentication expired.
- Device revoked.
- Destination unavailable.

The UI must show useful, actionable connection states rather than a generic disconnected indicator.

## 15. Performance Requirements

Optimize for a responsive remote-control experience.

Priorities:
- Low perceived pointer latency.
- Accurate relative pointer movement.
- Smooth scrolling.
- Reliable key state.
- Responsive gestures.
- Fast device switching.
- Minimal idle resource usage.
- Stable reconnection.
- Efficient database access.
- No blocking operations in real-time handlers.

Keep high-frequency movement events out of persistent database writes.

Use profiling and measurements before introducing complex optimization.

Test on actual hardware rather than relying exclusively on simulated performance.

## 16. Testing Strategy

### Backend tests
- Pairing and authorization.
- Device registration and idempotent updates.
- Online/offline transitions.
- Device revocation.
- Input routing.
- WebSocket reconnection.
- Layout persistence.
- Concurrent layout updates.
- Invalid message rejection.

### Topology tests
- Horizontal arrangements.
- Vertical arrangements.
- Partial edge overlap.
- Different screen resolutions.
- Coordinate scaling.
- Boundary transitions.
- Offline neighboring devices.
- Invalid or disconnected arrangements.
- Repeated edge-crossing behavior.

### Agent tests
- Registration and reconnect.
- Credential persistence.
- Input injection.
- Key-down/key-up consistency.
- Mouse-button cleanup.
- Network loss.
- Agent shutdown.
- Configuration recovery.

### Frontend tests
- Trackpad gestures.
- Keyboard controls.
- Device selection.
- Connection indicators.
- Layout dragging.
- Zoom and pan.
- Layout save/discard.
- Offline-device rendering.
- API errors and reconnection.

### End-to-end tests

Provide instructions for testing:
1. One Windows laptop and one phone.
2. Two Windows laptops and one phone.
3. Different screen resolutions.
4. Device disconnection during input.
5. Backend restart.
6. Agent restart.
7. Layout changes and persistence.
8. Pairing, unpairing, and re-pairing.

Support simulated agents so most development can happen without multiple physical computers.

## 17. Repository Structure

Use a clear monorepo structure similar to:

orbit/
- frontend/
  - src/
  - public/
  - tests/
- backend/
  - app/
    - api/
    - auth/
    - devices/
    - connections/
    - routing/
    - topology/
    - database/
    - models/
    - schemas/
    - services/
  - migrations/
  - tests/
- agent/
  - orbit_agent/
    - networking/
    - authentication/
    - input/
    - display/
    - configuration/
    - tray/
    - diagnostics/
  - scripts/
  - tests/
- protocol/
  - schemas/
  - documentation/
- docs/
  - architecture.md
  - setup.md
  - security.md
  - protocol.md
  - troubleshooting.md
- scripts/
- README.md
- .gitignore

Adjust the structure when necessary, but keep component boundaries clear.

Do not duplicate protocol definitions unnecessarily. Prefer shared schemas or generated definitions where appropriate.

## 18. Development and Deployment

Provide a straightforward local development environment.

Document:
- Required development tools.
- Environment variables.
- Backend installation.
- Database initialization and migrations.
- Frontend development server.
- Agent configuration.
- Executable build commands.
- LAN connection setup.
- Firewall requirements.
- Device pairing.
- Troubleshooting.
- Production deployment.
- Secure remote-access options.

Provide an example environment file without real secrets.

Add suitable development scripts to run the backend and frontend conveniently.

The agent must be buildable independently from the frontend and backend.

Do not require Docker on the Windows laptop just to run the packaged agent.

For production, provide deployment guidance for the backend and a secure method for the PWA to connect to it.

## 19. Implementation Workflow

Develop Orbit in small, verified phases.

### Phase 1 — Architecture and protocol

- Inspect the repository.
- Document component responsibilities.
- Define device identity and pairing.
- Define the versioned event protocol.
- Establish the database schema.
- Set up the development environment.

### Phase 2 — Single-laptop control

- Build the FastAPI backend.
- Implement the Windows agent.
- Implement the PWA trackpad.
- Implement mouse buttons and scrolling.
- Implement text entry and special keys.
- Establish secure pairing.
- Verify actual input on Windows.

### Phase 3 — Standalone executable

- Package the agent into a standalone `.exe`.
- Test it without Python installed.
- Implement persistent device identity.
- Add a tray interface and diagnostics.
- Add optional startup at user login.
- Verify registration and reconnect behavior.

### Phase 4 — Multi-device coordination

- Support multiple paired agents.
- Add device selection.
- Implement online/offline tracking.
- Add connection health indicators.
- Implement reliable input routing.
- Add device renaming and revocation.

### Phase 5 — Virtual display layout editor

- Implement the topology data model.
- Build the draggable display-layout UI.
- Support different resolutions and positions.
- Implement saving, validation, and versioning.
- Preserve layouts for offline devices.
- Add conflict handling.

### Phase 6 — Seamless cursor handoff

- Implement edge adjacency calculations.
- Implement coordinate transformations.
- Implement cursor handoff in every supported direction.
- Handle partial overlaps and offline destinations.
- Test transitions on real laptops.
- Tune the experience based on measurements.

### Phase 7 — Hardening and release

- Complete security checks.
- Improve reconnection and input-state recovery.
- Add automated and manual tests.
- Profile performance.
- Finalize packaging and documentation.
- Prepare a release checklist.

## 20. Rules for the Coding Agent

1. Inspect the existing repository before creating or changing files.
2. Preserve existing working code and conventions unless a change is necessary.
3. Start by presenting a concise architecture and implementation checklist.
4. Then implement Phase 1 and continue through the phases incrementally.
5. Make actual repository changes rather than responding with code snippets alone.
6. Run tests and relevant build commands after implementing each phase.
7. Fix discovered errors before declaring a phase complete.
8. Do not claim functionality is implemented unless it works.
9. Do not replace real behavior with mock data or fake success responses.
10. Avoid leaving core functionality as TODOs or pseudocode.
11. Document platform limitations and justified deviations.
12. Keep credentials and secrets out of source control.
13. Keep the backend, agent, and frontend independently testable.
14. Update the README and implementation checklist as functionality changes.
15. Use stable interfaces between components.
16. Avoid unnecessary abstractions and infrastructure.
17. Do not implement every phase in one enormous, untested code generation step.
18. If a decision materially affects security, architecture, or operating-system compatibility, explain the trade-offs and choose a sensible default when possible.

At the end of every phase, report:
- Functionality completed.
- Files created or modified.
- Tests and build commands executed.
- Test results.
- Known limitations.
- Remaining requirements.
- The next implementation step.

## Final Acceptance Criteria

Orbit is ready for its initial release when:

- The PWA can control one Windows laptop.
- The phone's native keyboard can send text.
- Mouse movement, scrolling, dragging, and all three mouse buttons work.
- Special keys and supported shortcuts work.
- The Windows agent runs as a standalone `.exe`.
- A newly paired agent registers automatically in the backend database.
- Reconnecting agents reuse their existing identity.
- Multiple laptops can be connected simultaneously.
- Devices can be renamed, disconnected, and revoked.
- The PWA contains an editable, Windows-style virtual display layout.
- Layout positions persist across restarts and disconnections.
- Cursor handoff follows the configured topology.
- Input states recover safely after network interruptions.
- Unauthorized devices cannot control registered laptops.
- The system has automated tests and documented end-to-end setup instructions.

**Begin now:** Inspect the repository, establish the architecture, define the shared protocol, and implement Phase 1. Continue incrementally toward a functional Orbit release, verifying each stage rather than merely describing what should be built.
</USER_REQUEST>
<ADDITIONAL_METADATA>
The current local time is: 2026-10-15T00:03:38+05:30.
</ADDITIONAL_METADATA>
<USER_SETTINGS_CHANGE>
The user changed setting `Model Selection` from None to Claude Sonnet 4.6 (Thinking). No need to comment on this change if the user doesn't ask about it. If reporting what model you are, please use a human readable name instead of the exact string.
</USER_SETTINGS_CHANGE>