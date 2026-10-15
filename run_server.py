"""
OmniControl - Laptop Remote Control Launcher & Background Agent.
Starts high-performance ASGI servers:
- HTTPS on 0.0.0.0:8443 (Unlocks Gyroscope & Accelerometer on Chrome & Safari)
- HTTP on 0.0.0.0:8000 (Standard HTTP access)
- System Tray Agent for background execution on Windows
- Live Interactive Screen Streaming & Touch Control
"""

import os
import sys
import socket
import asyncio
import argparse

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
from backend.startup_manager import is_startup_enabled, set_startup

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
    
    # Save QR code image in static folder
    try:
        qr = qrcode.QRCode(box_size=10, border=2)
        qr.add_data(https_url)
        img = qr.make_image(fill_color="black", back_color="white")
        
        if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
            static_dir = os.path.join(os.path.dirname(sys.executable), "static")
        else:
            static_dir = os.path.join(os.path.dirname(__file__), "static")
            
        os.makedirs(static_dir, exist_ok=True)
        img.save(os.path.join(static_dir, "qr.png"))
    except Exception:
        pass

    startup_status = "[bold green]Enabled[/bold green]" if is_startup_enabled() else "[dim]Disabled[/dim]"

    console.print()
    console.print(Panel.fit(
        f"[bold cyan]📱 OmniControl - Laptop Remote Control & Screen Mirror[/bold cyan]\n"
        f"[dim]Control Mouse, Touch Screen, Keyboard, Gamepad & Audio from Phone[/dim]\n\n"
        f"[bold green]▶ HTTPS URL (Air Mouse & Gyro):[/bold green] [bold underline yellow]{https_url}[/bold underline yellow]\n"
        f"   [dim](Tap 'Advanced' -> 'Proceed' on first load to unlock full features)[/dim]\n\n"
        f"[bold white]▶ HTTP URL (Touchpad & Keys):[/bold white]   [bold underline cyan]{http_url}[/bold underline cyan]\n\n"
        f"[bold magenta]▶ Windows Startup on Boot:[/bold magenta]    {startup_status}\n"
        f"[dim]Right-click the system tray icon to toggle startup or view QR.[/dim]",
        title="[bold magenta]READY FOR CONNECTION[/bold magenta]",
        border_style="cyan"
    ))
    console.print()

    # Print ASCII QR Code for HTTPS URL
    try:
        ascii_qr = qrcode.QRCode()
        ascii_qr.add_data(https_url)
        console.print("[bold yellow]📷 Scan this QR Code with your phone camera:[/bold yellow]")
        ascii_qr.print_ascii(invert=True)
    except Exception:
        console.print(f"[dim]Navigate directly to {https_url} on your phone[/dim]")

    console.print()


async def run_console_servers(http_port: int, https_port: int):
    ip = get_local_ip()
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


def main():
    parser = argparse.ArgumentParser(description="OmniControl Server Launcher")
    parser.add_argument("--tray", action="store_true", help="Run as background agent in Windows system tray")
    parser.add_argument("--background", action="store_true", help="Alias for --tray")
    parser.add_argument("--headless", action="store_true", help="Run headless console server without tray")
    parser.add_argument("--enable-startup", action="store_true", help="Enable launch on Windows boot and exit")
    parser.add_argument("--disable-startup", action="store_true", help="Disable launch on Windows boot and exit")
    parser.add_argument("--http-port", type=int, default=8000, help="HTTP port (default: 8000)")
    parser.add_argument("--https-port", type=int, default=8443, help="HTTPS port (default: 8443)")

    args = parser.parse_args()

    if args.enable_startup:
        set_startup(True)
        print("OmniControl registered to start automatically on Windows boot.")
        return

    if args.disable_startup:
        set_startup(False)
        print("OmniControl removed from Windows startup.")
        return

    # In frozen executable (compiled .exe without console), run tray agent by default
    is_frozen = getattr(sys, "frozen", False)
    if args.tray or args.background or (is_frozen and not args.headless):
        from backend.tray_agent import TrayAgent
        agent = TrayAgent(http_port=args.http_port, https_port=args.https_port)
        agent.run()
    else:
        # Standard interactive terminal mode
        try:
            asyncio.run(run_console_servers(args.http_port, args.https_port))
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
