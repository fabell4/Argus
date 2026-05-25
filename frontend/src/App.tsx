import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { ArgusProvider } from '@/context/ArgusContext'
import { Layout } from '@/components/Layout'
import { Dashboard } from '@/pages/Dashboard'
import { Devices } from '@/pages/Devices'
import { Events } from '@/pages/Events'
import { Alerts } from '@/pages/Alerts'
import { Settings } from '@/pages/Settings'

export default function App() {
  return (
    <BrowserRouter>
      <ArgusProvider>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="devices" element={<Devices />} />
            <Route path="events" element={<Events />} />
            <Route path="alerts" element={<Alerts />} />
            <Route path="settings" element={<Settings />} />
          </Route>
        </Routes>
      </ArgusProvider>
    </BrowserRouter>
  )
}
