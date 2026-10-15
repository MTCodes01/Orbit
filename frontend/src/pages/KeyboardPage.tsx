/**
 * Keyboard / special keys page.
 *
 * Uses a hidden <input> to capture the native mobile keyboard.
 * Text is debounced and sent as text_input events.
 * Modifier keys use a "lock" model: tap to toggle, cleared after next keystroke.
 * Special keys are sent as key_down + key_up pairs.
 */

import { useRef, useState, useCallback } from 'react'
import { useOrbit } from '../store/OrbitContext'

const SPECIAL_KEYS = [
  ['Esc', 'escape'], ['Tab', 'tab'], ['Enter', 'enter'],
  ['Backspace', 'backspace'], ['Delete', 'delete'], ['Insert', 'insert'],
  ['Home', 'home'], ['End', 'end'], ['PgUp', 'pageup'], ['PgDn', 'pagedown'],
  ['↑', 'arrowup'], ['↓', 'arrowdown'], ['←', 'arrowleft'], ['→', 'arrowright'],
]

const FN_KEYS = Array.from({ length: 12 }, (_, i) => [`F${i + 1}`, `F${i + 1}`])

const MODIFIER_KEYS = ['Ctrl', 'Alt', 'Shift', 'Win'] as const
type Modifier = typeof MODIFIER_KEYS[number]

const MODIFIER_MAP: Record<Modifier, string> = {
  Ctrl: 'ctrl', Alt: 'alt', Shift: 'shift', Win: 'meta',
}

