"""
Orbit Agent — main entry point.

Startup sequence:
1. Load or create configuration.
2. If unconfigured, prompt for backend URL.
3. If not paired, enter pairing flow.
4. Authenticate with stored credentials.
5. Register device metadata.
6. Start WebSocket loop with reconnection.
7. Start system tray (optional).
8. Respond to incoming control events.
"""

import argparse
import asyncio
import logging
import signal
import sys

from orbit_agent.configuration.config import AgentConfig
from orbit_agent.networking.client import AgentWebSocketClient
from orbit_agent.input.injector import InputInjector
from orbit_agent.display.info import get_display_info
from orbit_agent.diagnostics.logger import setup_logging
from orbit_agent.tray.tray_icon import TrayIcon

logger = logging.getLogger("orbit.agent")


def enable_dpi_awareness():
    """Enable Per-Monitor DPI awareness on Windows so multi-monitor coordinates are 1:1."""
    if sys.platform == "win32":
        try:
            import ctypes
            # PROCESS_PER_MONITOR_DPI_AWARE_V2 = 2
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            try:
                import ctypes
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass


async def main():
    enable_dpi_awareness()
    setup_logging()
    logger.info("Orbit Agent starting...")

    parser = argparse.ArgumentParser(description="Orbit Agent")
    parser.add_argument("--backend-url", "-u", type=str, help="Backend URL (e.g. http://localhost:8000)")
    parser.add_argument("--reset", action="store_true", help="Reset stored configuration and credentials")
    args = parser.parse_args()

    config = AgentConfig.load()

    if args.reset:
        config.backend_url = ""
        config.device_id = None
        config.device_name = ""
        config.delete_secret()
        config.save()
        print("[INFO] Configuration reset.")

    if args.backend_url:
        url = args.backend_url.strip()
        if not (url.startswith("http://") or url.startswith("https://") or url.startswith("ws://") or url.startswith("wss://")):
            url = f"http://{url}"
        config.backend_url = url
        config.save()
        print(f"[INFO] Backend URL updated to: {config.backend_url}")

    # First-run: ask for backend URL
    if not config.backend_url:
        print("\n=== Orbit Agent First-Time Setup ===")
        url = input("Enter backend URL (e.g. http://localhost:8000): ").strip()
        if not url:
            print("No URL provided. Exiting.")
            sys.exit(1)
        if not (url.startswith("http://") or url.startswith("https://") or url.startswith("ws://") or url.startswith("wss://")):
            url = f"http://{url}"
        config.backend_url = url
        config.save()

    injector = InputInjector()
    display_info = get_display_info()
    logger.info("Display: %s", display_info)

    client = AgentWebSocketClient(config, injector, display_info)

    # Graceful shutdown
    loop = asyncio.get_running_loop()

    def _shutdown():
        logger.info("Shutdown signal received.")
        asyncio.create_task(client.stop())

    if sys.platform == "win32":
        # Windows: handle SIGINT via KeyboardInterrupt
        pass
    else:
        loop.add_signal_handler(signal.SIGTERM, _shutdown)

    # Start tray icon in a thread
    tray = TrayIcon(client)
    tray.start_in_thread()

    try:
        await client.run()
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt — shutting down.")
    finally:
        await injector.release_all()
        tray.stop()
        logger.info("Orbit Agent stopped.")


if __name__ == "__main__":
    asyncio.run(main())
