import { NavLink, Outlet } from 'react-router-dom'
import { Activity, Settings, Zap } from 'lucide-react'

const NAV = [
  { to: '/', label: 'Dashboard', icon: Activity, end: true },
  { to: '/settings', label: 'Settings', icon: Settings },
]

export function Layout() {
  return (
    <div className="layout">
      <header className="header">
        <div className="header-brand">
          <Zap size={20} />
          <span className="header-title">Argus</span>
          <span className="header-version">v0.1.0</span>
        </div>
      </header>

      <div className="body">
        <nav className="sidebar">
          {NAV.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}
            >
              <Icon size={16} />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>

        <main className="content">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
