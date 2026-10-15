# 📱 OmniControl - Wireless Laptop Remote Control Server

Turn your smartphone into a wireless trackpad, keyboard, Xbox 360 controller, presentation remote, and Bluetooth device manager for your laptop over Wi-Fi.

![OmniControl Banner](https://img.shields.io/badge/Platform-Windows%2010%2F11-00f0ff?style=for-the-badge&logo=windows)
![Latency](https://img.shields.io/badge/Latency-%3C10ms%20WebSocket-10b981?style=for-the-badge)
![Controller](https://img.shields.io/badge/Gamepad-Xbox%20360%20Virtual%20HID-3b82f6?style=for-the-badge)

---

## ⚡ Features

### 1. 🖱️ High-Precision Trackpad & Mouse
- **Multi-Touch Gestures**:
  - 1-Finger Move: Ultra-smooth cursor tracking.
  - 1-Finger Tap: Left Click.
  - 1-Finger Double Tap: Double Click.
  - 2-Finger Tap: Right Click (Context Menu).
  - 2-Finger Drag: Smooth vertical & horizontal scrolling.
- **Dedicated Scroll Wheel Strip**: Fast right-edge scroll column.
- **Physical Buttons**: Discrete Left, Middle, and Right mouse buttons.
- **Drag Lock**: One-touch latch for dragging windows, folders, and files.
- **Adjustable Sensitivity**: Live speed slider (0.5x to 3.0x).
- **Air Mouse (Gyro)**: Tilt phone in the air to guide the mouse pointer.

### 2. ⌨️ Keyboard & Windows Shortcuts
- **Live Text Typing & Dictation**: Use your phone's native keyboard, speech-to-text dictation, and autocomplete to send text directly to your laptop with full Unicode support.
- **Modifier Keys**: `Ctrl`, `Alt`, `Shift`, `Win` toggle latches.
- **1-Tap Windows Hotkeys**:
  - `Win + D` (Show / Hide Desktop)
  - `Alt + Tab` (Switch active applications)
  - `Win + Tab` (Task View)
  - `Ctrl + C`, `Ctrl + V`, `Ctrl + Z` (Copy, Paste, Undo)
  - `Alt + F4` (Close window)
  - `PrtScn` (Screenshot)
- **Arrow Pad & Navigation**: Full Arrow keys, `Home`, `End`, `Page Up`, `Page Down`.
- **Function Keys**: Expandable drawer with `F1` through `F12`.

### 3. 🎮 Virtual Game Controller (Xbox 360)
- **Dual Analog Thumbsticks**:
  - Left Stick (WASD movement) & Right Stick (Camera aim/look).
  - Dynamic touch origin with normalized vector clamping (-1.0 to 1.0) and elastic spring-return.
- **ABXY Face Buttons**: Xbox styled color-coded buttons with glowing active states.
- **Bumpers & Triggers**: `LB`, `RB`, `LT`, `RT`.
- **D-Pad**: 4-way tactical cross.
- **Dual Engine Architecture**:
  - **Native Xbox 360 Gamepad**: Powered by `ViGEmBus` driver (compatible with Steam, emulators, and all PC games).
  - **Zero-Config Fallback**: If drivers are not installed, automatically operates in keyboard/mouse emulation mode without interrupting your gameplay.

### 4. 🎧 Bluetooth & Audio Hub
- **Live Audio Endpoint Detection**: Automatically discovers your laptop's connected Bluetooth audio devices (e.g. *Stone 120, Mivi DuoPods, Airdopes, M19, Toad One*).
- **Master Volume Slider**: Real-time bidirectional volume synchronization (0% to 100%).
- **Quick Stepper Buttons**: `-10%`, `-5%`, `+5%`, `+10%`.
- **Mute / Unmute Toggle**: Instant mute with animated speaker icon.
- **Media Controls Deck**: Play / Pause, Next Track, Previous Track, Stop.

### 5. 📽️ Presentation & Living Room Remote
- **Giant Touch Targets**: Designed for couch browsing or stage presentations.
- **PowerPoint & Google Slides Controls**: Next slide, Previous slide, Start Slideshow (`F5`), Black Screen (`B`), Fullscreen (`F11`).

---

## 🚀 Quick Start

### 1. Launch the Server
Open a terminal in this directory and run:
```bash
python run_server.py
```

The server will automatically:
1. Detect your laptop's local Wi-Fi IP (e.g., `192.168.29.149:8000`).
2. Generate an **ASCII QR Code** directly in your terminal.
3. Start the low-latency WebSocket engine on `0.0.0.0:8000`.

### 2. Connect Your Phone
1. Connect your phone to the **same Wi-Fi network** (or connect your laptop to your phone's Wi-Fi Hotspot).
2. Open your phone camera or QR scanner and scan the terminal QR code.
3. *Alternatively*, open your mobile browser (Chrome, Safari) and navigate to:
   ```
   http://<YOUR-LAPTOP-IP>:8000
   ```
   *(e.g., `http://192.168.29.149:8000`)*

---

## 🎮 Virtual Xbox 360 Controller Setup (Optional)

OmniControl supports native virtual Xbox 360 controller emulation. To enable direct game recognition in Steam and PC games:
1. Right-click `install_controller_driver.bat` and select **Run as Administrator**.
2. Complete the quick ViGEmBus installer.
3. In the phone app, tap **Driver Info** > **Re-detect Controller Driver**.

---

## 🛠️ Project Structure

```
d:/VScode/Control/
├── backend/
│   ├── input_handler.py        # Win32 SendInput (Mouse, Keyboard, Media keys, Unicode typing)
│   ├── controller_handler.py   # Xbox 360 controller emulation via vgamepad & fallback
│   ├── bluetooth_handler.py    # Bluetooth device detection, Audio endpoints, Volume & Media
│   └── server.py               # FastAPI application, WebSockets router, REST API
├── static/
│   ├── index.html              # Modern, sleek mobile-first web app
│   ├── style.css               # Futuristic cyberpunk glassmorphic design system
│   └── app.js                  # Touchpad gestures, virtual sticks, WebSocket client, haptics
├── vgamepad/                   # Included vgamepad package
├── install_controller_driver.bat # 1-click installer for ViGEmBus driver (admin prompt)
├── run_server.py               # Main launcher with QR code generator and local IP detection
└── requirements.txt            # Dependencies
```
