import { NavLink, Outlet } from 'react-router-dom'

interface AppShellProps {
  username: string
  role: 'admin' | 'viewer'
  onLogout: () => void
}

const navItems = [
  { to: '/', label: 'Dashboard' },
  { to: '/assets', label: 'Assets' },
  { to: '/policies', label: 'Policies' },
  { to: '/ingestion', label: 'Ingestion' },
]

export function AppShell({ username, role, onLogout }: AppShellProps) {
  return (
    <div className="min-h-screen bg-slate-100 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Lifecycle Policy Engine</p>
            <h1 className="text-xl font-bold">OS / firmware lifecycle governance</h1>
          </div>
          <div className="flex items-center gap-4 text-sm">
            <div className="text-right">
              <p className="font-semibold">{username}</p>
              <p className="text-slate-500">{role.toUpperCase()}</p>
            </div>
            <button className="rounded-lg border border-slate-300 px-3 py-2 font-medium text-slate-700 hover:bg-slate-50" onClick={onLogout}>
              Log out
            </button>
          </div>
        </div>
        <nav className="mx-auto flex max-w-7xl gap-2 px-6 pb-4">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                `rounded-lg px-4 py-2 text-sm font-medium ${isActive ? 'bg-slate-900 text-white' : 'text-slate-600 hover:bg-slate-200'}`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </header>
      <main className="mx-auto max-w-7xl px-6 py-8">
        <Outlet />
      </main>
    </div>
  )
}
