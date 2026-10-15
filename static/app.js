/**
 * OmniControl - Frontend Controller Engine
 * Features:
 * - Persistent Local Settings (retains active tab, sensitivity, haptics, wake lock)
 * - Ultra-Fast Resilient Reconnection (instant on wake, visibility, touch, and network events)
 * - Low-Latency WebSocket Touchpad, Keyboard, Gamepad, and Bluetooth Audio Controls
 */

(function () {
  'use strict';

  // --- Local Settings Store ---
  const SETTINGS_KEY = 'omnicontrol_prefs_v1';
  const defaultSettings = {
    activeTab: 'trackpad',
    mouseSensitivity: 1.5,
    hapticsEnabled: true,
    wakeLockEnabled: true,
    airMouseEnabled: false,
    airAimMode: 'always',
    airProfile: 'balanced',
    airInvertY: false,
  };

  function getSettings() {
    try {
      const data = localStorage.getItem(SETTINGS_KEY);
      return data ? { ...defaultSettings, ...JSON.parse(data) } : { ...defaultSettings };
    } catch (e) {
      return { ...defaultSettings };
    }
  }

  function saveSetting(key, value) {
    try {
      const current = getSettings();
      current[key] = value;
      localStorage.setItem(SETTINGS_KEY, JSON.stringify(current));
    } catch (e) {}
  }

  const prefs = getSettings();

  // --- State ---
  let ws = null;
  let isConnected = false;
  let isConnecting = false;
  let hapticsEnabled = prefs.hapticsEnabled;
  let wakeLockEnabled = prefs.wakeLockEnabled;
  let wakeLock = null;
  let mouseSensitivity = prefs.mouseSensitivity || 1.5;
  let isDragLocked = false;
  let isAirMouseActive = false;
  let airAimMode = prefs.airAimMode || 'always';
  let isAirClutchDown = false;
  let airProfile = prefs.airProfile || 'balanced';
  let airInvertY = prefs.airInvertY === true;
  let isAirFrozen = false;
  let isAirDragging = false;

  let reconnectAttempts = 0;
  let reconnectTimer = null;
  let lastPongTime = Date.now();
  let pingInterval = null;

  // Active Modifiers
  const activeModifiers = new Set();

  // DOM Elements
  const statusBadge = document.getElementById('connection-status');
  const statusText = document.getElementById('status-text');
  const pingText = document.getElementById('ping-text');
  const btnHaptic = document.getElementById('btn-haptic');
  const btnWakeLock = document.getElementById('btn-wakelock');
  const btnFullscreen = document.getElementById('btn-fullscreen');

  // =========================================================================
  // WEBSOCKET: LOW-LATENCY & RAPID AUTO-RECONNECT ENGINE
  // =========================================================================
  function connectWebSocket(immediate = false) {
    if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
      if (ws.readyState === WebSocket.OPEN) return;
      if (!immediate) return;
      // If immediate and still stuck connecting, terminate and restart
      try { ws.close(); } catch (e) {}
    }

    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }

    isConnecting = true;
    updateStatus('connecting', reconnectAttempts > 0 ? 'Reconnecting...' : 'Connecting...');

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;

    try {
      ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        isConnected = true;
        isConnecting = false;
        reconnectAttempts = 0;
        lastPongTime = Date.now();
        updateStatus('connected', 'Connected');
        
        // Fast sync
        fetchInitialData();
        startHeartbeat();
      };

      ws.onmessage = (event) => {
        lastPongTime = Date.now();
        try {
          const msg = JSON.parse(event.data);
          handleServerMessage(msg);
        } catch (e) {
          console.error('Error parsing WS message:', e);
        }
      };

      ws.onclose = () => {
        handleDisconnect();
      };

      ws.onerror = () => {
        try { ws.close(); } catch (e) {}
      };
    } catch (e) {
      handleDisconnect();
    }
  }

  function handleDisconnect() {
    const wasConnected = isConnected;
    isConnected = false;
    isConnecting = false;
    stopHeartbeat();
    updateStatus('disconnected', 'Reconnecting...');

    // Exponential fast backoff: 150ms -> 350ms -> 750ms -> max 1500ms
    const delays = [150, 350, 750, 1200, 1500];
    const delay = delays[Math.min(reconnectAttempts, delays.length - 1)];
    reconnectAttempts++;

    if (!reconnectTimer) {
      reconnectTimer = setTimeout(() => {
        reconnectTimer = null;
        connectWebSocket();
      }, delay);
    }
  }

  function ensureConnectedNow() {
    if (!isConnected && !isConnecting) {
      connectWebSocket(true);
    }
  }

  function sendWS(data) {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(data));
      return true;
    }
    // If user tries to send an action and we are disconnected, attempt immediate reconnect
    if (!isConnecting) {
      connectWebSocket(true);
    }
    return false;
  }

  function updateStatus(state, text) {
    if (!statusBadge || !statusText) return;
    statusBadge.className = `status-badge ${state}`;
    statusText.textContent = text;
    if (state !== 'connected' && pingText) {
      pingText.textContent = '--ms';
    }
  }

  function startHeartbeat() {
    stopHeartbeat();
    pingInterval = setInterval(() => {
      if (isConnected) {
        // Detect stale silent connection (e.g. mobile radio drop)
        if (Date.now() - lastPongTime > 3200) {
          console.warn('WebSocket heartbeat timeout - forcing fast reconnect');
          try { ws.close(); } catch (e) {}
          return;
        }
        sendWS({ type: 'ping', t: Date.now() });
      }
    }, 1200);
  }

  function stopHeartbeat() {
    if (pingInterval) {
      clearInterval(pingInterval);
      pingInterval = null;
    }
  }

  function handleServerMessage(msg) {
    if (msg.type === 'pong') {
      const rtt = Date.now() - msg.t;
      if (pingText) pingText.textContent = `${rtt}ms`;
    } else if (msg.type === 'volume_update') {
      updateVolumeDisplay(msg.volume);
    } else if (msg.type === 'mute_update') {
      updateMuteDisplay(msg.muted);
    } else if (msg.type === 'drag_state') {
      setDragLockUI(msg.active);
    }
  }

  // Fast Reconnect Hooks for Mobile Browsers
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') {
      ensureConnectedNow();
      if (wakeLockEnabled && !wakeLock) {
        requestWakeLock();
      }
    }
  });

  window.addEventListener('focus', ensureConnectedNow);
  window.addEventListener('pageshow', ensureConnectedNow);
  window.addEventListener('online', ensureConnectedNow);

  // Reconnect on touch if disconnected
  document.addEventListener('touchstart', () => {
    if (!isConnected && !isConnecting) {
      connectWebSocket(true);
    }
  }, { passive: true });

  if (statusBadge) {
    statusBadge.addEventListener('click', () => {
      haptic(25);
      connectWebSocket(true);
    });
  }

  // =========================================================================
  // HAPTICS & SCREEN WAKE LOCK
  // =========================================================================
  function haptic(ms = 25) {
    if (hapticsEnabled && navigator.vibrate) {
      try {
        navigator.vibrate(ms);
      } catch (e) {}
    }
  }

  async function requestWakeLock() {
    if ('wakeLock' in navigator) {
      try {
        wakeLock = await navigator.wakeLock.request('screen');
        if (btnWakeLock) btnWakeLock.classList.add('active');
        wakeLock.addEventListener('release', () => {
          wakeLock = null;
          if (btnWakeLock && !wakeLockEnabled) {
            btnWakeLock.classList.remove('active');
          }
        });
      } catch (err) {
        console.warn('Wake Lock request error:', err);
      }
    }
  }

  async function toggleWakeLock() {
    wakeLockEnabled = !wakeLockEnabled;
    saveSetting('wakeLockEnabled', wakeLockEnabled);

    if (wakeLockEnabled) {
      await requestWakeLock();
    } else {
      if (wakeLock) {
        try { await wakeLock.release(); } catch (e) {}
        wakeLock = null;
      }
      if (btnWakeLock) btnWakeLock.classList.remove('active');
    }
  }

  function toggleFullscreen() {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen().catch(() => {});
      if (btnFullscreen) btnFullscreen.classList.add('active');
    } else {
      document.exitFullscreen().catch(() => {});
      if (btnFullscreen) btnFullscreen.classList.remove('active');
    }
  }

  // =========================================================================
  // MODE NAVIGATION & RESTORATION
  // =========================================================================
  function switchTab(target, save = true) {
    const tabs = document.querySelectorAll('.nav-tab');
    const panels = document.querySelectorAll('.tab-panel');

    tabs.forEach((t) => t.classList.toggle('active', t.dataset.tab === target));
    panels.forEach((p) => p.classList.toggle('active', p.id === `panel-${target}`));

    if (save) {
      saveSetting('activeTab', target);
    }

    if (target === 'bluetooth') {
      loadBluetoothDevices();
    }
  }

  function initNavigation() {
    const tabs = document.querySelectorAll('.nav-tab');
    tabs.forEach((tab) => {
      tab.addEventListener('click', () => {
        haptic(20);
        switchTab(tab.dataset.tab, true);
      });
    });

    // Restore saved tab on load
    const savedTab = prefs.activeTab || 'trackpad';
    switchTab(savedTab, false);
  }

  // =========================================================================
  // 1. PRECISION LAPTOP TRACKPAD ENGINE (MULTI-TOUCH, DRAG & DROP, GESTURES)
  // =========================================================================
  function initTrackpad() {
    const surface = document.getElementById('touchpad-surface');
    const scrollStrip = document.getElementById('scroll-strip');
    const ripple = document.getElementById('touch-ripple');
    const hud = document.getElementById('gesture-hud');
    const speedSlider = document.getElementById('mouse-speed');
    const speedVal = document.getElementById('speed-val');
    const btnDragLock = document.getElementById('btn-drag-lock');
    const btnGyro = document.getElementById('btn-gyro');

    let hudTimer = null;
    function showHUD(text, duration = 1200) {
      if (!hud) return;
      hud.textContent = text;
      hud.classList.remove('hidden');
      if (hudTimer) clearTimeout(hudTimer);
      hudTimer = setTimeout(() => {
        hud.classList.add('hidden');
      }, duration);
    }

    // Restore Sensitivity
    if (speedSlider) {
      speedSlider.value = mouseSensitivity;
      if (speedVal) speedVal.textContent = `${mouseSensitivity.toFixed(1)}x`;

      speedSlider.addEventListener('input', (e) => {
        mouseSensitivity = parseFloat(e.target.value);
        if (speedVal) speedVal.textContent = `${mouseSensitivity.toFixed(1)}x`;
        saveSetting('mouseSensitivity', mouseSensitivity);
      });
    }

    if (btnDragLock) {
      btnDragLock.addEventListener('click', () => {
        haptic(35);
        sendWS({ type: 'drag_toggle' });
      });
    }

    if (btnGyro) {
      btnGyro.addEventListener('click', () => {
        haptic(30);
        toggleAirMouse();
      });
    }

    if (!surface) return;

    // Gesture State Tracking
    let activeTouches = {};
    let initialTouchCount = 0;
    let touchStartTime = 0;
    let hasMovedSignificantly = false;

    // Drag & Hold State
    let isDragging = false;
    let longPressTimer = null;
    let lastTapTime = 0;
    let lastTapPos = { x: 0, y: 0 };

    // Multi-touch gestures
    let twoFingerInitialDist = 0;
    let gestureTriggered = false;
    let multiStartCenter = { x: 0, y: 0 };

    // 3-Finger and 4-Finger Interactive Scrubbing
    let threeFingerMode = null; // 'switcher' | 'vertical' | null
    let threeFingerSwitcherActive = false;
    let threeFingerLastStepX = 0;

    let fourFingerMode = null; // 'desktop_scrub' | null
    let fourFingerLastStepX = 0;

    surface.addEventListener('touchstart', (e) => {
      e.preventDefault();
      isAirClutchDown = true;
      initialTouchCount = e.touches.length;
      touchStartTime = Date.now();
      hasMovedSignificantly = false;
      gestureTriggered = false;
      threeFingerMode = null;
      threeFingerSwitcherActive = false;
      fourFingerMode = null;

      // Update active touch coordinates
      activeTouches = {};
      let sumX = 0, sumY = 0;
      for (let i = 0; i < e.touches.length; i++) {
        const t = e.touches[i];
        activeTouches[t.identifier] = {
          startX: t.clientX,
          startY: t.clientY,
          lastX: t.clientX,
          lastY: t.clientY,
        };
        sumX += t.clientX;
        sumY += t.clientY;
      }
      multiStartCenter = { x: sumX / e.touches.length, y: sumY / e.touches.length };
      threeFingerLastStepX = multiStartCenter.x;
      fourFingerLastStepX = multiStartCenter.x;

      // Ripple effect
      if (e.touches.length === 1 && ripple) {
        const rect = surface.getBoundingClientRect();
        const rx = e.touches[0].clientX - rect.left;
        const ry = e.touches[0].clientY - rect.top;
        ripple.style.left = `${rx}px`;
        ripple.style.top = `${ry}px`;
        ripple.style.opacity = '1';
        ripple.style.transform = 'translate(-50%, -50%) scale(1)';
      }

      // --- 1. SINGLE FINGER: TAP-AND-HOLD DRAG & LONG-PRESS DRAG ---
      if (e.touches.length === 1) {
        const t = e.touches[0];
        const timeSinceLastTap = Date.now() - lastTapTime;
        const distFromLastTap = Math.hypot(t.clientX - lastTapPos.x, t.clientY - lastTapPos.y);

        // Check for Double-Tap-and-Hold Drag (Classic laptop touchpad drag)
        if (timeSinceLastTap < 280 && distFromLastTap < 40) {
          isDragging = true;
          sendWS({ type: 'mouse_button', button: 'left', action: 'down' });
          haptic(45);
          showHUD('🖱️ Dragging (Tap & Hold)');
          lastTapTime = 0;
        } else {
          // Set Long-Press to Drag Timer (320ms stationary hold)
          if (longPressTimer) clearTimeout(longPressTimer);
          longPressTimer = setTimeout(() => {
            if (!hasMovedSignificantly && activeTouches[t.identifier]) {
              isDragging = true;
              sendWS({ type: 'mouse_button', button: 'left', action: 'down' });
              haptic(45);
              const dragBadge = document.getElementById('air-drag-status-badge');
              if (isAirMouseActive && dragBadge) dragBadge.classList.remove('hidden');
              showHUD(isAirMouseActive ? '✊ Air Drag Active' : '🖱️ Drag Mode Active');
            }
          }, 320);
        }
      }

      // --- 2. TWO FINGERS: SCROLL & PINCH PREPARATION ---
      else if (e.touches.length === 2) {
        if (longPressTimer) clearTimeout(longPressTimer);
        const t0 = e.touches[0];
        const t1 = e.touches[1];
        twoFingerInitialDist = Math.hypot(t0.clientX - t1.clientX, t0.clientY - t1.clientY);
      }

      // --- 3. THREE & FOUR FINGERS: GESTURE PREPARATION ---
      else if (e.touches.length >= 3) {
        if (longPressTimer) clearTimeout(longPressTimer);
      }
    }, { passive: false });

    surface.addEventListener('touchmove', (e) => {
      e.preventDefault();

      // --- 1-FINGER MOVEMENT / DRAGGING ---
      if (e.touches.length === 1 && activeTouches[e.touches[0].identifier]) {
        const t = e.touches[0];
        const prev = activeTouches[t.identifier];
        const dx = (t.clientX - prev.lastX) * mouseSensitivity;
        const dy = (t.clientY - prev.lastY) * mouseSensitivity;

        const totalDistFromStart = Math.hypot(t.clientX - prev.startX, t.clientY - prev.startY);
        if (totalDistFromStart > 8) {
          hasMovedSignificantly = true;
          if (!isDragging && longPressTimer) {
            clearTimeout(longPressTimer);
            longPressTimer = null;
          }
        }

        // When Air Mouse is active, pointer is driven by phone motion in air!
        // Suppress 1-finger relative movement on touch surface to avoid thumb conflict.
        if (!isAirMouseActive && (Math.abs(dx) > 0.6 || Math.abs(dy) > 0.6)) {
          sendWS({ type: 'mouse_move', dx: dx, dy: dy, accel: 1.0 });
        }
        prev.lastX = t.clientX;
        prev.lastY = t.clientY;
      }

      // --- 2-FINGER SCROLL & PINCH-TO-ZOOM ---
      else if (e.touches.length === 2) {
        hasMovedSignificantly = true;
        if (longPressTimer) clearTimeout(longPressTimer);

        const t0 = e.touches[0];
        const t1 = e.touches[1];
        const prev0 = activeTouches[t0.identifier];
        const prev1 = activeTouches[t1.identifier];

        if (prev0 && prev1) {
          const curDist = Math.hypot(t0.clientX - t1.clientX, t0.clientY - t1.clientY);
          const distChange = curDist - twoFingerInitialDist;

          // Pinch-to-zoom detection
          if (Math.abs(distChange) > 22 && !gestureTriggered) {
            const zoomDelta = (distChange > 0 ? 1 : -1) * (Math.abs(distChange) / 9);
            sendWS({ type: 'mouse_zoom', delta: zoomDelta });
            showHUD(distChange > 0 ? '🔍 Zoom In' : '🔍 Zoom Out');
            twoFingerInitialDist = curDist;
          } else {
            // Natural 2D Smooth Scrolling
            const dy0 = t0.clientY - prev0.lastY;
            const dy1 = t1.clientY - prev1.lastY;
            const dx0 = t0.clientX - prev0.lastX;
            const dx1 = t1.clientX - prev1.lastX;

            const avgDy = (dy0 + dy1) / 2;
            const avgDx = (dx0 + dx1) / 2;

            if (Math.abs(avgDy) > 0.6 || Math.abs(avgDx) > 0.6) {
              sendWS({ type: 'mouse_scroll', dx: -avgDx * 0.45, dy: avgDy * 0.45 });
            }
          }

          prev0.lastX = t0.clientX;
          prev0.lastY = t0.clientY;
          prev1.lastX = t1.clientX;
          prev1.lastY = t1.clientY;
        }
      }

      // --- 3-FINGER INTERACTIVE WINDOW CHOOSER (ALT+TAB SCRUB & GESTURES) ---
      else if (e.touches.length === 3) {
        hasMovedSignificantly = true;
        let sumX = 0, sumY = 0;
        for (let i = 0; i < 3; i++) {
          sumX += e.touches[i].clientX;
          sumY += e.touches[i].clientY;
        }
        const curCenter = { x: sumX / 3, y: sumY / 3 };
        const deltaX = curCenter.x - multiStartCenter.x;
        const deltaY = curCenter.y - multiStartCenter.y;

        // Decide gesture mode
        if (!threeFingerMode) {
          if (Math.hypot(deltaX, deltaY) > 18) {
            if (Math.abs(deltaX) >= Math.abs(deltaY) * 0.75) {
              // HORIZONTAL: Interactive Alt+Tab Window Chooser!
              threeFingerMode = 'switcher';
              threeFingerSwitcherActive = true;
              threeFingerLastStepX = curCenter.x;
              sendWS({ type: 'app_switcher_start' });
              haptic(35);
              showHUD('🗔 Drag to Choose Window');
            } else {
              // VERTICAL: Task View (Up) or Show Desktop (Down)
              threeFingerMode = 'vertical';
              if (deltaY < -28 && !gestureTriggered) {
                sendWS({ type: 'gesture', action: 'task_view' });
                haptic(35);
                showHUD('⊞ Task View (Win + Tab)');
                gestureTriggered = true;
              } else if (deltaY > 28 && !gestureTriggered) {
                sendWS({ type: 'gesture', action: 'show_desktop' });
                haptic(35);
                showHUD('🖥️ Show Desktop (Win + D)');
                gestureTriggered = true;
              }
            }
          }
        } else if (threeFingerMode === 'switcher') {
          // Continuously scrub across open windows!
          const stepDiff = curCenter.x - threeFingerLastStepX;
          const STEP_THRESHOLD = 36; // px per window step

          if (stepDiff > STEP_THRESHOLD) {
            // Drag RIGHT -> Next window
            sendWS({ type: 'app_switcher_step', dir: 1 });
            haptic(20);
            showHUD('🗔 Window ▶');
            threeFingerLastStepX = curCenter.x;
          } else if (stepDiff < -STEP_THRESHOLD) {
            // Drag LEFT -> Previous window
            sendWS({ type: 'app_switcher_step', dir: -1 });
            haptic(20);
            showHUD('◀ Window 🗔');
            threeFingerLastStepX = curCenter.x;
          }
        }
      }

      // --- 4-FINGER INTERACTIVE VIRTUAL DESKTOP CHOOSER ---
      else if (e.touches.length === 4) {
        hasMovedSignificantly = true;
        let sumX = 0;
        for (let i = 0; i < 4; i++) sumX += e.touches[i].clientX;
        const curCenterX = sumX / 4;
        const deltaX = curCenterX - multiStartCenter.x;

        if (!fourFingerMode) {
          if (Math.abs(deltaX) > 18) {
            fourFingerMode = 'desktop_scrub';
            fourFingerLastStepX = curCenterX;
            showHUD('🗔 Drag to Choose Desktop');
          }
        }

        if (fourFingerMode === 'desktop_scrub') {
          const stepDiff = curCenterX - fourFingerLastStepX;
          const DESKTOP_THRESHOLD = 42; // px per desktop step

          if (stepDiff > DESKTOP_THRESHOLD) {
            // Drag RIGHT -> Next Virtual Desktop
            sendWS({ type: 'desktop_step', dir: 1 });
            haptic(35);
            showHUD('🗔 Desktop ▶');
            fourFingerLastStepX = curCenterX;
          } else if (stepDiff < -DESKTOP_THRESHOLD) {
            // Drag LEFT -> Previous Virtual Desktop
            sendWS({ type: 'desktop_step', dir: -1 });
            haptic(35);
            showHUD('◀ Desktop 🗔');
            fourFingerLastStepX = curCenterX;
          }
        }
      }
    }, { passive: false });

    surface.addEventListener('touchend', (e) => {
      e.preventDefault();
      if (ripple) {
        ripple.style.opacity = '0';
        ripple.style.transform = 'translate(-50%, -50%) scale(0)';
      }

      if (longPressTimer) {
        clearTimeout(longPressTimer);
        longPressTimer = null;
      }

      // If we were dragging, release the mouse button now!
      if (isDragging) {
        isDragging = false;
        sendWS({ type: 'mouse_button', button: 'left', action: 'up' });
        haptic(25);
        const dragBadge = document.getElementById('air-drag-status-badge');
        if (dragBadge) dragBadge.classList.add('hidden');
        showHUD('Dropped');
      }

      // If 3-finger app switcher was active, finalize window selection now!
      if (threeFingerSwitcherActive) {
        threeFingerSwitcherActive = false;
        threeFingerMode = null;
        sendWS({ type: 'app_switcher_end' });
        haptic(40);
        showHUD('✓ Window Selected');
      }

      // If 4-finger desktop scrub was active, confirm desktop selection!
      if (fourFingerMode === 'desktop_scrub') {
        fourFingerMode = null;
        haptic(30);
        showHUD('✓ Desktop Selected');
      }

      const duration = Date.now() - touchStartTime;

      // Tap handling (short touch with minimal movement)
      if (!hasMovedSignificantly && duration < 320 && !gestureTriggered) {
        const now = Date.now();

        if (initialTouchCount === 1) {
          const t = e.changedTouches[0];
          // Check for double click
          if (now - lastTapTime < 280) {
            haptic(40);
            sendWS({ type: 'mouse_button', button: 'left', action: 'dblclick' });
            showHUD('Double Click');
            lastTapTime = 0;
          } else {
            // Single Left Click
            haptic(25);
            sendWS({ type: 'mouse_button', button: 'left', action: 'click' });
            lastTapTime = now;
            lastTapPos = { x: t.clientX, y: t.clientY };
          }
        } else if (initialTouchCount === 2) {
          // 2-Finger Tap -> Right Click
          haptic(35);
          sendWS({ type: 'mouse_button', button: 'right', action: 'click' });
          showHUD('Right Click');
        } else if (initialTouchCount === 3) {
          // 3-Finger Tap -> Windows Search
          haptic(35);
          sendWS({ type: 'gesture', action: 'search' });
          showHUD('🔍 Windows Search (3-Finger Tap)');
        } else if (initialTouchCount === 4) {
          // 4-Finger Tap -> Action Center
          haptic(40);
          sendWS({ type: 'gesture', action: 'action_center' });
          showHUD('🔔 Action Center (4-Finger Tap)');
        }
      }

      activeTouches = {};
      isAirClutchDown = false;
    }, { passive: false });

    surface.addEventListener('touchcancel', () => {
      isAirClutchDown = false;
      if (longPressTimer) clearTimeout(longPressTimer);
      if (isDragging) {
        isDragging = false;
        sendWS({ type: 'mouse_button', button: 'left', action: 'up' });
        const dragBadge = document.getElementById('air-drag-status-badge');
        if (dragBadge) dragBadge.classList.add('hidden');
      }
      if (threeFingerSwitcherActive) {
        threeFingerSwitcherActive = false;
        threeFingerMode = null;
        sendWS({ type: 'app_switcher_end' });
      }
      if (fourFingerMode) {
        fourFingerMode = null;
      }
      activeTouches = {};
    });

    // Dedicated Vertical Scroll Strip
    if (scrollStrip) {
      let scrollStartY = 0;
      scrollStrip.addEventListener('touchstart', (e) => {
        e.preventDefault();
        scrollStartY = e.touches[0].clientY;
        haptic(15);
      }, { passive: false });

      scrollStrip.addEventListener('touchmove', (e) => {
        e.preventDefault();
        const currentY = e.touches[0].clientY;
        const deltaY = (scrollStartY - currentY) * 0.45;
        if (Math.abs(deltaY) > 0.4) {
          sendWS({ type: 'mouse_scroll', dx: 0, dy: deltaY });
          scrollStartY = currentY;
        }
      }, { passive: false });
    }

    // Bottom Physical-Style Mouse Buttons (Click & Hold & Drag)
    function setupPhysicalButton(id, btnName) {
      const el = document.getElementById(id);
      if (!el) return;

      el.addEventListener('pointerdown', (e) => {
        e.preventDefault();
        haptic(30);
        el.classList.add('active');
        sendWS({ type: 'mouse_button', button: btnName, action: 'down' });
      });

      function handleUp(e) {
        e.preventDefault();
        if (el.classList.contains('active')) {
          el.classList.remove('active');
          sendWS({ type: 'mouse_button', button: btnName, action: 'up' });
        }
      }

      el.addEventListener('pointerup', handleUp);
      el.addEventListener('pointercancel', handleUp);
    }

    setupPhysicalButton('btn-mouse-left', 'left');
    setupPhysicalButton('btn-mouse-mid', 'middle');
    setupPhysicalButton('btn-mouse-right', 'right');
  }

  function setDragLockUI(active) {
    isDragLocked = active;
    const btn = document.getElementById('btn-drag-lock');
    if (btn) btn.classList.toggle('active', active);
  }

  // =========================================================================
  // AIR REMOTE ENGINE (1€ ADAPTIVE FILTER, rAF LOOP & ERGONOMIC TOUCH CONTROLS)
  // =========================================================================

  // --- 1. One Euro Adaptive Low-Pass Filter (CHI 2012 VR Pointer Spec) ---
  class OneEuroFilter {
    constructor(minCutoff = 0.8, beta = 0.045, dCutoff = 1.0) {
      this.minCutoff = minCutoff;
      this.beta = beta;
      this.dCutoff = dCutoff;
      this.xPrev = null;
      this.dxPrev = 0;
      this.tPrev = null;
    }

    setParams(minCutoff, beta) {
      this.minCutoff = minCutoff;
      this.beta = beta;
    }

    alpha(cutoff, dt) {
      const tau = 1.0 / (2 * Math.PI * cutoff);
      return 1.0 / (1.0 + tau / dt);
    }

    filter(x, t) {
      if (this.tPrev === null) {
        this.xPrev = x;
        this.tPrev = t;
        this.dxPrev = 0;
        return x;
      }

      const dt = Math.max((t - this.tPrev) / 1000.0, 0.001);
      this.tPrev = t;

      // Estimate speed / derivative
      const dx = (x - this.xPrev) / dt;
      const aD = this.alpha(this.dCutoff, dt);
      const dxHat = aD * dx + (1 - aD) * this.dxPrev;
      this.dxPrev = dxHat;

      // Dynamic cutoff: high damping at low speeds, zero lag at high speeds
      const cutoff = this.minCutoff + this.beta * Math.abs(dxHat);
      const a = this.alpha(cutoff, dt);
      const xHat = a * x + (1 - a) * this.xPrev;
      this.xPrev = xHat;

      return xHat;
    }

    reset() {
      this.xPrev = null;
      this.dxPrev = 0;
      this.tPrev = null;
    }
  }

  // Profile presets
  const AIR_PROFILES = {
    smooth: { minCutoff: 0.35, beta: 0.02, label: 'Smooth' },
    balanced: { minCutoff: 0.80, beta: 0.045, label: 'Balanced' },
    fast: { minCutoff: 1.35, beta: 0.085, label: 'Agile' },
  };

  const filterX = new OneEuroFilter(0.80, 0.045);
  const filterY = new OneEuroFilter(0.80, 0.045);

  let rawAccumYaw = 0;
  let rawAccumPitch = 0;
  let prevOrientationAlpha = null;
  let prevOrientationBeta = null;
  let prevOrientationGamma = null;
  let motionListenerActive = false;
  let orientationFallbackActive = false;
  let sensorEventsReceived = 0;
  let sensorDiagTimer = null;
  let motionRafId = null;

  function applyAirProfile(profileName) {
    airProfile = profileName in AIR_PROFILES ? profileName : 'balanced';
    saveSetting('airProfile', airProfile);
    const p = AIR_PROFILES[airProfile];
    filterX.setParams(p.minCutoff, p.beta);
    filterY.setParams(p.minCutoff, p.beta);

    document.querySelectorAll('.air-profile-btn').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.profile === airProfile);
    });
  }

  function updateAirModeUI() {
    const banner = document.getElementById('air-remote-banner');
    const btnGyro = document.getElementById('btn-gyro');
    const modeBtn = document.getElementById('btn-air-mode-toggle');
    const freezeBtn = document.getElementById('btn-air-freeze');
    const invertBtn = document.getElementById('btn-air-invert-y');
    const httpsNotice = document.getElementById('air-https-notice');
    const httpsLink = document.getElementById('btn-switch-https');
    const surface = document.getElementById('touchpad-surface');
    const hintText = document.getElementById('surface-hint-text');

    if (btnGyro) btnGyro.classList.toggle('active', isAirMouseActive);
    if (banner) banner.classList.toggle('hidden', !isAirMouseActive);
    if (surface) surface.classList.toggle('air-active', isAirMouseActive);

    if (hintText) {
      hintText.textContent = isAirMouseActive
        ? 'Thumb Deck: Tap to Click • Hold to Air Drag • 2-Finger: Right Click & Scroll'
        : '1-Finger Tap: Click • Tap & Hold: Drag • 2-Finger: Right Click & Scroll • Pinch: Zoom • 3-Finger: Windows Gestures';
    }

    const isHttps = window.location.protocol === 'https:';
    const isSecure = window.isSecureContext === true;
    if (httpsNotice) {
      httpsNotice.classList.toggle('hidden', isHttps || isSecure);
      if (httpsLink) {
        httpsLink.href = `https://${window.location.hostname}:8443`;
      }
    }

    if (modeBtn) {
      if (airAimMode === 'always') {
        modeBtn.textContent = 'Mode: Always Aim';
        modeBtn.classList.add('active');
      } else {
        modeBtn.textContent = 'Mode: Touch-to-Aim';
        modeBtn.classList.remove('active');
      }
    }

    if (freezeBtn) {
      freezeBtn.textContent = isAirFrozen ? '▶ Resume' : '⏸️ Freeze';
      freezeBtn.classList.toggle('frozen', isAirFrozen);
    }

    if (invertBtn) {
      invertBtn.textContent = airInvertY ? 'Invert Y: On' : 'Invert Y: Off';
      invertBtn.classList.toggle('active', airInvertY);
    }

    applyAirProfile(airProfile);
  }

  function startSensorDiagnostics() {
    if (sensorDiagTimer) clearInterval(sensorDiagTimer);
    sensorDiagTimer = setInterval(() => {
      if (!isAirMouseActive) {
        clearInterval(sensorDiagTimer);
        sensorDiagTimer = null;
        return;
      }

      const led = document.getElementById('air-sensor-led');
      const text = document.getElementById('air-sensor-status-text');
      const isHttps = window.location.protocol === 'https:';
      const isSecure = window.isSecureContext === true;

      if (!isSecure && !isHttps) {
        if (led) led.className = 'sensor-led warning';
        if (text) text.textContent = 'HTTP: Needs HTTPS';
        return;
      }

      if (isAirFrozen) {
        if (led) led.className = 'sensor-led warning';
        if (text) text.textContent = 'Pointer Paused';
        return;
      }

      if (sensorEventsReceived > 0) {
        if (led) led.className = 'sensor-led active';
        if (text) text.textContent = `Sensors Active (${sensorEventsReceived})`;
      } else {
        if (led) led.className = 'sensor-led warning';
        if (text) text.textContent = 'Wave phone to aim';
      }
    }, 350);
  }

  function recenterAirMouse() {
    filterX.reset();
    filterY.reset();
    rawAccumYaw = 0;
    rawAccumPitch = 0;
    prevOrientationAlpha = null;
    prevOrientationBeta = null;
    prevOrientationGamma = null;
    haptic(40);
    const dot = document.getElementById('air-reticle-dot');
    if (dot) dot.style.transform = 'translate(0, 0)';
    showHUD('🎯 Pointer Centered');
  }

  // --- 2. Orientation & Acceleration Event Handlers ---
  function handleDeviceOrientation(e) {
    if (!isAirMouseActive || !isConnected || isAirFrozen) return;
    if (airAimMode === 'clutch' && !isAirClutchDown) return;

    sensorEventsReceived++;

    const alpha = typeof e.alpha === 'number' ? e.alpha : 0;
    const beta = typeof e.beta === 'number' ? e.beta : 0;
    const gamma = typeof e.gamma === 'number' ? e.gamma : 0;

    if (prevOrientationAlpha === null) {
      prevOrientationAlpha = alpha;
      prevOrientationBeta = beta;
      prevOrientationGamma = gamma;
      return;
    }

    let dAlpha = alpha - prevOrientationAlpha;
    if (dAlpha > 180) dAlpha -= 360;
    if (dAlpha < -180) dAlpha += 360;

    let dBeta = beta - prevOrientationBeta;
    if (dBeta > 180) dBeta -= 360;
    if (dBeta < -180) dBeta += 360;

    let dGamma = gamma - prevOrientationGamma;
    if (dGamma > 180) dGamma -= 360;
    if (dGamma < -180) dGamma += 360;

    prevOrientationAlpha = alpha;
    prevOrientationBeta = beta;
    prevOrientationGamma = gamma;

    // 3D Projection of phone tilt relative to user line of sight
    const radBeta = (beta * Math.PI) / 180;
    const sinBeta = Math.sin(radBeta);
    const cosBeta = Math.cos(radBeta);

    const yawDelta = -(dAlpha * sinBeta + dGamma * cosBeta);
    const pitchDelta = airInvertY ? dBeta : -dBeta;

    // Accumulate raw deltas for the rAF loop
    rawAccumYaw += yawDelta * 3.4;
    rawAccumPitch += pitchDelta * 3.4;
  }

  function handleDeviceMotion(e) {
    if (!isAirMouseActive || !isConnected || isAirFrozen) return;
    if (airAimMode === 'clutch' && !isAirClutchDown) return;

    sensorEventsReceived++;

    // Linear spatial acceleration contribution
    const accel = e.acceleration;
    if (accel && (accel.x !== null || accel.y !== null)) {
      const ax = accel.x || 0;
      const ay = accel.y || 0;
      rawAccumYaw += ax * 0.35;
      rawAccumPitch += (airInvertY ? ay : -ay) * 0.35;
    }
  }

  // --- 3. requestAnimationFrame Motion Dispatcher Loop ---
  function motionLoop() {
    if (!isAirMouseActive) return;

    if (!isAirFrozen && isConnected) {
      if (airAimMode !== 'clutch' || isAirClutchDown) {
        const now = performance.now();

        // Pass accumulated motion through 1€ filter
        const smoothDx = filterX.filter(rawAccumYaw, now);
        const smoothDy = filterY.filter(rawAccumPitch, now);

        // Reset frame accumulation
        rawAccumYaw = 0;
        rawAccumPitch = 0;

        const speed = Math.hypot(smoothDx, smoothDy);

        if (speed > 0.035) {
          // Smooth power curve ballistics (precision on slow movements, fast traverse on wrist flicks)
          const ballistics = 1.0 + Math.pow(Math.min(speed / 13.0, 1.0), 1.5) * 1.8;
          const outDx = smoothDx * ballistics * mouseSensitivity;
          const outDy = smoothDy * ballistics * mouseSensitivity;

          sendWS({ type: 'mouse_move', dx: outDx, dy: outDy, accel: 1.0 });

          // Visual 3D Reticle Radar Feedback
          const dot = document.getElementById('air-reticle-dot');
          if (dot) {
            const rx = Math.max(-12, Math.min(12, smoothDx * 2.2));
            const ry = Math.max(-12, Math.min(12, smoothDy * 2.2));
            dot.style.transform = `translate(${rx}px, ${ry}px)`;
          }
        } else {
          const dot = document.getElementById('air-reticle-dot');
          if (dot) dot.style.transform = 'translate(0, 0)';
        }
      }
    }

    motionRafId = requestAnimationFrame(motionLoop);
  }

  // --- 4. Sensors Lifecycle & Permissions ---
  async function startMotionSensors() {
    sensorEventsReceived = 0;
    filterX.reset();
    filterY.reset();
    rawAccumYaw = 0;
    rawAccumPitch = 0;

    try {
      if (typeof DeviceOrientationEvent !== 'undefined' && typeof DeviceOrientationEvent.requestPermission === 'function') {
        const res = await DeviceOrientationEvent.requestPermission();
        if (res !== 'granted') console.warn('DeviceOrientation permission:', res);
      }
    } catch (err) {
      console.warn('DeviceOrientation error:', err);
    }

    try {
      if (typeof DeviceMotionEvent !== 'undefined' && typeof DeviceMotionEvent.requestPermission === 'function') {
        const res = await DeviceMotionEvent.requestPermission();
        if (res !== 'granted') console.warn('DeviceMotion permission:', res);
      }
    } catch (err) {
      console.warn('DeviceMotion error:', err);
    }

    if (!orientationFallbackActive) {
      window.addEventListener('deviceorientation', handleDeviceOrientation, { passive: true });
      orientationFallbackActive = true;
    }
    if (!motionListenerActive) {
      window.addEventListener('devicemotion', handleDeviceMotion, { passive: true });
      motionListenerActive = true;
    }

    // Start 60Hz/120Hz rAF dispatch loop
    if (!motionRafId) {
      motionRafId = requestAnimationFrame(motionLoop);
    }

    startSensorDiagnostics();
  }

  function stopMotionSensors() {
    if (orientationFallbackActive) {
      window.removeEventListener('deviceorientation', handleDeviceOrientation);
      orientationFallbackActive = false;
    }
    if (motionListenerActive) {
      window.removeEventListener('devicemotion', handleDeviceMotion);
      motionListenerActive = false;
    }
    if (motionRafId) {
      cancelAnimationFrame(motionRafId);
      motionRafId = null;
    }
    if (sensorDiagTimer) {
      clearInterval(sensorDiagTimer);
      sensorDiagTimer = null;
    }

    filterX.reset();
    filterY.reset();
    rawAccumYaw = 0;
    rawAccumPitch = 0;
    prevOrientationAlpha = null;
    prevOrientationBeta = null;
    prevOrientationGamma = null;
    sensorEventsReceived = 0;
  }

  function toggleAirMouse() {
    isAirMouseActive = !isAirMouseActive;
    saveSetting('airMouseEnabled', isAirMouseActive);
    updateAirModeUI();

    if (isAirMouseActive) {
      startMotionSensors();
      haptic(45);
      showHUD('✨ Air Remote Active');
    } else {
      stopMotionSensors();
      haptic(25);
      showHUD('Air Remote Disabled');
    }
  }

  // --- 5. Interactive UI Setup (Profiles, Freeze, Invert, Recenter) ---
  function initAirRemoteControls() {
    const banner = document.getElementById('air-remote-banner');
    const btnModeToggle = document.getElementById('btn-air-mode-toggle');
    const btnRecenter = document.getElementById('btn-air-recenter');
    const btnFreeze = document.getElementById('btn-air-freeze');
    const btnInvertY = document.getElementById('btn-air-invert-y');

    // Crucial: Stop touch & pointer propagation on the banner so touches on popup buttons
    // NEVER reach the trackpad underneath or trigger accidental trackpad clicks
    if (banner) {
      ['pointerdown', 'pointerup', 'touchstart', 'touchend', 'click'].forEach((evt) => {
        banner.addEventListener(evt, (e) => e.stopPropagation(), { passive: evt.startsWith('touch') });
      });
    }

    // Aim Mode Toggle (Always Aim vs Touch-to-Aim Clutch)
    if (btnModeToggle) {
      btnModeToggle.addEventListener('click', (e) => {
        e.stopPropagation();
        airAimMode = airAimMode === 'always' ? 'clutch' : 'always';
        saveSetting('airAimMode', airAimMode);
        updateAirModeUI();
        haptic(30);
        showHUD(airAimMode === 'always' ? '🎯 Always Aim' : '✋ Touch-to-Aim (Clutch)');
      });
    }

    // Freeze / Pause Aiming
    if (btnFreeze) {
      btnFreeze.addEventListener('click', (e) => {
        e.stopPropagation();
        isAirFrozen = !isAirFrozen;
        updateAirModeUI();
        haptic(35);
        showHUD(isAirFrozen ? '⏸️ Pointer Paused' : '▶ Pointer Resumed');
      });
    }

    // Invert Pitch Toggle
    if (btnInvertY) {
      btnInvertY.addEventListener('click', (e) => {
        e.stopPropagation();
        airInvertY = !airInvertY;
        saveSetting('airInvertY', airInvertY);
        updateAirModeUI();
        haptic(25);
        showHUD(airInvertY ? '↕ Invert Y: ON' : '↕ Invert Y: OFF');
      });
    }

    // Recenter
    if (btnRecenter) {
      btnRecenter.addEventListener('click', (e) => {
        e.stopPropagation();
        recenterAirMouse();
      });
    }

    // Damping / Smoothing Profiles
    document.querySelectorAll('.air-profile-btn').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        haptic(25);
        applyAirProfile(btn.dataset.profile);
        showHUD(`Smoothing: ${AIR_PROFILES[airProfile].label}`);
      });
    });

    updateAirModeUI();
  }

  // =========================================================================
  // 2. KEYBOARD & SHORTCUTS LOGIC
  // =========================================================================
  function initKeyboard() {
    const typeField = document.getElementById('type-input-field');
    const btnSendText = document.getElementById('btn-send-text');
    const btnClearText = document.getElementById('btn-clear-text');

    function sendCurrentText() {
      const text = typeField ? typeField.value : '';
      if (text) {
        haptic(30);
        sendWS({ type: 'type_text', text: text });
        typeField.value = '';
      }
    }

    if (btnSendText) btnSendText.addEventListener('click', sendCurrentText);
    if (typeField) {
      typeField.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') sendCurrentText();
      });
    }

    if (btnClearText && typeField) {
      btnClearText.addEventListener('click', () => { typeField.value = ''; });
    }

    // Modifiers (Ctrl, Alt, Shift, Win)
    document.querySelectorAll('.mod-toggle').forEach((btn) => {
      btn.addEventListener('click', () => {
        haptic(25);
        const modKey = btn.dataset.key;
        if (activeModifiers.has(modKey)) {
          activeModifiers.delete(modKey);
          btn.classList.remove('active');
          sendWS({ type: 'key', key: modKey, action: 'up' });
        } else {
          activeModifiers.add(modKey);
          btn.classList.add('active');
          sendWS({ type: 'key', key: modKey, action: 'down' });
        }
      });
    });

    // Windows Shortcuts Buttons
    document.querySelectorAll('.shortcut-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        haptic(35);
        const hotkey = btn.dataset.hotkey;
        if (hotkey) {
          sendWS({ type: 'hotkey', keys: hotkey.split(',') });
        }
      });
    });

    // Single Keys (Esc, Tab, Enter, Space, Arrows, Del, Fn)
    document.querySelectorAll('[data-key]').forEach((btn) => {
      if (!btn.classList.contains('mod-toggle')) {
        setupButtonPress(btn, () => {
          haptic(20);
          sendWS({ type: 'key', key: btn.dataset.key, action: 'tap' });
        });
      }
    });
  }

  // =========================================================================
  // 3. GAME CONTROLLER ENGINE (VIRTUAL THUMBSTICKS & ABXY)
  // =========================================================================
  function initController() {
    setupThumbstick('left-stick-base', 'left-stick-nub', 'left');
    setupThumbstick('right-stick-base', 'right-stick-nub', 'right');

    // ABXY Face Buttons
    document.querySelectorAll('[data-ctrl-btn]').forEach((btn) => {
      const btnName = btn.dataset.ctrlBtn;
      btn.addEventListener('pointerdown', (e) => {
        e.preventDefault();
        haptic(30);
        sendWS({ type: 'controller_button', button: btnName, state: 'down' });
      });
      btn.addEventListener('pointerup', (e) => {
        e.preventDefault();
        sendWS({ type: 'controller_button', button: btnName, state: 'up' });
      });
      btn.addEventListener('pointercancel', (e) => {
        sendWS({ type: 'controller_button', button: btnName, state: 'up' });
      });
    });

    // Triggers (LT, RT)
    document.querySelectorAll('[data-ctrl-trigger]').forEach((btn) => {
      const triggerSide = btn.dataset.ctrlTrigger;
      btn.addEventListener('pointerdown', (e) => {
        e.preventDefault();
        haptic(35);
        sendWS({ type: 'controller_trigger', trigger: triggerSide, value: 1.0 });
      });
      btn.addEventListener('pointerup', (e) => {
        e.preventDefault();
        sendWS({ type: 'controller_trigger', trigger: triggerSide, value: 0.0 });
      });
      btn.addEventListener('pointercancel', (e) => {
        sendWS({ type: 'controller_trigger', trigger: triggerSide, value: 0.0 });
      });
    });

    // D-Pad Cross
    document.querySelectorAll('[data-ctrl-dpad]').forEach((btn) => {
      const dir = btn.dataset.ctrlDpad;
      btn.addEventListener('pointerdown', (e) => {
        e.preventDefault();
        haptic(25);
        sendWS({ type: 'controller_dpad', direction: dir, state: 'down' });
      });
      btn.addEventListener('pointerup', (e) => {
        e.preventDefault();
        sendWS({ type: 'controller_dpad', direction: dir, state: 'up' });
      });
      btn.addEventListener('pointercancel', (e) => {
        sendWS({ type: 'controller_dpad', direction: dir, state: 'up' });
      });
    });

    // Driver Modal & Reconnect
    const modal = document.getElementById('driver-modal');
    const btnOpenModal = document.getElementById('btn-driver-setup');
    const btnCloseModal = document.getElementById('btn-close-modal');
    const btnReconnect = document.getElementById('btn-reconnect-controller');

    if (btnOpenModal && modal) {
      btnOpenModal.addEventListener('click', () => modal.classList.remove('hidden'));
    }
    if (btnCloseModal && modal) {
      btnCloseModal.addEventListener('click', () => modal.classList.add('hidden'));
    }
    if (btnReconnect) {
      btnReconnect.addEventListener('click', async () => {
        haptic(30);
        btnReconnect.textContent = 'Checking Driver...';
        try {
          const res = await fetch('/api/controller/retry', { method: 'POST' });
          const data = await res.json();
          updateControllerStatus(data);
          btnReconnect.textContent = 'Driver Checked!';
          setTimeout(() => {
            btnReconnect.textContent = 'Re-detect Controller Driver';
            modal.classList.add('hidden');
          }, 1000);
        } catch (e) {
          btnReconnect.textContent = 'Error connecting to server';
        }
      });
    }
  }

  function setupThumbstick(baseId, nubId, stickName) {
    const base = document.getElementById(baseId);
    const nub = document.getElementById(nubId);
    if (!base || !nub) return;

    let touchId = null;
    const maxRadius = 45;
    let lastSent = 0;

    function handleStart(e) {
      e.preventDefault();
      const touch = e.changedTouches ? e.changedTouches[0] : e;
      touchId = touch.identifier ?? 'mouse';
      haptic(20);
      updateNub(touch.clientX, touch.clientY);
    }

    function handleMove(e) {
      if (touchId === null) return;
      e.preventDefault();
      let touch = null;
      if (e.changedTouches) {
        for (let i = 0; i < e.changedTouches.length; i++) {
          if (e.changedTouches[i].identifier === touchId) {
            touch = e.changedTouches[i];
            break;
          }
        }
      } else {
        touch = e;
      }
      if (touch) {
        updateNub(touch.clientX, touch.clientY);
      }
    }

    function handleEnd(e) {
      if (touchId === null) return;
      e.preventDefault();
      touchId = null;
      nub.style.transform = `translate(0px, 0px)`;
      sendWS({ type: 'controller_stick', stick: stickName, x: 0.0, y: 0.0 });
    }

    function updateNub(clientX, clientY) {
      const rect = base.getBoundingClientRect();
      const centerX = rect.left + rect.width / 2;
      const centerY = rect.top + rect.height / 2;

      let dx = clientX - centerX;
      let dy = clientY - centerY;
      const distance = Math.hypot(dx, dy);

      if (distance > maxRadius) {
        dx = (dx / distance) * maxRadius;
        dy = (dy / distance) * maxRadius;
      }

      nub.style.transform = `translate(${dx}px, ${dy}px)`;

      const nx = dx / maxRadius;
      const ny = -(dy / maxRadius);

      const now = Date.now();
      if (now - lastSent > 16) { // ~60Hz responsive stream
        sendWS({ type: 'controller_stick', stick: stickName, x: nx, y: ny });
        lastSent = now;
      }
    }

    base.addEventListener('touchstart', handleStart, { passive: false });
    window.addEventListener('touchmove', handleMove, { passive: false });
    window.addEventListener('touchend', handleEnd, { passive: false });
    window.addEventListener('touchcancel', handleEnd, { passive: false });
  }

  function updateControllerStatus(status) {
    const dot = document.getElementById('ctrl-mode-dot');
    const title = document.getElementById('ctrl-mode-title');
    const desc = document.getElementById('ctrl-mode-desc');
    const modalStatus = document.getElementById('modal-mode-status');

    if (status && status.vigem_active) {
      if (dot) dot.style.background = '#10b981';
      if (title) title.textContent = 'Xbox 360 Controller (ViGEm Active)';
      if (desc) desc.textContent = 'Native gamepad recognized by PC games';
      if (modalStatus) modalStatus.textContent = 'Native Xbox 360 Controller (Connected)';
    } else {
      if (dot) dot.style.background = '#3b82f6';
      if (title) title.textContent = 'Gamepad Mode: Direct Input Fallback';
      if (desc) desc.textContent = 'WASD + Mouse mappings active';
      if (modalStatus) modalStatus.textContent = 'Fallback Keyboard/Mouse (Driver Not Installed)';
    }
  }

  // =========================================================================
  // 4. BLUETOOTH & AUDIO DEVICES HUB LOGIC
  // =========================================================================
  function initBluetoothAudio() {
    const volumeSlider = document.getElementById('master-volume-slider');
    const btnMute = document.getElementById('btn-toggle-mute');
    const btnRefresh = document.getElementById('btn-refresh-devices');

    // Volume Slider
    if (volumeSlider) {
      volumeSlider.addEventListener('input', (e) => {
        const val = parseInt(e.target.value, 10);
        updateVolumeDisplay(val);
        sendWS({ type: 'volume_set', value: val });
        saveSetting('lastVolume', val);
      });
    }

    // Volume Steppers
    document.querySelectorAll('[data-vol-step]').forEach((btn) => {
      btn.addEventListener('click', () => {
        haptic(25);
        const step = parseInt(btn.dataset.volStep, 10);
        if (volumeSlider) {
          let cur = parseInt(volumeSlider.value, 10);
          cur = Math.max(0, Math.min(100, cur + step));
          updateVolumeDisplay(cur);
          sendWS({ type: 'volume_set', value: cur });
          saveSetting('lastVolume', cur);
        }
      });
    });

    // Mute Button
    if (btnMute) {
      btnMute.addEventListener('click', () => {
        haptic(30);
        sendWS({ type: 'volume_mute_toggle' });
      });
    }

    // Media Controls
    document.querySelectorAll('[data-media]').forEach((btn) => {
      btn.addEventListener('click', () => {
        haptic(30);
        sendWS({ type: 'media_action', action: btn.dataset.media });
      });
    });

    // Refresh Devices List
    if (btnRefresh) {
      btnRefresh.addEventListener('click', () => {
        haptic(25);
        loadBluetoothDevices();
      });
    }
  }

  function updateVolumeDisplay(val) {
    const volumeSlider = document.getElementById('master-volume-slider');
    const volumeDisplay = document.getElementById('volume-display-val');
    if (volumeSlider) volumeSlider.value = val;
    if (volumeDisplay) volumeDisplay.textContent = `${val}%`;
  }

  function updateMuteDisplay(muted) {
    const btnMute = document.getElementById('btn-toggle-mute');
    const iconUnmuted = document.getElementById('mute-icon-unmuted');
    const iconMuted = document.getElementById('mute-icon-muted');

    if (btnMute) btnMute.classList.toggle('muted', muted);
    if (iconUnmuted) iconUnmuted.classList.toggle('hidden', muted);
    if (iconMuted) iconMuted.classList.toggle('hidden', !muted);
  }

  async function loadBluetoothDevices() {
    const listEl = document.getElementById('devices-list');
    const countBadge = document.getElementById('device-count-badge');
    const activeTitle = document.getElementById('active-device-title');

    try {
      const res = await fetch('/api/devices');
      const data = await res.json();
      const devices = data.devices || [];

      if (countBadge) countBadge.textContent = devices.length;

      if (!devices.length) {
        if (listEl) listEl.innerHTML = '<div class="loading-state">No Bluetooth devices found</div>';
        return;
      }

      if (listEl) listEl.innerHTML = '';
      devices.forEach((dev) => {
        if (dev.is_default && activeTitle) {
          activeTitle.textContent = dev.name;
        }

        const card = document.createElement('div');
        card.className = `device-card ${dev.is_default ? 'active-device' : ''}`;

        let iconSvg = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m7 7 10 10-5 5V2l5 5L7 17"/></svg>';
        if (dev.category.includes('headphone')) {
          iconSvg = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 18v-6a9 9 0 0 1 18 0v6"/><path d="M21 19a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3zM3 19a2 2 0 0 0 2 2h1a2 2 0 0 0 2-2v-3a2 2 0 0 0-2-2H3z"/></svg>';
        } else if (dev.category.includes('speaker')) {
          iconSvg = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"/></svg>';
        }

        const tagClass = dev.connected ? 'connected' : 'paired';

        card.innerHTML = `
          <div class="device-info-left">
            <div class="device-icon-wrap">${iconSvg}</div>
            <div>
              <div class="device-name-text">${escapeHtml(dev.name)}</div>
              <div class="device-status-text">${escapeHtml(dev.status_text)}</div>
            </div>
          </div>
          <span class="device-tag ${tagClass}">${dev.connected ? 'Active' : 'Paired'}</span>
        `;

        card.addEventListener('click', () => {
          haptic(25);
          if (activeTitle) activeTitle.textContent = dev.name;
        });

        if (listEl) listEl.appendChild(card);
      });
    } catch (e) {
      console.error('Error loading devices:', e);
      if (listEl) listEl.innerHTML = '<div class="loading-state">Error loading devices</div>';
    }
  }

  // --- Initial Data Fetch ---
  async function fetchInitialData() {
    try {
      const res = await fetch('/api/status');
      const status = await res.json();

      if (status.audio) {
        updateVolumeDisplay(status.audio.volume);
        updateMuteDisplay(status.audio.muted);
        const titleEl = document.getElementById('active-device-title');
        if (titleEl && status.audio.device_name) {
          titleEl.textContent = status.audio.device_name;
        }
      }

      if (status.controller) {
        updateControllerStatus(status.controller);
      }
    } catch (e) {
      console.error('Error fetching initial status:', e);
    }
  }

  // --- Helpers ---
  function setupButtonPress(target, callback) {
    const el = typeof target === 'string' ? document.getElementById(target) : target;
    if (!el) return;

    el.addEventListener('click', (e) => {
      e.preventDefault();
      callback();
    });
  }

  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  // --- Init App ---
  document.addEventListener('DOMContentLoaded', () => {
    // Restore Haptics
    if (btnHaptic) {
      btnHaptic.classList.toggle('active', hapticsEnabled);
      btnHaptic.addEventListener('click', () => {
        hapticsEnabled = !hapticsEnabled;
        btnHaptic.classList.toggle('active', hapticsEnabled);
        saveSetting('hapticsEnabled', hapticsEnabled);
        haptic(30);
      });
    }

    // Restore Wake Lock
    if (btnWakeLock) {
      btnWakeLock.classList.toggle('active', wakeLockEnabled);
      if (wakeLockEnabled) {
        requestWakeLock();
      }
      btnWakeLock.addEventListener('click', toggleWakeLock);
    }

    if (btnFullscreen) {
      btnFullscreen.addEventListener('click', toggleFullscreen);
    }

    initNavigation();
    initTrackpad();
    initAirRemoteControls();
    initKeyboard();
    initController();
    initBluetoothAudio();

    // Start WebSocket Connection
    connectWebSocket(true);
  });
})();
