export interface ScrapeJob {
  id: string
  job_type: string
  source: string
  status: 'pending' | 'running' | 'success' | 'failed' | 'partial'
  parameters: Record<string, unknown>
  result_summary: Record<string, unknown> | null
  error_detail: string | null
  triggered_by: string
  created_at: string
  started_at: string | null
  completed_at: string | null
}
