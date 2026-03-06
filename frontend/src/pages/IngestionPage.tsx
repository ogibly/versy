import { useEffect, useState } from 'react'

import api from '../api'
import type { IngestionRun } from '../types'

interface IngestionPageProps {
  role: 'admin' | 'viewer'
}

export function IngestionPage({ role }: IngestionPageProps) {
  const [runs, setRuns] = useState<IngestionRun[]>([])
  const [file, setFile] = useState<File | null>(null)
  const [search, setSearch] = useState('')
  const [fields, setFields] = useState('')
  const isAdmin = role === 'admin'

  const loadRuns = async () => {
    const response = await api.get<IngestionRun[]>('/ingest/runs')
    setRuns(response.data)
  }

  useEffect(() => {
    void loadRuns()
  }, [])

  const uploadFile = async () => {
    if (!file) return
    const formData = new FormData()
    formData.append('file', file)
    await api.post('/ingest/file', formData)
    setFile(null)
    await loadRuns()
  }

  const triggerRunZero = async () => {
    await api.post('/ingest/runzero', { search: search || null, fields: fields || null })
    await loadRuns()
  }

  const evaluate = async () => {
    await api.post('/evaluate')
    await loadRuns()
  }

  return (
    <div className="space-y-6">
      <section>
        <h2 className="text-2xl font-semibold">Ingestion</h2>
        <p className="mt-1 text-sm text-slate-500">Manual file ingest, runZero pull triggers, and evaluation recomputation.</p>
      </section>

      {isAdmin && (
        <section className="grid gap-6 lg:grid-cols-3">
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <h3 className="text-lg font-semibold">Manual upload</h3>
            <input className="mt-4 block w-full text-sm" type="file" accept=".json,.jsonl" onChange={(event) => setFile(event.target.files?.[0] || null)} />
            <button className="mt-4 rounded-xl bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-50" disabled={!file} onClick={() => void uploadFile()}>
              Upload export
            </button>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <h3 className="text-lg font-semibold">Trigger runZero pull</h3>
            <input className="mt-4 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm" placeholder="Optional search query" value={search} onChange={(event) => setSearch(event.target.value)} />
            <input className="mt-3 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm" placeholder="Optional fields list" value={fields} onChange={(event) => setFields(event.target.value)} />
            <button className="mt-4 rounded-xl bg-slate-900 px-4 py-2 text-sm font-medium text-white" onClick={() => void triggerRunZero()}>
              Pull from runZero
            </button>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <h3 className="text-lg font-semibold">Evaluation</h3>
            <p className="mt-1 text-sm text-slate-500">Recompute the latest policy match for every observed asset component.</p>
            <button className="mt-4 rounded-xl bg-slate-900 px-4 py-2 text-sm font-medium text-white" onClick={() => void evaluate()}>
              Recompute evaluations
            </button>
          </div>
        </section>
      )}

      <section className="overflow-x-auto rounded-2xl border border-slate-200 bg-white shadow-sm">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-slate-50 text-slate-500">
            <tr>
              <th className="px-4 py-3 font-medium">Started</th>
              <th className="px-4 py-3 font-medium">Finished</th>
              <th className="px-4 py-3 font-medium">Source</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium">Stats</th>
              <th className="px-4 py-3 font-medium">Error</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((run) => (
              <tr key={run.id} className="border-t border-slate-100">
                <td className="px-4 py-3 text-slate-600">{new Date(run.started_at).toLocaleString()}</td>
                <td className="px-4 py-3 text-slate-600">{run.finished_at ? new Date(run.finished_at).toLocaleString() : '-'}</td>
                <td className="px-4 py-3 text-slate-600">{run.source}</td>
                <td className="px-4 py-3 font-medium text-slate-900">{run.status}</td>
                <td className="px-4 py-3"><pre className="max-w-xs overflow-x-auto text-xs text-slate-600">{JSON.stringify(run.stats, null, 2)}</pre></td>
                <td className="px-4 py-3 text-xs text-rose-700">{run.error || '-'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  )
}
