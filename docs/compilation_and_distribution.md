# 📦 Compiling to .EXE & Windows Startup Agent

This guide explains how OmniControl compiles into a standalone `.exe` and runs as a background Windows System Tray agent with auto-start capability.

---

## 🔨 Compiling into a Standalone .EXE

OmniControl uses **PyInstaller** to package Python code, web assets, and native dependencies into a single portable binary.

### Method 1: Using the 1-Click Batch Script
Double-click:
```text
build_exe.bat
```

### Method 2: Running via Python
From a terminal in the project directory:
```bash
python build_exe.py
```

### What Happens During Build:
1. Verifies `PyInstaller` and dependencies.
2. Checks/generates the application icon (`static/icon.ico`).
3. Cleans previous `build/` and `dist/` folders.
4. Executes `OmniControl.spec`, bundling:
   - `static/` (HTML, CSS, JS, icons)
   - `backend/` (server, screen capture, input engine)
   - Hidden imports for `uvicorn`, `fastapi`, `websockets`, `mss`, `pystray`, `cv2`, `PIL`, `pycaw`, `comtypes`, `cryptography`.
5. Compiles with `console=False` (windowless GUI) for system tray operation.
6. Generates **`dist/OmniControl.exe`**.

---

## 🪟 Windows Background System Tray Agent

When launched (either via `dist/OmniControl.exe` or `python run_server.py --tray`), OmniControl runs as a background agent:

- **No CMD Window**: Does not clutter your taskbar with a command prompt window.
- **Notification Area Icon**: Shows an orbital neon cyan icon in the Windows taskbar system tray.
- **Context Menu Options**:
  - `📱 OmniControl: <IP>:<PORT>`: Status header showing active IP address.
  - `🌐 Open Web Remote in Browser`: Opens the web controller in your default browser.
  - `📷 Show QR Code & Connection Info`: Displays a popup window with the QR code and HTTPS/HTTP addresses.
  - `🚀 Start with Windows on Boot`: Checkable toggle for auto-starting on Windows restart.
  - `❌ Exit OmniControl`: Stops the servers and shuts down gracefully.

---

## 🚀 Setting Up Windows Auto-Start on Boot

OmniControl registers in the Windows Current User Run key:
```text
HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run
Key: OmniControl
```
This requires **no administrator privileges**.

### Ways to Toggle Auto-Start:

1. **From the System Tray**: Right-click the OmniControl tray icon and click **Start with Windows on Boot**. A checkmark indicates it is active.
2. **From the Phone Web App**: Tap the power button in the header bar of the phone web remote.
3. **Using Batch Scripts**:
   - Enable: Double-click [`enable_startup.bat`](../enable_startup.bat)
   - Disable: Double-click [`disable_startup.bat`](../disable_startup.bat)
4. **Command Line**:
   ```bash
   python -m backend.startup_manager --enable
   python -m backend.startup_manager --disable
   python -m backend.startup_manager --status
   ```
