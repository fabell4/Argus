import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { ArgusProvider } from '@/context/ArgusContext'
import { Layout } from '@/components/Layout'
import { Dashboard } from '@/pages/Dashboard'
import { Settings } from '@/pages/Settings'

export default function App() {
  return (
    <BrowserRouter>
      <ArgusProvider>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="settings" element={<Settings />} />
          </Route>
        </Routes>
      </ArgusProvider>
    </BrowserRouter>
  )
}
