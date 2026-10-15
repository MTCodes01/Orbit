# 📱 OmniControl - Wireless Laptop Remote Control & Screen Mirror

Turn your smartphone into a wireless touchscreen monitor, trackpad, keyboard, Xbox 360 controller, presentation remote, and Bluetooth device manager for your laptop over Wi-Fi.

![OmniControl Banner](https://img.shields.io/badge/Platform-Windows%2010%2F11-00f0ff?style=for-the-badge&logo=windows)
![Screen Mirror](https://img.shields.io/badge/Screen%20Mirror-30%20FPS%20Touch-8b5cf6?style=for-the-badge)
![Latency](https://img.shields.io/badge/Latency-%3C15ms%20WebSocket-10b981?style=for-the-badge)
![Gamepad](https://img.shields.io/badge/Gamepad-Xbox%20360%20Virtual%20HID-3b82f6?style=for-the-badge)
![Executable](https://img.shields.io/badge/Package-Standalone%20.EXE-f59e0b?style=for-the-badge)
[![Documentation](https://img.shields.io/badge/Docs-View%20Documentation-00f0ff?style=for-the-badge&logo=gitbook)](docs/index.md)

---

> 📖 **Looking for in-depth documentation?** Check out the comprehensive **[Documentation Suite in /docs](docs/index.md)** covering [Getting Started](docs/getting_started.md), [Screen Mirroring & Touch](docs/screen_mirroring_and_touch.md), [Compiling & Distribution](docs/compilation_and_distribution.md), and [Architecture & APIs](docs/architecture_and_api.md).

---

## ⚡ Features

### 1. 🖥️ Live Interactive Screen Mirroring & Touchscreen
- **Real-Time Visual Feedback**: View your laptop screen in high definition on your phone screen with 25-30 FPS low-latency streaming.
- **Direct Touchscreen Mode**: Tap anywhere on your phone screen to tap directly at that exact point on your laptop!
  - **Tap**: Instant left-click at touch coordinate.
  - **Double-Tap**: Instant double-click to open files and folders.
  - **Long-Press (Hold)**: Right-click (Context Menu) with tactile haptic vibration.
  - **Touch & Drag**: Smoothly drag windows, files, and select text.
  - **2-Finger Scroll**: Swipe two fingers up/down to scroll web pages and documents.
- **Pointer Trackpad Mode**: Toggle between Direct Touchscreen and virtual relative cursor control.
- **Mobile Keyboard Integration**: Tap the `⌨️ Type` button to summon your phone's native keyboard and type directly into any active laptop window.
- **Quick Action Toolbar**: Instant buttons for `Left Click`, `Right Click`, `Middle Click`, `Drag Lock`, `Esc`, `Win`, `Alt+Tab`, `Show Desktop`, and `Undo`.
- **Quality Presets**: Switch between 30 FPS (HD), 25 FPS (Balanced), and 15 FPS (Battery Saver).
- **Fit & Fullscreen**: Expand to borderless fullscreen with pinch-to-fit display scaling.

### 2. 🪟 Windows Background Agent & Auto-Start on Boot
- **System Tray Agent**: Runs silently in the background in the Windows taskbar system tray.
- **Auto-Start on Boot**: One-click toggle in the system tray menu or web interface to launch OmniControl on Windows startup automatically so your phone can connect anytime without manually running scripts.
- **Instant QR Code Popup**: Right-click the system tray icon anytime and click **Show QR Code** to view connection details and local IP.
- **One-Click Web Launch**: Right-click tray menu to open the controller directly.

### 3. 📦 Standalone Windows Executable (.exe)
- **Zero Python Setup Required**: Compile into a single portable `.exe` using `build_exe.bat` or `python build_exe.py`.
- **Output Executable**: Placed in `dist/OmniControl.exe` ready to run on any Windows 10/11 laptop.

### 4. 🖱️ High-Precision Trackpad & Mouse
- **Multi-Touch Gestures**: 1-finger move, 1-finger tap, 2-finger right-click, 2-finger scroll.
- **Dedicated Scroll Wheel Strip** & Drag Lock latch.
- **Adjustable Sensitivity**: Live speed slider (0.5x to 3.0x).
- **Air Mouse (Gyro)**: Tilt phone in the air to guide the mouse pointer.

### 5. ⌨️ Keyboard & Windows Shortcuts
- **Live Text Typing & Dictation**: Phone keyboard with full Unicode support.
- **Modifier Keys**: `Ctrl`, `Alt`, `Shift`, `Win` toggle latches.
- **1-Tap Windows Hotkeys**: `Win + D`, `Alt + Tab`, `Win + Tab`, `Ctrl + C / V / Z`, `Alt + F4`, `PrtScn`.
- **Navigation & Function Keys**: Full Arrow keys, `Home`, `End`, `Page Up`, `Page Down`, and `F1`–`F12`.

### 6. 🎮 Virtual Game Controller (Xbox 360)
- **Dual Analog Thumbsticks**: WASD movement & Camera aim with elastic spring-return.
- **ABXY Face Buttons**, Bumpers (`LB`/`RB`), Triggers (`LT`/`RT`), and 4-way D-Pad.
- **Dual Engine**: Real Xbox 360 emulation via `ViGEmBus` or automatic keyboard/mouse fallback.

### 7. 🎧 Bluetooth & Audio Hub
- **Device Detection**: Detects connected Bluetooth speakers and headphones.
- **Master Volume Slider** & Quick Stepper Buttons (`-10%`, `-5%`, `+5%`, `+10%`).
- **Media Controls Deck**: Play / Pause, Next Track, Previous Track, Stop, Mute toggle.

### 8. 📽️ Presentation & Media Remote
- Giant touch targets for couch media playback and PowerPoint / Google Slides presentations (`F5`, `F11`, `B`, `Esc`).

---

## 🚀 Quick Start

### Option A: Run the Standalone .EXE
Double-click `dist\OmniControl.exe`!
The app will launch silently in your Windows System Tray and start the local server.

### Option B: Run from Source
```bash
python run_server.py
```
Or start silently in the system tray:
```bash
python run_server.py --tray
```

### Connect Your Phone
1. Connect your phone to the **same Wi-Fi network** (or laptop mobile hotspot).
2. Scan the QR code displayed in the terminal or click **Show QR Code** from the system tray icon.
3. Or open your phone's browser and go to:
   ```
   https://<YOUR-LAPTOP-IP>:8443   (Recommended: unlocks full sensor and screen features)
   http://<YOUR-LAPTOP-IP>:8000
   ```

---

## 🛠️ Compiling into .EXE

To rebuild the standalone executable:
1. Double-click `build_exe.bat`
   *(or run `python build_exe.py` in your terminal)*
2. The compiler will clean previous builds, package static files, bundle dependencies, and generate:
   ```
   dist/OmniControl.exe
   ```

---

## 🚀 Managing Windows Startup

- **From System Tray**: Right-click the OmniControl icon in the system tray and toggle **Start with Windows on Boot**.
- **From Phone Web App**: Tap the power button in the header bar to toggle startup.
- **From Command Line**:
  - Double-click `enable_startup.bat` to enable auto-start.
  - Double-click `disable_startup.bat` to disable auto-start.

---

## 🛠️ Project Structure

```
d:/Github/Orbit/
├── dist/
│   └── OmniControl.exe         # Compiled standalone Windows executable (.exe)
├── backend/
│   ├── screen_handler.py       # High-performance desktop screen capture & JPEG compression
│   ├── startup_manager.py      # Windows HKCU registry auto-start manager
│   ├── tray_agent.py           # Background system tray agent with QR dialog & menus
│   ├── input_handler.py        # Absolute cursor positioning, touch mapping & Win32 SendInput
│   ├── controller_handler.py   # Xbox 360 controller emulation via ViGEmBus & fallback
│   ├── bluetooth_handler.py    # Bluetooth device detection, Audio endpoints, Volume & Media
│   ├── cert_gen.py             # Automatic SSL certificate generation for HTTPS
│   └── server.py               # FastAPI server, /ws/screen stream, REST endpoints
├── static/
│   ├── index.html              # Mobile web app with Screen Mirror & Touch interface
│   ├── style.css               # Futuristic cyberpunk glassmorphic design system
│   ├── app.js                  # Direct touch controller, screen canvas renderer, WebSocket
│   ├── icon.ico                # App and System Tray icon
│   └── qr.png                  # Saved connection QR code
├── OmniControl.spec            # PyInstaller build specification
├── build_exe.py                # Automated executable compiler
├── build_exe.bat               # 1-click executable compiler batch file
├── enable_startup.bat          # 1-click Windows startup register script
├── disable_startup.bat         # 1-click Windows startup unregister script
├── run_server.py               # Launcher with CLI arguments (--tray, --startup)
└── requirements.txt            # Project dependencies
```
