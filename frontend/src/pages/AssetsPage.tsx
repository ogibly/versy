import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import api from '../api'
import { StatusBadge } from '../components/StatusBadge'
import type { Asset } from '../types'

export function AssetsPage() {
  const navigate = useNavigate()
  const [assets, setAssets] = useState<Asset[]>([])
  const [filters, setFilters] = useState({ q: '', asset_type: '', environment: '' })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      const response = await api.get<Asset[]>('/assets', { params: filters })
      setAssets(response.data)
      setLoading(false)
    }
    void load()
  }, [filters])

  return (
    <div className="space-y-6">
      <section className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <h2 className="text-2xl font-semibold">Assets</h2>
          <p className="mt-1 text-sm text-slate-500">Filter inventory and inspect the latest lifecycle evaluation for each asset.</p>
        </div>
        <div className="grid gap-3 md:grid-cols-3">
          <input className="rounded-xl border border-slate-300 px-3 py-2 text-sm" placeholder="Search hostname/vendor/model" value={filters.q} onChange={(event) => setFilters((current) => ({ ...current, q: event.target.value }))} />
          <input className="rounded-xl border border-slate-300 px-3 py-2 text-sm" placeholder="Asset type" value={filters.asset_type} onChange={(event) => setFilters((current) => ({ ...current, asset_type: event.target.value }))} />
          <input className="rounded-xl border border-slate-300 px-3 py-2 text-sm" placeholder="Environment" value={filters.environment} onChange={(event) => setFilters((current) => ({ ...current, environment: event.target.value }))} />
        </div>
      </section>
      <section className="overflow-x-auto rounded-2xl border border-slate-200 bg-white shadow-sm">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-slate-50 text-slate-500">
            <tr>
              <th className="px-4 py-3 font-medium">Hostname</th>
              <th className="px-4 py-3 font-medium">Type</th>
              <th className="px-4 py-3 font-medium">Vendor / model</th>
              <th className="px-4 py-3 font-medium">Environment</th>
              <th className="px-4 py-3 font-medium">OS tier</th>
              <th className="px-4 py-3 font-medium">FW tier</th>
              <th className="px-4 py-3 font-medium">Last seen</th>
            </tr>
          </thead>
          <tbody>
            {assets.map((asset) => (
              <tr key={asset.id} className="cursor-pointer border-t border-slate-100 hover:bg-slate-50" onClick={() => navigate(`/assets/${asset.id}`)}>
                <td className="px-4 py-3 font-medium text-slate-900">{asset.hostname || 'Unnamed asset'}</td>
                <td className="px-4 py-3 text-slate-600">{asset.asset_type}</td>
                <td className="px-4 py-3 text-slate-600">{[asset.vendor, asset.model].filter(Boolean).join(' / ') || 'Unknown'}</td>
                <td className="px-4 py-3 text-slate-600">{asset.environment || 'other'}</td>
                <td className="px-4 py-3"><StatusBadge label={asset.os_tier} /></td>
                <td className="px-4 py-3"><StatusBadge label={asset.firmware_tier} /></td>
                <td className="px-4 py-3 text-slate-600">{new Date(asset.last_seen_at).toLocaleString()}</td>
              </tr>
            ))}
            {!loading && assets.length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-10 text-center text-slate-500">No assets match the current filters.</td>
              </tr>
            )}
          </tbody>
        </table>
      </section>
    </div>
  )
}
