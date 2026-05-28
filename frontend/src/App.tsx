import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { ArgusProvider } from '@/context/ArgusContext'
import { useArgus } from '@/hooks/useArgus'
import { ApiKeySetup } from '@/components/ApiKeySetup'
import { Layout } from '@/components/Layout'
import { Dashboard } from '@/pages/Dashboard'
import { Devices } from '@/pages/Devices'
import { Events } from '@/pages/Events'
import { Alerts } from '@/pages/Alerts'
import { Settings } from '@/pages/Settings'

function AppRoutes() {
  const { needsApiKey } = useArgus()
  if (needsApiKey) return <ApiKeySetup />
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="devices" element={<Devices />} />
        <Route path="events" element={<Events />} />
        <Route path="alerts" element={<Alerts />} />
        <Route path="settings" element={<Settings />} />
      </Route>
    </Routes>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <ArgusProvider>
        <AppRoutes />
      </ArgusProvider>
    </BrowserRouter>
  )
}
