# 🎮 Features & Controls Guide

OmniControl integrates six dedicated control modes into a sleek, mobile-first web application.

---

## 1. 🖱️ High-Precision Trackpad & Air Mouse

### Multi-Touch Gestures
- **1-Finger Move**: Fluid cursor navigation with subpixel accumulator and adjustable acceleration.
- **1-Finger Tap**: Left Click.
- **2-Finger Tap**: Right Click.
- **2-Finger Scroll**: Vertical and horizontal content scrolling.
- **Scroll Wheel Column**: Dedicated right-edge touch strip for continuous vertical scrolling.
- **Sensitivity Slider**: Live adjustment from `0.5x` to `3.0x`.
- **Drag Lock Latch**: One-tap toggle to latch the left mouse button for dragging windows and files without holding your finger down.

### 🎯 Air Mouse (Gyroscope Motion)
- Tilt and wave your phone in the air to guide the mouse pointer across the screen.
- Supported on mobile browsers with orientation sensor access (via HTTPS port 8443).
- **Profiles**: *Smooth*, *Balanced*, *Tactical / Twitch*.
- **3D Reticle Radar**: Visual horizon feedback on your phone display.

---

## 2. ⌨️ Keyboard & Windows Shortcuts

- **Native Phone Keyboard Typing**: Type text, emojis, and use voice-to-text dictation with full Unicode support.
- **Modifier Keys**: `Ctrl`, `Alt`, `Shift`, and `Win` keys with latching active states.
- **1-Tap Windows Hotkeys**:
  - `Win + D`: Show / Hide Desktop
  - `Alt + Tab`: Switch active applications
  - `Win + Tab`: Windows Task View
  - `Ctrl + C` / `Ctrl + V`: Copy and Paste
  - `Ctrl + Z`: Undo
  - `Alt + F4`: Close active window
  - `PrtScn`: Capture screenshot
- **Navigation Cluster**: Full arrow pad (`Up`, `Down`, `Left`, `Right`), `Home`, `End`, `Page Up`, `Page Down`.
- **Function Keys Drawer**: Expandable tray with `F1` through `F12`.

---

## 3. 🎮 Virtual Game Controller (Xbox 360)

OmniControl provides a full Xbox 360 gamepad controller layout:

- **Dual Analog Thumbsticks**:
  - Left Stick (WASD movement) & Right Stick (Camera aim/look).
  - Dynamic touch origin with normalized vector clamping (`-1.0` to `+1.0`) and elastic spring-return.
- **ABXY Face Buttons**: Color-coded buttons with glowing active states.
- **Bumpers & Triggers**: `LB`, `RB`, `LT`, `RT`.
- **D-Pad**: 4-way tactical directional pad.
- **Dual Engine Architecture**:
  - **Native Xbox 360 Gamepad**: Powered by the `ViGEmBus` driver (recognized natively by Steam, PC games, and emulators).
  - **Zero-Config Fallback**: If drivers are not installed, automatically translates gamepad inputs into keyboard and mouse events so gameplay is never interrupted.

---

## 4. 🎧 Bluetooth & Audio Hub

- **Endpoint Detection**: Discovers connected Bluetooth audio devices (speakers, wireless earbuds, headsets).
- **Master Volume Slider**: Bidirectional synchronization between laptop and phone (0% to 100%).
- **Quick Steppers**: `-10%`, `-5%`, `+5%`, `+10%`.
- **Mute / Unmute Toggle**: Instant system mute with animated status icon.
- **Media Deck**: Play/Pause, Next Track, Previous Track, Stop.

---

## 5. 📽️ Presentation & Living Room Remote

- **Living Room Couch Browsing**: Giant touch targets designed for couch media playback.
- **Presentation Mode**: Full support for PowerPoint, Google Slides, and PDF presentations:
  - **Start Slideshow**: `F5`
  - **Fullscreen**: `F11`
  - **Black Screen**: `B`
  - **Exit**: `Escape`
  - Giant **Previous** / **Play** / **Next** buttons.
