# -*- mode: python ; coding: utf-8 -*-
import sys
import os

block_cipher = None

project_dir = os.path.abspath(SPECPATH)
static_dir = os.path.join(project_dir, 'static')
backend_dir = os.path.join(project_dir, 'backend')
vgamepad_dir = os.path.join(project_dir, 'vgamepad')

added_datas = [
    (static_dir, 'static'),
    (backend_dir, 'backend'),
]

if os.path.exists(vgamepad_dir):
    added_datas.append((vgamepad_dir, 'vgamepad'))

icon_path = os.path.join(static_dir, 'icon.ico')
if not os.path.exists(icon_path):
    icon_path = None

hidden_imports = [
    'uvicorn',
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.http.h11_impl',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.protocols.websockets.websockets_impl',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    'uvicorn.lifespan.off',
    'fastapi',
    'fastapi.staticfiles',
    'fastapi.responses',
    'websockets',
    'websockets.legacy',
    'websockets.legacy.server',
    'pystray',
    'pystray._win32',
    'mss',
    'mss.windows',
    'cv2',
    'numpy',
    'PIL',
    'PIL.Image',
    'PIL.ImageTk',
    'PIL.ImageDraw',
    'pycaw',
    'pycaw.pycaw',
    'comtypes',
    'comtypes.client',
    'psutil',
    'qrcode',
    'rich',
    'cryptography',
    'cryptography.x509',
    'cryptography.hazmat.primitives',
    'cryptography.hazmat.primitives.asymmetric',
    'cryptography.hazmat.primitives.asymmetric.rsa',
    'cryptography.hazmat.primitives.serialization',
    'cryptography.hazmat.backends.openssl',
    'winreg',
    'ctypes',
    'ctypes.wintypes',
]

a = Analysis(
    ['run_server.py'],
    pathex=[project_dir],
    binaries=[],
    datas=added_datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['pytest', 'unittest', 'IPython', 'matplotlib', 'torch', 'scipy', 'django'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='OmniControl',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Windowless background execution for system tray agent
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path,
)
