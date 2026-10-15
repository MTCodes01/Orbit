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
- Virtual displ
<truncated 26945 bytes>
ested code generation step.
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