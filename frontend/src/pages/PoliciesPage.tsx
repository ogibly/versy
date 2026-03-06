import { useEffect, useMemo, useState } from 'react'

import api from '../api'
import { StatusBadge } from '../components/StatusBadge'
import type { Policy } from '../types'

interface PoliciesPageProps {
  role: 'admin' | 'viewer'
}

const initialForm = {
  component_type_key: 'OS',
  version: '',
  match_mode: 'exact',
  lifecycle_tier: 'N',
  effective_from: new Date().toISOString().slice(0, 16),
  effective_to: '',
  asset_type: '',
  vendor: '',
  model: '',
  environment: '',
  notes: '',
  active: true,
}

export function PoliciesPage({ role }: PoliciesPageProps) {
  const [policies, setPolicies] = useState<Policy[]>([])
  const [form, setForm] = useState(initialForm)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [csvFile, setCsvFile] = useState<File | null>(null)

  const isAdmin = role === 'admin'

  const loadPolicies = async () => {
    const response = await api.get<Policy[]>('/policies')
    setPolicies(response.data)
  }

  useEffect(() => {
    void loadPolicies()
  }, [])

  const submit = async () => {
    const payload = {
      ...form,
      effective_from: new Date(form.effective_from).toISOString(),
      effective_to: form.effective_to ? new Date(form.effective_to).toISOString() : null,
      asset_type: form.asset_type || null,
      vendor: form.vendor || null,
      model: form.model || null,
      environment: form.environment || null,
      notes: form.notes || null,
    }
    if (editingId) {
      await api.patch(`/policies/${editingId}`, payload)
    } else {
      await api.post('/policies', payload)
    }
    setForm(initialForm)
    setEditingId(null)
    await loadPolicies()
  }

  const importCsv = async () => {
    if (!csvFile) return
    const formData = new FormData()
    formData.append('file', csvFile)
    await api.post('/policies/import', formData)
    setCsvFile(null)
    await loadPolicies()
  }

  const activeCount = useMemo(() => policies.filter((policy) => policy.active).length, [policies])

  return (
    <div className="space-y-6">
      <section className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold">Policies</h2>
          <p className="mt-1 text-sm text-slate-500">Authoritative lifecycle policy rows with conflict visibility and CSV import.</p>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
          <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Active policies</p>
          <p className="text-2xl font-bold">{activeCount}</p>
        </div>
      </section>

      {isAdmin && (
        <section className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <h3 className="text-lg font-semibold">{editingId ? 'Edit policy' : 'Create policy'}</h3>
            <div className="mt-4 grid gap-3 md:grid-cols-2">
              <input className="rounded-xl border border-slate-300 px-3 py-2 text-sm" value={form.component_type_key} onChange={(event) => setForm((current) => ({ ...current, component_type_key: event.target.value }))} placeholder="Component type" />
              <input className="rounded-xl border border-slate-300 px-3 py-2 text-sm" value={form.version} onChange={(event) => setForm((current) => ({ ...current, version: event.target.value }))} placeholder="Version or prefix" />
              <select className="rounded-xl border border-slate-300 px-3 py-2 text-sm" value={form.match_mode} onChange={(event) => setForm((current) => ({ ...current, match_mode: event.target.value }))}>
                <option value="exact">exact</option>
                <option value="prefix">prefix</option>
              </select>
              <select className="rounded-xl border border-slate-300 px-3 py-2 text-sm" value={form.lifecycle_tier} onChange={(event) => setForm((current) => ({ ...current, lifecycle_tier: event.target.value }))}>
                <option value="N">N</option>
                <option value="N-1">N-1</option>
                <option value="N-2">N-2</option>
                <option value="Unsupported">Unsupported</option>
              </select>
              <input className="rounded-xl border border-slate-300 px-3 py-2 text-sm" type="datetime-local" value={form.effective_from} onChange={(event) => setForm((current) => ({ ...current, effective_from: event.target.value }))} />
              <input className="rounded-xl border border-slate-300 px-3 py-2 text-sm" type="datetime-local" value={form.effective_to} onChange={(event) => setForm((current) => ({ ...current, effective_to: event.target.value }))} />
              <input className="rounded-xl border border-slate-300 px-3 py-2 text-sm" value={form.asset_type} onChange={(event) => setForm((current) => ({ ...current, asset_type: event.target.value }))} placeholder="Asset type scope" />
              <input className="rounded-xl border border-slate-300 px-3 py-2 text-sm" value={form.environment} onChange={(event) => setForm((current) => ({ ...current, environment: event.target.value }))} placeholder="Environment scope" />
              <input className="rounded-xl border border-slate-300 px-3 py-2 text-sm" value={form.vendor} onChange={(event) => setForm((current) => ({ ...current, vendor: event.target.value }))} placeholder="Vendor scope" />
              <input className="rounded-xl border border-slate-300 px-3 py-2 text-sm" value={form.model} onChange={(event) => setForm((current) => ({ ...current, model: event.target.value }))} placeholder="Model scope" />
            </div>
            <textarea className="mt-3 min-h-24 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm" value={form.notes} onChange={(event) => setForm((current) => ({ ...current, notes: event.target.value }))} placeholder="Notes" />
            <div className="mt-4 flex gap-3">
              <button className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-medium text-white" onClick={() => void submit()}>
                {editingId ? 'Update policy' : 'Create policy'}
              </button>
              {editingId && (
                <button className="rounded-xl border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700" onClick={() => { setEditingId(null); setForm(initialForm) }}>
                  Cancel
                </button>
              )}
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <h3 className="text-lg font-semibold">CSV bulk import</h3>
            <p className="mt-1 text-sm text-slate-500">Upload a CSV with policy rows to seed or update the catalog quickly.</p>
            <input className="mt-4 block w-full text-sm" type="file" accept=".csv" onChange={(event) => setCsvFile(event.target.files?.[0] || null)} />
            <button className="mt-4 rounded-xl bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-50" disabled={!csvFile} onClick={() => void importCsv()}>
              Import CSV
            </button>
          </div>
        </section>
      )}

      <section className="overflow-x-auto rounded-2xl border border-slate-200 bg-white shadow-sm">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-slate-50 text-slate-500">
            <tr>
              <th className="px-4 py-3 font-medium">Component</th>
              <th className="px-4 py-3 font-medium">Version</th>
              <th className="px-4 py-3 font-medium">Scope</th>
              <th className="px-4 py-3 font-medium">Tier</th>
              <th className="px-4 py-3 font-medium">Effective</th>
              <th className="px-4 py-3 font-medium">Conflicts</th>
              {isAdmin && <th className="px-4 py-3 font-medium">Actions</th>}
            </tr>
          </thead>
          <tbody>
            {policies.map((policy) => (
              <tr key={policy.id} className="border-t border-slate-100 align-top">
                <td className="px-4 py-3 font-medium text-slate-900">{policy.component_type_key}</td>
                <td className="px-4 py-3 text-slate-600">{policy.version} ({policy.match_mode})</td>
                <td className="px-4 py-3 text-slate-600">{[policy.asset_type, policy.vendor, policy.model, policy.environment].filter(Boolean).join(' / ') || 'component only'}</td>
                <td className="px-4 py-3"><StatusBadge label={policy.lifecycle_tier} /></td>
                <td className="px-4 py-3 text-slate-600">{new Date(policy.effective_from).toLocaleString()}</td>
                <td className="px-4 py-3 text-slate-600">{policy.conflicts.length > 0 ? `${policy.conflicts.length} overlap(s)` : 'None'}</td>
                {isAdmin && (
                  <td className="px-4 py-3">
                    <div className="flex gap-2">
                      <button
                        className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700"
                        onClick={() => {
                          setEditingId(policy.id)
                          setForm({
                            component_type_key: policy.component_type_key,
                            version: policy.version,
                            match_mode: policy.match_mode,
                            lifecycle_tier: policy.lifecycle_tier,
                            effective_from: policy.effective_from.slice(0, 16),
                            effective_to: policy.effective_to ? policy.effective_to.slice(0, 16) : '',
                            asset_type: policy.asset_type || '',
                            vendor: policy.vendor || '',
                            model: policy.model || '',
                            environment: policy.environment || '',
                            notes: policy.notes || '',
                            active: policy.active,
                          })
                        }}
                      >
                        Edit
                      </button>
                      <button
                        className="rounded-lg border border-rose-300 px-3 py-1.5 text-xs font-medium text-rose-700"
                        onClick={() => {
                          void api.delete(`/policies/${policy.id}`).then(loadPolicies)
                        }}
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  )
}
