import { useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { Activity, Settings, Zap, Menu, X } from 'lucide-react'

const NAV = [
  { to: '/', label: 'Dashboard', icon: Activity, end: true },
  { to: '/settings', label: 'Settings', icon: Settings },
]

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  `flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-all ${
    isActive
      ? 'bg-violet-500/10 text-violet-400 border border-violet-500/20'
      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
  }`

export function Layout() {
  const [mobileOpen, setMobileOpen] = useState(false)

  const sidebar = (
    <nav className="flex flex-col gap-1 p-4">
      {NAV.map(({ to, label, icon: Icon, end }) => (
        <NavLink
          key={to}
          to={to}
          end={end}
          className={navLinkClass}
          onClick={() => setMobileOpen(false)}
        >
          <Icon size={18} />
          {label}
        </NavLink>
      ))}
    </nav>
  )

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      {/* Header */}
      <header className="fixed top-0 left-0 right-0 z-40 h-14 border-b border-slate-800 bg-slate-950/90 backdrop-blur flex items-center px-4 gap-3">
        <button
          className="lg:hidden p-2 rounded-md text-slate-400 hover:text-slate-200 hover:bg-slate-800/50 transition-colors"
          onClick={() => setMobileOpen((o) => !o)}
          aria-label="Toggle menu"
        >
          {mobileOpen ? <X size={20} /> : <Menu size={20} />}
        </button>
        <div className="flex items-center gap-2">
          <Zap size={20} className="text-violet-400" />
          <span className="font-bold text-slate-100 text-lg tracking-tight">Argus</span>
          <span className="hidden sm:inline text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700">
            Power Monitor
          </span>
        </div>
      </header>

      {/* Desktop sidebar */}
      <aside className="hidden lg:flex flex-col fixed top-14 left-0 bottom-0 w-56 border-r border-slate-800 bg-slate-950/50">
        {sidebar}
      </aside>

      {/* Mobile drawer */}
      <AnimatePresence>
        {mobileOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-30 bg-slate-950/70 lg:hidden"
              onClick={() => setMobileOpen(false)}
            />
            <motion.div
              initial={{ x: '-100%' }}
              animate={{ x: 0 }}
              exit={{ x: '-100%' }}
              transition={{ type: 'tween', duration: 0.22 }}
              className="fixed top-14 left-0 bottom-0 w-56 z-40 border-r border-slate-800 bg-slate-950 lg:hidden"
            >
              {sidebar}
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* Main content */}
      <main className="pt-14 lg:ml-56 min-h-screen">
        <div className="max-w-6xl mx-auto p-4 md:p-6">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
