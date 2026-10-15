"""
Laptop Remote Control Launcher.
Generates terminal QR code and starts high-performance ASGI servers:
- HTTPS on 0.0.0.0:8443 (Unlocks Gyroscope & Accelerometer on Chrome & Safari)
- HTTP on 0.0.0.0:8000 (Standard HTTP access)
"""

import os
import sys
import socket
import asyncio

# Configure UTF-8 stdout/stderr for Windows console unicode support
try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

import qrcode
import uvicorn
from rich.console import Console
from rich.panel import Panel
from backend.cert_gen import ensure_ssl_certs

console = Console(legacy_windows=False, force_terminal=True)


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


def print_banner(ip: str, http_port: int, https_port: int):
    https_url = f"https://{ip}:{https_port}"
    http_url = f"http://{ip}:{http_port}"
    
    # Save QR code image in static folder (default to HTTPS for full sensor support)
    try:
        qr = qrcode.QRCode(box_size=10, border=2)
        qr.add_data(https_url)
        img = qr.make_image(fill_color="black", back_color="white")
        static_dir = os.path.join(os.path.dirname(__file__), "static")
        os.makedirs(static_dir, exist_ok=True)
        img.save(os.path.join(static_dir, "qr.png"))
    except Exception:
        pass

    console.print()
    console.print(Panel.fit(
        f"[bold cyan]📱 Laptop Remote Control Server[/bold cyan]\n"
        f"[dim]Control Mouse, Keyboard, Gamepad & Bluetooth from your Phone[/dim]\n\n"
        f"[bold green]▶ HTTPS URL (Air Mouse & Gyro):[/bold green] [bold underline yellow]{https_url}[/bold underline yellow]\n"
        f"   [dim](Recommended for phone: Tap 'Advanced' -> 'Proceed' on first load to unlock motion sensors)[/dim]\n\n"
        f"[bold white]▶ HTTP URL (Touchpad & Keys):[/bold white]   [bold underline cyan]{http_url}[/bold underline cyan]\n"
        f"[dim]Ensure your phone is connected to the same Wi-Fi / Hotspot network.[/dim]",
        title="[bold magenta]READY FOR CONNECTION[/bold magenta]",
        border_style="cyan"
    ))
    console.print()

    # Print ASCII QR Code for HTTPS URL
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        ascii_qr = qrcode.QRCode()
        ascii_qr.add_data(https_url)
        console.print("[bold yellow]📷 Scan this QR Code with your phone camera (opens HTTPS):[/bold yellow]")
        ascii_qr.print_ascii(invert=True)
    except Exception:
        console.print(f"[dim]Tip: Or navigate directly to {https_url} on your phone[/dim]")

    console.print()


async def main():
    ip = get_local_ip()
    http_port = 8000
    https_port = 8443

    # Generate SSL certs for LAN IP
    cert_path, key_path = ensure_ssl_certs(ip)

    print_banner(ip, http_port, https_port)

    config_http = uvicorn.Config(
        "backend.server:app",
        host="0.0.0.0",
        port=http_port,
        log_level="info",
        access_log=False
    )
    config_https = uvicorn.Config(
        "backend.server:app",
        host="0.0.0.0",
        port=https_port,
        ssl_keyfile=key_path,
        ssl_certfile=cert_path,
        log_level="info",
        access_log=False
    )

    server_http = uvicorn.Server(config_http)
    server_https = uvicorn.Server(config_https)

    await asyncio.gather(server_http.serve(), server_https.serve())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
