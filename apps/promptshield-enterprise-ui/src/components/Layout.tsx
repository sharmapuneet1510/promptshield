import { NavLink, Outlet } from 'react-router-dom'
import {
  BarChart3,
  FileText,
  LayoutDashboard,
  Settings,
  Shield,
  Users,
} from 'lucide-react'
import { clsx } from 'clsx'

const NAV_ITEMS = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/requests', label: 'Requests', icon: FileText },
  { to: '/policies', label: 'Policies', icon: Shield },
  { to: '/users', label: 'Users', icon: Users },
  { to: '/settings', label: 'Settings', icon: Settings },
]

export default function Layout() {
  return (
    <div className="flex h-screen bg-slate-900 overflow-hidden">
      {/* Sidebar */}
      <aside className="w-60 flex-shrink-0 bg-slate-800 border-r border-slate-700 flex flex-col">
        {/* Logo */}
        <div className="px-5 py-4 border-b border-slate-700">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center">
              <Shield className="w-4 h-4 text-white" />
            </div>
            <div>
              <div className="text-sm font-bold text-white">PromptShield</div>
              <div className="text-xs text-slate-400">Enterprise</div>
            </div>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                clsx(
                  'flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-indigo-600 text-white'
                    : 'text-slate-400 hover:bg-slate-700 hover:text-slate-100',
                )
              }
            >
              <Icon className="w-4 h-4 flex-shrink-0" />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* Footer */}
        <div className="px-5 py-3 border-t border-slate-700">
          <p className="text-xs text-slate-500">PromptShield v0.1.0</p>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top bar */}
        <header className="h-14 bg-slate-800 border-b border-slate-700 flex items-center px-6">
          <div className="flex items-center gap-2">
            <BarChart3 className="w-4 h-4 text-indigo-400" />
            <span className="text-sm text-slate-400">Admin Dashboard</span>
          </div>
          <div className="ml-auto flex items-center gap-3">
            <div className="w-2 h-2 bg-green-500 rounded-full"></div>
            <span className="text-xs text-slate-400">API Connected</span>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
