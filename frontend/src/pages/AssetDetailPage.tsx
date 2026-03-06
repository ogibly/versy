import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import api from '../api'
import { StatusBadge } from '../components/StatusBadge'
import type { AssetDetail } from '../types'

export function AssetDetailPage() {
  const { assetId } = useParams()
  const [asset, setAsset] = useState<AssetDetail | null>(null)

  useEffect(() => {
    const load = async () => {
      const response = await api.get<AssetDetail>(`/assets/${assetId}`)
      setAsset(response.data)
    }
    void load()
  }, [assetId])

  if (!asset) return <p className="text-sm text-slate-500">Loading asset detail...</p>

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <Link to="/assets" className="text-sm text-slate-500 hover:text-slate-900">&larr; Back to assets</Link>
          <h2 className="mt-2 text-2xl font-semibold">{asset.hostname || 'Asset detail'}</h2>
          <p className="mt-1 text-sm text-slate-500">{[asset.asset_type, asset.vendor, asset.model].filter(Boolean).join(' / ')}</p>
        </div>
        <div className="flex gap-3">
          <StatusBadge label={asset.os_tier} />
          <StatusBadge label={asset.firmware_tier} />
        </div>
      </div>

      <section className="grid gap-6 lg:grid-cols-2">
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <h3 className="text-lg font-semibold">Identifiers</h3>
          <pre className="mt-4 overflow-x-auto rounded-xl bg-slate-950 p-4 text-xs text-slate-100">{JSON.stringify(asset.identifiers, null, 2)}</pre>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <h3 className="text-lg font-semibold">Observed components</h3>
          <div className="mt-4 space-y-3">
            {asset.observations.map((observation) => (
              <div key={observation.id} className="rounded-xl border border-slate-200 p-4">
                <div className="flex items-center justify-between">
                  <p className="font-medium">{observation.component_type_key}</p>
                  <p className="text-xs text-slate-500">{new Date(observation.observed_at).toLocaleString()}</p>
                </div>
                <p className="mt-2 text-sm text-slate-600">Version: {observation.version}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <h3 className="text-lg font-semibold">Evaluations</h3>
        <div className="mt-4 space-y-3">
          {asset.evaluations.map((evaluation) => (
            <div key={evaluation.id} className="rounded-xl border border-slate-200 p-4">
              <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                <div>
                  <p className="font-medium">{evaluation.component_type_key} {evaluation.observed_version}</p>
                  <p className="text-xs text-slate-500">Matched policy: {evaluation.matched_policy_id || 'No match'}</p>
                </div>
                <StatusBadge label={evaluation.lifecycle_tier} />
              </div>
              <pre className="mt-3 overflow-x-auto rounded-xl bg-slate-950 p-4 text-xs text-slate-100">{JSON.stringify(evaluation.rationale, null, 2)}</pre>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
