"""
Windows Background Tray Agent for OmniControl.
Runs in the Windows notification area (System Tray), manages HTTP/HTTPS servers,
handles Windows startup registration, and provides quick access to QR code & URLs.
"""

import sys
import os
import socket
import threading
import webbrowser
import logging
import asyncio
from typing import Optional

from PIL import Image, ImageDraw
import pystray
from pystray import MenuItem as item

from backend.startup_manager import is_startup_enabled, toggle_startup, set_startup
from backend.cert_gen import ensure_ssl_certs
import uvicorn

logger = logging.getLogger("tray_agent")


def get_local_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


def create_tray_icon_image() -> Image.Image:
    """Generate a sleek neon cyan / blue orbit icon for system tray."""
    # Check if custom icon exists
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ico_path = os.path.join(base_dir, "static", "icon.ico")
    if os.path.exists(ico_path):
        try:
            return Image.open(ico_path)
        except Exception:
            pass

    width = 64
    height = 64
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    # Outer neon ring
    draw.ellipse([4, 4, 60, 60], outline=(0, 240, 255, 255), width=4)
    # Inner glowing planet / core
    draw.ellipse([18, 18, 46, 46], fill=(0, 200, 255, 255))
    # Orbital satellite dot
    draw.ellipse([46, 10, 56, 20], fill=(255, 255, 255, 255))

    return image


class TrayAgent:
    """System Tray background agent controller."""

    def __init__(self, http_port: int = 8000, https_port: int = 8443):
        self.http_port = http_port
        self.https_port = https_port
        self.ip = get_local_ip()
        self.icon: Optional[pystray.Icon] = None
        self.server_thread: Optional[threading.Thread] = None
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.servers = []
        self._running = False

    def get_http_url(self) -> str:
        return f"http://{self.ip}:{self.http_port}"

    def get_https_url(self) -> str:
        return f"https://{self.ip}:{self.https_port}"

    def open_browser(self):
        """Open mobile web remote in default desktop browser for testing."""
        webbrowser.open(self.get_https_url())

    def show_qr_dialog(self):
        """Display QR code and connection URL in a clean popup window."""
        try:
            import tkinter as tk
            from PIL import ImageTk
            import qrcode

            def _popup():
                root = tk.Tk()
                root.title("OmniControl - Connection Info")
                root.geometry("380x480")
                root.configure(bg="#0d1117")
                root.resizable(False, False)

                # Keep on top
                root.attributes("-topmost", True)

                # Heading
                title = tk.Label(
                    root,
                    text="📱 Connect Your Phone",
                    font=("Segoe UI", 16, "bold"),
                    fg="#00f0ff",
                    bg="#0d1117"
                )
                title.pack(pady=(18, 6))

                subtitle = tk.Label(
                    root,
                    text=f"Connect your phone to the same Wi-Fi\nand scan the QR code below:",
                    font=("Segoe UI", 10),
                    fg="#8b949e",
                    bg="#0d1117"
                )
                subtitle.pack(pady=(0, 14))

                # Generate QR code for HTTPS URL
                qr = qrcode.QRCode(box_size=6, border=2)
                qr.add_data(self.get_https_url())
                qr_img = qr.make_image(fill_color="black", back_color="white")
                tk_qr = ImageTk.PhotoImage(qr_img)

                qr_label = tk.Label(root, image=tk_qr, bg="#ffffff", bd=3, relief="solid")
                qr_label.image = tk_qr  # keep reference
                qr_label.pack(pady=4)

                # URLs
                url_label = tk.Label(
                    root,
                    text=f"HTTPS: {self.get_https_url()}\nHTTP:  {self.get_http_url()}",
                    font=("Consolas", 10, "bold"),
                    fg="#58a6ff",
                    bg="#0d1117",
                    justify="center"
                )
                url_label.pack(pady=(12, 10))

                btn_close = tk.Button(
                    root,
                    text="Close",
                    font=("Segoe UI", 10, "bold"),
                    bg="#21262d",
                    fg="#c9d1d9",
                    activebackground="#30363d",
                    activeforeground="#ffffff",
                    relief="flat",
                    padx=20,
                    pady=4,
                    command=root.destroy
                )
                btn_close.pack(pady=(4, 12))

                root.mainloop()

            t = threading.Thread(target=_popup, daemon=True)
            t.start()
        except Exception as e:
            logger.error(f"Failed to show Tkinter QR dialog: {e}")
            # Fallback to browser
            webbrowser.open(self.get_https_url())

    def toggle_startup_action(self, icon, item):
        """Toggle startup state and update tray icon menu."""
        toggle_startup()

    def is_startup_checked(self, item) -> bool:
        return is_startup_enabled()

    def start_servers_thread(self):
        """Run uvicorn ASGI servers in a dedicated background thread."""
        def run_uvicorn():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)

            cert_path, key_path = ensure_ssl_certs(self.ip)

            config_http = uvicorn.Config(
                "backend.server:app",
                host="0.0.0.0",
                port=self.http_port,
                log_level="warning",
                access_log=False
            )
            config_https = uvicorn.Config(
                "backend.server:app",
                host="0.0.0.0",
                port=self.https_port,
                ssl_keyfile=key_path,
                ssl_certfile=cert_path,
                log_level="warning",
                access_log=False
            )

            server_http = uvicorn.Server(config_http)
            server_https = uvicorn.Server(config_https)
            self.servers = [server_http, server_https]

            async def _serve():
                await asyncio.gather(server_http.serve(), server_https.serve())

            self._running = True
            try:
                self.loop.run_until_complete(_serve())
            except Exception as e:
                logger.error(f"Uvicorn loop error: {e}")

        self.server_thread = threading.Thread(target=run_uvicorn, daemon=True)
        self.server_thread.start()

    def stop(self, icon=None, item=None):
        """Gracefully stop servers and exit tray icon."""
        self._running = False
        for s in self.servers:
            s.should_exit = True
        if self.icon:
            self.icon.stop()
        sys.exit(0)

    def run(self):
        """Launch background server and system tray icon."""
        self.start_servers_thread()

        menu = pystray.Menu(
            item(f"📱 OmniControl: {self.ip}:{self.http_port}", lambda: None, enabled=False),
            pystray.Menu.SEPARATOR,
            item("🌐 Open Web Remote in Browser", lambda: self.open_browser()),
            item("📷 Show QR Code & Connection Info", lambda: self.show_qr_dialog()),
            pystray.Menu.SEPARATOR,
            item(
                "🚀 Start with Windows on Boot",
                self.toggle_startup_action,
                checked=self.is_startup_checked
            ),
            pystray.Menu.SEPARATOR,
            item("❌ Exit OmniControl", self.stop)
        )

        icon_image = create_tray_icon_image()
        self.icon = pystray.Icon("OmniControl", icon_image, "OmniControl - Laptop Wireless Remote", menu)

        # Notify user server is running in background tray
        try:
            self.icon.notify(
                f"OmniControl is running in background!\nIP: {self.ip}:{self.http_port}",
                title="OmniControl Background Agent"
            )
        except Exception:
            pass

        self.icon.run()


def main():
    agent = TrayAgent()
    agent.run()


if __name__ == "__main__":
    main()
