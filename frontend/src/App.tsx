import { Routes, Route, Navigate } from 'react-router-dom'
import { OrbitProvider } from './store/OrbitContext'
import AppShell from './components/AppShell'
import TrackpadPage from './pages/TrackpadPage'
import DevicesPage from './pages/DevicesPage'
import LayoutEditorPage from './pages/LayoutEditorPage'
import KeyboardPage from './pages/KeyboardPage'
import SettingsPage from './pages/SettingsPage'
import PairingPage from './pages/PairingPage'
import DeviceDetailPage from './pages/DeviceDetailPage'

export default function App() {
  return (
    <OrbitProvider>
      <Routes>
        <Route element={<AppShell />}>
          <Route index element={<Navigate to="/trackpad" replace />} />
          <Route path="/trackpad" element={<TrackpadPage />} />
          <Route path="/devices" element={<DevicesPage />} />
          <Route path="/devices/:deviceId" element={<DeviceDetailPage />} />
          <Route path="/layout" element={<LayoutEditorPage />} />
          <Route path="/keyboard" element={<KeyboardPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/pairing" element={<PairingPage />} />
        </Route>
      </Routes>
    </OrbitProvider>
  )
}