export default function KeyboardPage() {
  const { state, sendInput } = useOrbit()
  const { activeDeviceId } = state

  const inputRef = useRef<HTMLInputElement>(null)
  const composingRef = useRef(false)
  const lastTextRef = useRef('')

  const [lockedModifiers, setLockedModifiers] = useState<Set<Modifier>>(new Set())
  const [keyboardOpen, setKeyboardOpen] = useState(false)

  const sendKey = useCallback((key: string, modifiers: string[] = []) => {
    if (!activeDeviceId) return
    const allKeys = [...modifiers, key]
    if (modifiers.length > 0) {
      sendInput({ type: 'shortcut', protocol_version: '1.0.0', target_device_id: activeDeviceId, keys: allKeys, timestamp_ms: Date.now() })
    } else {
      sendInput({ type: 'key_down', protocol_version: '1.0.0', target_device_id: activeDeviceId, key, timestamp_ms: Date.now() })
      setTimeout(() => {
        sendInput({ type: 'key_up', protocol_version: '1.0.0', target_device_id: activeDeviceId, key, timestamp_ms: Date.now() })
      }, 30)
    }
  }, [activeDeviceId, sendInput])

  const activeModifiers = Array.from(lockedModifiers).map(m => MODIFIER_MAP[m])

  const handleSpecialKey = useCallback((key: string) => {
    sendKey(key, activeModifiers)
    // Clear locked modifiers after use
    setLockedModifiers(new Set())
  }, [sendKey, activeModifiers])

  const toggleModifier = (mod: Modifier) => {
    setLockedModifiers(prev => {
      const next = new Set(prev)
      if (next.has(mod)) next.delete(mod)
      else next.add(mod)
      return next
    })
  }

  const openKeyboard = () => {
    setKeyboardOpen(true)
    requestAnimationFrame(() => inputRef.current?.focus())
  }

  // Text input from native keyboard
  const handleInput = useCallback(() => {
    if (!activeDeviceId || composingRef.current) return
    const el = inputRef.current
    if (!el) return
    const text = el.value
    if (text.length === 0) {
      // User pressed backspace
      if (lastTextRef.current.length > 0) {
        sendKey('backspace', activeModifiers)
        setLockedModifiers(new Set())
      }
    } else {
      // Send only the delta (new characters)
      const prev = lastTextRef.current
      if (text.startsWith(prev)) {
        const delta = text.slice(prev.length)
        if (delta) {
          sendInput({ type: 'text_input', protocol_version: '1.0.0', target_device_id: activeDeviceId, text: delta, timestamp_ms: Date.now() })
        }
      } else {
        // Full replacement — send entire text
        sendInput({ type: 'text_input', protocol_version: '1.0.0', target_device_id: activeDeviceId, text, timestamp_ms: Date.now() })
      }
      // Keep only last ~50 chars to avoid buffer bloat
      el.value = text.slice(-50)
    }
    lastTextRef.current = el.value
  }, [activeDeviceId, sendInput, sendKey, activeModifiers])

  const handleCompositionStart = () => { composingRef.current = true }
  const handleCompositionEnd = () => {
    composingRef.current = false
    handleInput()
  }

  const handleBlur = () => setKeyboardOpen(false)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', padding: '12px', gap: 12, overflowY: 'auto' }}>
      {/* Hidden text input for native keyboard capture */}
      <input
        ref={inputRef}
        className="sr-only"
        type="text"
        autoComplete="off"
        autoCorrect="off"
        autoCapitalize="off"
        spellCheck={false}
        onInput={handleInput}
        onCompositionStart={handleCompositionStart}
        onCompositionEnd={handleCompositionEnd}
        onBlur={handleBlur}
        aria-label="Text input for remote keyboard"
        id="orbit-text-input"
      />

      {!activeDeviceId ? (
        <div className="empty-state">
          <div className="empty-state-icon">⌨️</div>
          <div className="empty-state-title">No device selected</div>
          <div className="empty-state-desc">Go to Trackpad tab and select a device first.</div>
        </div>
      ) : (
        <>
          {/* Keyboard activation */}
          <button
            className={`btn ${keyboardOpen ? 'btn-secondary' : 'btn-primary'}`}
            onClick={openKeyboard}
            id="open-keyboard-btn"
          >
            {keyboardOpen ? '⌨ Keyboard open — tap here to type' : '⌨ Open keyboard'}
          </button>

          {/* Modifier keys */}
          <div className="card">
            <div className="card-header">Modifier Keys</div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 8 }}>
              {MODIFIER_KEYS.map(mod => (
                <button
                  key={mod}
                  className={`modifier-btn${lockedModifiers.has(mod) ? ' locked' : ''}`}
                  onClick={() => toggleModifier(mod)}
                  id={`modifier-${mod.toLowerCase()}`}
                >
                  {mod}
                </button>
              ))}
            </div>
            {lockedModifiers.size > 0 && (
              <div style={{ marginTop: 8, fontSize: 12, color: 'var(--accent)', textAlign: 'center' }}>
                🔒 {Array.from(lockedModifiers).join(' + ')} locked — tap a key to send
              </div>
            )}
          </div>

          {/* Special keys */}
          <div className="card">
            <div className="card-header">Special Keys</div>
            <div className="shortcut-grid">
              {SPECIAL_KEYS.map(([label, key]) => (
                <button
                  key={key}
                  className="shortcut-btn"
                  onPointerDown={() => handleSpecialKey(key)}
                  id={`key-${key}`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          {/* Function keys */}
          <div className="card">
            <div className="card-header">Function Keys</div>
            <div className="shortcut-grid">
              {FN_KEYS.map(([label, key]) => (
                <button
                  key={key}
                  className="shortcut-btn"
                  onPointerDown={() => handleSpecialKey(key)}
                  id={`key-fn-${label.toLowerCase()}`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          {/* Common shortcuts */}
          <div className="card">
            <div className="card-header">Common Shortcuts</div>
            <div className="shortcut-grid">
              {[
                { label: 'Ctrl+A', keys: ['ctrl', 'a'] },
                { label: 'Ctrl+C', keys: ['ctrl', 'c'] },
                { label: 'Ctrl+V', keys: ['ctrl', 'v'] },
                { label: 'Ctrl+X', keys: ['ctrl', 'x'] },
                { label: 'Ctrl+Z', keys: ['ctrl', 'z'] },
                { label: 'Ctrl+Y', keys: ['ctrl', 'y'] },
                { label: 'Ctrl+S', keys: ['ctrl', 's'] },
                { label: 'Ctrl+W', keys: ['ctrl', 'w'] },
                { label: 'Alt+Tab', keys: ['alt', 'tab'] },
                { label: 'Alt+F4', keys: ['alt', 'F4'] },
                { label: 'Win+D', keys: ['meta', 'd'] },
                { label: 'Win+L', keys: ['meta', 'l'] },
                { label: 'Ctrl+⇧+Esc', keys: ['ctrl', 'shift', 'escape'] },
                { label: 'Prnt Scr', keys: ['printscreen'] },
              ].map(s => (
                <button
                  key={s.label}
                  className="shortcut-btn"
                  onPointerDown={() => {
                    if (!activeDeviceId) return
                    sendInput({ type: 'shortcut', protocol_version: '1.0.0', target_device_id: activeDeviceId, keys: s.keys, timestamp_ms: Date.now() })
                  }}
                >
                  {s.label}
                </button>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
