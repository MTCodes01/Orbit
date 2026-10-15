# Orbit Setup & Deployment Guide

## 1. Local Development Setup

### 1.1 Coordinator Backend

1. Navigate to the `backend/` directory:
   ```bash
   cd backend
   ```
2. Create and activate a Python virtual environment:
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Linux/macOS:
   source .venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy environment template and configure:
   ```bash
   cp .env.example .env
   ```
5. Start the development server:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

---

### 1.2 Frontend PWA Controller

1. Navigate to the `frontend/` directory:
   ```bash
   cd frontend
   ```
2. Install npm dependencies:
   ```bash
   npm install
   ```
3. Start the Vite dev server:
   ```bash
   npm run dev -- --host 0.0.0.0
   ```
4. Access from your smartphone:
   Ensure your phone is on the same local Wi-Fi network as your host machine.
   Open Safari (iOS) or Chrome (Android) and navigate to:
   `http://<YOUR_LOCAL_IP>:5173`
   Tap **Add to Home Screen** to install as a standalone PWA.

---

### 1.3 Windows Agent

1. Navigate to the `agent/` directory:
   ```bash
   cd agent
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```
3. Install agent dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the agent in interactive development mode:
   ```bash
   python -m orbit_agent
   ```
5. Enter the backend URL when prompted (e.g., `http://192.168.1.100:8000`).

---

## 2. Building the Windows Standalone Executable

To generate a single `.exe` file without requiring Python on target laptops:

1. Ensure `pyinstaller` is installed in your agent environment:
   ```bash
   pip install pyinstaller
   ```
2. Run the build script:
   ```bash
   python scripts/build_exe.py
   ```
3. The resulting binary will be located at:
   `agent/dist/orbit-agent.exe`
4. Copy `orbit-agent.exe` to any Windows 10/11 laptop and launch it directly.
