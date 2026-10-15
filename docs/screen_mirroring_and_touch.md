# 🖥️ Screen Mirroring & Interactive Touch Guide

OmniControl allows you to turn your smartphone into a wireless touchscreen monitor for your Windows laptop. You can view your entire laptop screen in real time and interact with Windows applications directly using touch gestures.

---

## 🌟 Overview & Key Capabilities

- **Ultra-Low Latency Streaming**: Frames are captured at up to **30 FPS** and streamed via a dedicated binary WebSocket (`/ws/screen`).
- **Direct Touch Screen**: Tapping anywhere on your phone taps that exact pixel on your laptop.
- **Hardware Acceleration**: The mobile web app leverages `createImageBitmap` for off-thread GPU canvas rendering.
- **Background Desktop Attachment**: Automatically connects to the interactive Windows input desktop (`OpenInputDesktop` & `SetThreadDesktop`), ensuring capture continues even when the server runs in the background.

---

## 👆 Touch Gestures Reference

| Gesture | Action on Laptop | Feedback |
| :--- | :--- | :--- |
| **1-Finger Tap** | Left-click at touch coordinate | Cyan ripple ring + gentle haptic tick |
| **1-Finger Double-Tap** | Double-click (opens apps, files, folders) | Double ripple + dual haptic pulse |
| **Touch & Hold (450ms)** | Right-click (Context Menu) | Glowing ripple + strong haptic vibration |
| **Touch & Drag** | Drag windows, select text, or move icons | Real-time cursor tracking |
| **2-Finger Drag (Vertical)** | Scroll up / down through web pages and documents | Smooth proportional scrolling |

---

## 🕹️ Interaction Modes

In the **Screen** tab toolbar, you can switch between two interaction styles:

### 1. Direct Touch (Default)
Tapping on any button, icon, or window on your phone screen immediately moves the Windows cursor to that exact location and clicks it, behaving like a physical touchscreen laptop or tablet.

### 2. Pointer Mode
For users who prefer relative cursor movement over the live screen visual: moving your finger glides the cursor relative to its current position, and tapping clicks.

---

## ⌨️ Typing from Phone onto Laptop

In Screen mode, tap the glowing **`⌨️ Type`** button in the lower toolbar:
1. Your phone's native on-screen keyboard will open.
2. Any text, emojis, or speech-to-text dictation you enter is sent directly to the currently active window on your laptop via Win32 Unicode injection.
3. Common keys like `Backspace` and `Enter` work seamlessly.

---

## 🛠️ Screen Toolbar Controls

- **Display Selector (Multi-Monitor)**: In setups with multiple monitors or an external display, select which display to view and control:
  - `Display <N> (Primary)`: Your main laptop screen (selected by default).
  - `Display <N>`: External monitors (secondary displays).
  - `All Displays`: Combined virtual desktop spanning all connected monitors.
  - *All touch inputs dynamically translate to the exact virtual pixel coordinates of the chosen monitor.*
- **FPS & Latency Pill**: Displays live stream frame rate and network round-trip time.
- **Quality Selector**:
  - `30 FPS (HD)`: 0.85 scale, 65 JPEG quality for ultra-sharp visuals on fast 5GHz Wi-Fi.
  - `25 FPS (Normal)`: 0.75 scale, 55 JPEG quality (recommended balance).
  - `15 FPS (Saver)`: 0.50 scale, 40 JPEG quality for battery saving or crowded networks.
- **Fit / Fill Display Toggle**: Switches between aspect-ratio preserved scaling (`contain`) and full viewport fill (`cover`).
- **Expand Fullscreen**: Hides the browser chrome and enters native mobile fullscreen mode.
- **Quick Action Buttons**:
  - `Left Click`, `Right Click`, `Middle Click`
  - `Drag Lock` (latches mouse button for dragging complex selections)
  - `Esc`, `Win`, `Alt+Tab`, `Show Desktop (Win+D)`, `Undo (Ctrl+Z)`, `Enter`
