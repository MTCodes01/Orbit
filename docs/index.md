# 📖 OmniControl Documentation

Welcome to the **OmniControl** documentation! OmniControl turns any smartphone into an ultra-low latency wireless touchscreen monitor, trackpad, keyboard, Xbox 360 game controller, and media remote for Windows laptops and desktops over local Wi-Fi.

---

## 📚 Table of Contents

| Guide | Description |
| :--- | :--- |
| [🚀 Getting Started](getting_started.md) | How to run OmniControl via executable or Python source, connect your phone, and scan QR codes. |
| [🖥️ Screen Mirroring & Touch Guide](screen_mirroring_and_touch.md) | How to view your entire laptop screen on your phone and control it directly using touch gestures. |
| [🎮 Features & Controls Guide](features_guide.md) | Complete manual for Trackpad, Air Mouse, Keyboard hotkeys, Xbox 360 Gamepad, and Bluetooth Audio. |
| [📦 Compiling & Startup Agent](compilation_and_distribution.md) | Compiling into a standalone Windows `.exe` and running the background system tray agent on boot. |
| [🏗️ Architecture & Protocols](architecture_and_api.md) | System internals, WebSocket low-latency engine, REST API endpoints, and Win32 SendInput mechanics. |
| [❓ Troubleshooting & FAQ](troubleshooting.md) | Solutions for Wi-Fi firewall issues, HTTPS warnings, Xbox drivers, and mobile browser setups. |

---

## ⚡ Quick Links & One-Click Scripts

In the project root directory, you can run:

- **Run Server from Source**: `python run_server.py`
- **Run Standalone Executable**: [`dist/OmniControl.exe`](../dist/OmniControl.exe)
- **Run in Windows Tray (Background)**: `python run_server.py --tray`
- **Compile into .EXE**: Double-click [`build_exe.bat`](../build_exe.bat)
- **Enable Windows Auto-Start**: Double-click [`enable_startup.bat`](../enable_startup.bat)
- **Disable Windows Auto-Start**: Double-click [`disable_startup.bat`](../disable_startup.bat)
- **Install Xbox Gamepad Driver**: Right-click [`install_controller_driver.bat`](../install_controller_driver.bat) and Run as Administrator
