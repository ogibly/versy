import { useMemo, useState } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import axios from 'axios'

import { setAuthToken } from './api'
import { AppShell } from './components/AppShell'
import { AssetDetailPage } from './pages/AssetDetailPage'
import { AssetsPage } from './pages/AssetsPage'
import { DashboardPage } from './pages/DashboardPage'
import { IngestionPage } from './pages/IngestionPage'
import { PoliciesPage } from './pages/PoliciesPage'
import type { TokenResponse } from './types'

const storedToken = localStorage.getItem('lpe_token')
const storedRole = (localStorage.getItem('lpe_role') as 'admin' | 'viewer' | null) || null
const storedUsername = localStorage.getItem('lpe_username')
if (storedToken) {
  setAuthToken(storedToken)
}

function LoginScreen({ onAuthenticated }: { onAuthenticated: (token: TokenResponse) => void }) {
  const [username, setUsername] = useState('admin')
  const [password, setPassword] = useState('admin123!')
  const [error, setError] = useState<string | null>(null)

  const submit = async () => {
    try {
      const body = new URLSearchParams({ username, password })
      const response = await axios.post<TokenResponse>(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}/auth/token`, body, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      })
      onAuthenticated(response.data)
    } catch {
      setError('Login failed. Check credentials or API availability.')
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-100 px-6">
      <div className="w-full max-w-md rounded-3xl border border-slate-200 bg-white p-8 shadow-xl shadow-slate-200/70">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Lifecycle Policy Engine</p>
        <h1 className="mt-3 text-2xl font-bold text-slate-900">Sign in</h1>
        <p className="mt-2 text-sm text-slate-500">Default demo users: admin/admin123! and viewer/viewer123!</p>
        <div className="mt-6 space-y-4">
          <input className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm" value={username} onChange={(event) => setUsername(event.target.value)} placeholder="Username" />
          <input className="w-full rounded-xl border border-slate-300 px-3 py-2 text-sm" type="password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="Password" />
          {error && <p className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</p>}
          <button className="w-full rounded-xl bg-slate-900 px-4 py-2.5 text-sm font-medium text-white" onClick={() => void submit()}>
            Sign in
          </button>
        </div>
      </div>
    </div>
  )
}

function App() {
  const [token, setToken] = useState<string | null>(storedToken)
  const [role, setRole] = useState<'admin' | 'viewer' | null>(storedRole)
  const [username, setUsername] = useState<string | null>(storedUsername)

  const authenticated = useMemo(() => Boolean(token && role && username), [role, token, username])

  const handleAuthenticated = (response: TokenResponse) => {
    localStorage.setItem('lpe_token', response.access_token)
    localStorage.setItem('lpe_role', response.role)
    localStorage.setItem('lpe_username', response.username)
    setAuthToken(response.access_token)
    setToken(response.access_token)
    setRole(response.role)
    setUsername(response.username)
  }

  const logout = () => {
    localStorage.removeItem('lpe_token')
    localStorage.removeItem('lpe_role')
    localStorage.removeItem('lpe_username')
    setAuthToken(null)
    setToken(null)
    setRole(null)
    setUsername(null)
  }

  if (!authenticated || !role || !username) {
    return <LoginScreen onAuthenticated={handleAuthenticated} />
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<AppShell username={username} role={role} onLogout={logout} />}>
          <Route index element={<DashboardPage />} />
          <Route path="assets" element={<AssetsPage />} />
          <Route path="assets/:assetId" element={<AssetDetailPage />} />
          <Route path="policies" element={<PoliciesPage role={role} />} />
          <Route path="ingestion" element={<IngestionPage role={role} />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
