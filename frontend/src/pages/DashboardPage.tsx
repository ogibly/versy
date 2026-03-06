import { useEffect, useState } from 'react'

import api from '../api'
import { StatusBadge } from '../components/StatusBadge'
import type { DashboardSummary } from '../types'

export function DashboardPage() {
  const [summary, setSummary] = useState<DashboardSummary>({ counts: [], hotspots: [] })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true)
        const response = await api.get<DashboardSummary>('/dashboard/summary')
        setSummary(response.data)
        setError(null)
      } catch (err) {
        setError('Unable to load dashboard summary.')
      } finally {
        setLoading(false)
      }
    }
    void load()
  }, [])

  if (loading) return <p className="text-sm text-slate-500">Loading dashboard...</p>
  if (error) return <p className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">{error}</p>

  return (
    <div className="space-y-6">
      <section>
        <h2 className="text-2xl font-semibold">Dashboard</h2>
        <p className="mt-1 text-sm text-slate-500">Current policy coverage across observed OS and firmware-style components.</p>
      </section>
      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {summary.counts.map((item) => (
          <div key={`${item.component_group}-${item.lifecycle_tier}`} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex items-center justify-between">
              <p className="text-sm font-medium text-slate-500">{item.component_group}</p>
              <StatusBadge label={item.lifecycle_tier} />
            </div>
            <p className="mt-4 text-3xl font-bold text-slate-900">{item.count}</p>
          </div>
        ))}
      </section>
      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold">Top hotspots</h3>
            <p className="text-sm text-slate-500">Highest-volume asset types and environments in the current evaluation set.</p>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="text-slate-500">
              <tr>
                <th className="pb-3 font-medium">Dimension</th>
                <th className="pb-3 font-medium">Value</th>
                <th className="pb-3 font-medium">Count</th>
              </tr>
            </thead>
            <tbody>
              {summary.hotspots.map((hotspot) => (
                <tr key={`${hotspot.dimension}-${hotspot.value}`} className="border-t border-slate-100">
                  <td className="py-3 font-medium text-slate-700">{hotspot.dimension}</td>
                  <td className="py-3 text-slate-600">{hotspot.value}</td>
                  <td className="py-3 text-slate-900">{hotspot.count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
