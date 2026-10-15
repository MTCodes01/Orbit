"""
Automated PyInstaller Build Script for OmniControl Windows Executable (.exe).
Compiles OmniControl into a standalone, portable Windows .exe with
system tray agent, screen mirroring, and startup support bundled.
"""

import os
import sys
import subprocess
import shutil
import time

try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

def build():
    start_time = time.time()
    project_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_dir)

    print("==================================================")
    print("[*] OmniControl Windows Executable (.exe) Compiler")
    print("==================================================")
    print(f"Working Directory: {project_dir}")

    # 1. Ensure PyInstaller is installed
    try:
        import PyInstaller
        print(f"[+] PyInstaller version {PyInstaller.__version__} found.")
    except ImportError:
        print("[*] Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    # 2. Check icon
    icon_path = os.path.join(project_dir, "static", "icon.ico")
    if not os.path.exists(icon_path):
        print("[*] Generating icon...")
        from PIL import Image, ImageDraw
        img = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.ellipse([16, 16, 240, 240], outline=(0, 240, 255, 255), width=16)
        d.ellipse([70, 70, 186, 186], fill=(0, 180, 255, 255))
        d.ellipse([180, 30, 226, 76], fill=(255, 255, 255, 255))
        img.save(icon_path, format="ICO")
    print("[+] App icon verified.")

    # 3. Clean previous build artifacts
    # Close any running instance of OmniControl.exe so dist/ is not locked
    try:
        subprocess.run(["taskkill", "/f", "/im", "OmniControl.exe"], capture_output=True)
        time.sleep(1)
    except Exception:
        pass

    for folder in ["build", "dist"]:
        p = os.path.join(project_dir, folder)
        if os.path.exists(p):
            try:
                shutil.rmtree(p)
                print(f"[+] Cleaned {folder}/")
            except Exception as e:
                print(f"[*] Notice: Could not clean {folder}/: {e}")

    # 4. Run PyInstaller
    spec_file = os.path.join(project_dir, "OmniControl.spec")
    print(f"\n[*] Building from {spec_file} ...\n[*] This may take 1-2 minutes...")

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--clean",
        "--noconfirm",
        spec_file
    ]

    result = subprocess.run(cmd)
    if result.returncode != 0:
        print("\n[-] Build failed! Check the error log above.")
        sys.exit(result.returncode)

    # 5. Verify output
    dist_exe = os.path.join(project_dir, "dist", "OmniControl.exe")
    if os.path.exists(dist_exe):
        size_mb = os.path.getsize(dist_exe) / (1024 * 1024)
        elapsed = time.time() - start_time
        print("\n" + "=" * 50)
        print("[+] BUILD COMPLETE SUCCESSFUL!")
        print("=" * 50)
        print(f"Executable:  {dist_exe}")
        print(f"Binary Size: {size_mb:.1f} MB")
        print(f"Build Time:  {elapsed:.1f} seconds")
        print("\nFeatures in this build:")
        print(" - Standalone portable Windows .exe (no Python installation required)")
        print(" - System Tray background agent with launch on Windows startup")
        print(" - Live Interactive Screen Mirroring with mobile Touchscreen controls")
        print(" - Low-latency Gamepad, Keyboard, Mouse, and Bluetooth Hub")
        print("=" * 50)
    else:
        print("\n[!] Build completed, but dist/OmniControl.exe was not found.")

if __name__ == "__main__":
    build()
