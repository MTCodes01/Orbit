# ❓ Troubleshooting & FAQ

Common questions, network configurations, and troubleshooting steps for OmniControl.

---

## 1. Phone Cannot Connect / Page Won't Load

### Potential Causes & Fixes:
1. **Different Networks**:
   - Ensure your phone and laptop are on the same Wi-Fi SSID / frequency (2.4GHz or 5GHz) or mobile hotspot.
   - Some routers enable "AP Isolation" or "Guest Network Isolation", which prevents devices on the same Wi-Fi from talking to each other. Connect through your phone's personal hotspot if you are on a restricted university or office network.
2. **Windows Firewall**:
   - Windows Defender may block incoming ports `8000` and `8443`.
   - To allow ports through Windows Firewall in PowerShell (Run as Administrator):
     ```powershell
     New-NetFirewallRule -DisplayName "OmniControl Server" -Direction Inbound -LocalPort 8000,8443 -Protocol TCP -Action Allow
     ```

---

## 2. Browser Shows "Your connection is not private" (HTTPS Warning)

- **Why this happens**: OmniControl auto-generates a self-signed SSL certificate for your local IP (`192.168.x.x`). Browsers display this warning because the certificate is locally generated rather than issued by a public authority like Let's Encrypt.
- **Solution**:
  - **Chrome / Edge**: Tap **Advanced** ➔ **Proceed to \<IP> (unsafe)**.
  - **Safari (iOS)**: Tap **Show Details** ➔ **Visit this Website** ➔ confirm **Visit Website**.
- **Alternative**: You can also use standard HTTP (`http://<IP>:8000`), but mobile browsers require HTTPS for motion sensors (Air Mouse) and persistent screen wake locks.

---

## 3. Screen Stream is Blank or Black

- **Screen Resolution / Desktop Context**: OmniControl attaches to the Windows interactive input desktop (`OpenInputDesktop`). If your laptop is currently locked (Windows Lock Screen `Win + L`) or displaying a UAC prompt on a secure desktop, Windows prevents screen capture until you unlock the laptop.
- **Multi-Monitor Setups**: By default, OmniControl captures Monitor 1 (Primary Display). You can set your desired screen as Primary in Windows Display Settings.

---

## 4. ViGEmBus Driver Not Found (Gamepad Fallback Mode)

- OmniControl runs in **Zero-Config Fallback Mode** by default, allowing the virtual thumbsticks to send keyboard WASD and mouse aiming commands.
- If you want genuine Xbox 360 controller detection for Steam, Xbox App, and PC games:
  1. Right-click [`install_controller_driver.bat`](../install_controller_driver.bat) and select **Run as Administrator**.
  2. Complete the ViGEmBus installer.
  3. In the phone web app, tap **Gamepad** ➔ **Driver Info** ➔ **Re-detect Controller Driver**.

---

## 5. Auto-Start Does Not Run on Boot

- Ensure the file `dist/OmniControl.exe` has not been moved to another folder after enabling auto-start. If you move the executable, re-run [`enable_startup.bat`](../enable_startup.bat) or toggle the setting again in the system tray menu.
