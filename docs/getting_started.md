# 🚀 Getting Started with OmniControl

This guide walks you through setting up, running OmniControl on Windows, and connecting your smartphone over Wi-Fi.

---

## 📋 System Requirements

- **Operating System**: Windows 10 or Windows 11 (64-bit).
- **Network**: Both your laptop and smartphone must be connected to the **same Wi-Fi network** (or laptop connected to phone's Wi-Fi Hotspot).
- **Phone Browser**: Google Chrome, Apple Safari, Microsoft Edge, or Mozilla Firefox.

---

## 🏃 Ways to Run OmniControl

### Method 1: Standalone Windows Executable (Recommended)

No Python installation required.

1. Navigate to the `dist/` directory.
2. Double-click **`OmniControl.exe`**.
3. OmniControl will launch silently in your **Windows System Tray** (bottom-right taskbar near clock).
4. Right-click the glowing cyan tray icon to:
   - View the **QR Code & IP Address**.
   - Open the Web Remote in your browser.
   - Toggle **Start with Windows on Boot**.

---

### Method 2: Running from Python Source

If you prefer running from source or are actively developing:

1. **Clone / Open the Repository**:
   ```bash
   cd d:/Github/Orbit
   ```

2. **Install Python Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Launch the Server**:
   ```bash
   python run_server.py
   ```

   The server will print an ASCII banner and QR code in your console:
   - **HTTPS**: `https://<YOUR-LAPTOP-IP>:8443` *(Unlocks motion sensors and high-performance screen features)*
   - **HTTP**: `http://<YOUR-LAPTOP-IP>:8000`

4. **Launch directly into Background System Tray**:
   ```bash
   python run_server.py --tray
   ```

---

## 📱 Connecting Your Phone

1. Ensure your phone and laptop are on the same Wi-Fi network.
2. Open your smartphone camera or QR code scanner.
3. Scan the QR code shown in the terminal or in the system tray popup (**Show QR Code**).
4. Alternatively, open your phone browser and navigate manually to:
   ```text
   https://192.168.x.x:8443
   ```
   *(Replace with your laptop's actual IP address displayed in the launcher)*

> [!TIP]
> **HTTPS Notice for Mobile Browsers**:
> Because the server uses a self-signed local certificate for low-latency HTTPS encryption (required by mobile Chrome and Safari to unlock motion sensors and hardware acceleration), your browser will display a one-time connection warning:
> - **On Chrome / Edge**: Tap **Advanced** ➔ **Proceed to \<IP> (unsafe)**.
> - **On Safari**: Tap **Show Details** ➔ **Visit this Website**.

Once loaded, your phone connects to the laptop in under **10 milliseconds**!
