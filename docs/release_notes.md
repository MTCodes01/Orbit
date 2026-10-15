# 🪐 Orbit v1.0.0 Release Notes & User Manual

## 1. Executive Summary

**Orbit** is a universal multi-device remote-control system transforming your smartphone into a virtual workstation controller for multiple Windows laptops simultaneously.

With Orbit, you can:
- Glide between laptops seamlessly by simply moving your cursor across adjacent screen borders.
- Use your phone's touch trackpad with acceleration, 2-finger scroll, physical-style mouse buttons, and tap-and-hold drag.
- Type smoothly using your phone's native keyboard directly into active Windows applications.
- Arrange your computers on a 2D canvas exactly like Windows Display Settings.
- Run the laptop agent as a single, zero-dependency Windows executable (`orbit-agent.exe`).

---

## 2. Quick Setup & First Run

### Step 1: Start the Coordinator Backend
The backend acts as the lightweight central coordinator for pairing, topology, and low-latency input streaming:

```bash
cd backend
.venv\Scripts\activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

> **Tip:** You can also run `scripts\start_backend.bat` directly!

---

### Step 2: Open Orbit on Your Phone (Controller)
1. Ensure your phone is connected to the same Wi-Fi network as the coordinator machine.
2. Open your mobile browser (Safari on iOS, Chrome on Android).
3. Navigate to: `http://<COORDINATOR_IP>:5173` (or port 8000 if serving production PWA assets).
4. Tap **"Install"** or **"Add to Home Screen"** to launch Orbit in full-screen PWA mode.

---

### Step 3: Run the Agent on Each Windows Laptop
Copy `agent/dist/orbit-agent.exe` to each Windows 10/11 laptop you wish to control:

1. Double-click `orbit-agent.exe`.
2. When prompted on first run, enter the Coordinator Backend URL (e.g. `http://192.168.1.100:8000`).
3. On your phone, tap the **"Pair"** tab to view your 6-digit pairing code.
4. Enter the 6-digit code in the agent prompt.
5. In your phone's PWA, tap **"Approve"** on the incoming request.
6. The laptop is immediately paired! Its credentials are saved securely in the Windows Credential Manager.

---

### Step 4: Arrange Displays & Start Controlling
1. In the mobile PWA, navigate to the **"Layout"** tab.
2. Drag each laptop rectangle into its real-world physical position (e.g. Laptop 1 on the left, Laptop 2 on the right, or stacked vertically).
3. Tap **"Apply"** to save your layout.
4. Go to the **"Trackpad"** tab:
   - Move your finger on the trackpad to control the active laptop.
   - When the cursor reaches the boundary between Laptop 1 and Laptop 2, it seamlessly transitions into the neighboring screen!
   - Tap the Quick Switch bar at any time to instantly jump between laptops.

---

## 3. System Tray & Autostart

The agent runs unobtrusively in your Windows Notification Area (System Tray):
- **Green circle**: Connected and actively accepting input.
- **Amber circle**: Reconnecting or authenticating.
- **Red circle**: Disconnected or offline.

**Right-click the tray icon to:**
- Toggle **"Start with Windows"** (enables automatic startup on Windows login without admin elevation).
- View **"Show Config & Logs"** to inspect rotating diagnostics logs.
- Trigger **"Reconnect"** or **"Disconnect"**.
- Perform a clean **"Exit"** (which automatically releases all held keys and mouse buttons).

---

## 4. Security & Safety Guarantees

- **HMAC / PBKDF2 Mutual Authentication**: Secret tokens are hashed with PBKDF2-HMAC-SHA256 and never logged or stored in plaintext.
- **Ephemeral Pairing Challenges**: 6-digit pairing codes expire after 120 seconds.
- **Automatic Failsafe Key Release**: The agent monitors network health and connection state. If connection drops or the process terminates, all pressed keys and mouse buttons are instantly released to prevent stuck inputs.
