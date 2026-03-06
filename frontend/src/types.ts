export interface TokenResponse {
  access_token: string
  token_type: string
  role: 'admin' | 'viewer'
  username: string
}

export interface TierCount {
  component_group: string
  lifecycle_tier: 'N' | 'N-1' | 'N-2' | 'Unsupported'
  count: number
}

export interface Hotspot {
  dimension: string
  value: string
  count: number
}

export interface DashboardSummary {
  counts: TierCount[]
  hotspots: Hotspot[]
}

export interface Asset {
  id: string
  asset_type: string
  vendor: string | null
  model: string | null
  environment: string | null
  hostname: string | null
  identifiers: Record<string, unknown>
  first_seen_at: string
  last_seen_at: string
  os_tier: 'N' | 'N-1' | 'N-2' | 'Unsupported' | null
  firmware_tier: 'N' | 'N-1' | 'N-2' | 'Unsupported' | null
}

export interface Observation {
  id: string
  component_type_id: string
  component_type_key: string
  version: string
  observed_at: string
  source: string
  raw: Record<string, unknown>
}

export interface Evaluation {
  id: string
  asset_id: string
  component_type_id: string
  component_type_key: string
  observed_version: string
  lifecycle_tier: 'N' | 'N-1' | 'N-2' | 'Unsupported'
  matched_policy_id: string | null
  evaluated_at: string
  rationale: Record<string, unknown>
  asset_hostname?: string | null
  asset_type?: string | null
  environment?: string | null
}

export interface AssetDetail extends Asset {
  observations: Observation[]
  evaluations: Evaluation[]
}

export interface Policy {
  id: string
  component_type_id: string
  component_type_key: string
  asset_type: string | null
  vendor: string | null
  model: string | null
  environment: string | null
  version: string
  match_mode: 'exact' | 'prefix'
  lifecycle_tier: 'N' | 'N-1' | 'N-2' | 'Unsupported'
  effective_from: string
  effective_to: string | null
  active: boolean
  notes: string | null
  created_at: string
  created_by: string | null
  conflicts: Array<Record<string, unknown>>
}

export interface IngestionRun {
  id: string
  started_at: string
  finished_at: string | null
  status: string
  source: string
  stats: Record<string, unknown>
  error: string | null
}
