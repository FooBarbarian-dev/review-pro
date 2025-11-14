export interface Scan {
  id: string
  repository: {
    id: string
    name: string
    full_name: string
  }
  branch: string
  commit_sha: string
  status: 'pending' | 'queued' | 'running' | 'completed' | 'failed' | 'cancelled'
  total_findings: number
  critical_count: number
  high_count: number
  medium_count: number
  low_count: number
  info_count: number
  tools_used: string[]
  started_at: string | null
  completed_at: string | null
  duration_seconds: number | null
  created_at: string
}

export interface Finding {
  id: string
  rule_id: string
  rule_name: string | null
  message: string
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info'
  status: 'open' | 'fixed' | 'false_positive' | 'accepted_risk' | 'wont_fix'
  file_path: string
  start_line: number
  start_column: number
  end_line: number | null
  end_column: number | null
  snippet: string | null
  tool_name: string
  tool_version: string | null
  cwe_ids: string[]
  occurrence_count: number
  first_seen_at: string
  last_seen_at: string
  llm_verdicts?: LLMVerdict[]
  cluster_memberships?: ClusterMembership[]
}

export interface LLMVerdict {
  id: string
  verdict: 'true_positive' | 'false_positive' | 'uncertain'
  confidence: number
  reasoning: string
  cwe_id: string | null
  recommendation: string | null
  llm_provider: string
  llm_model: string
  agent_pattern: 'post_processing' | 'interactive' | 'multi_agent'
  total_tokens: number
  estimated_cost_usd: string
  processing_time_ms: number
  created_at: string
}

export interface FindingCluster {
  id: string
  cluster_label: string
  size: number
  avg_similarity: number
  cohesion_score: number
  algorithm: string
  similarity_threshold: number
  primary_rule_id: string
  primary_severity: string
  primary_tool: string
  representative_finding: Finding | null
  created_at: string
}

export interface ClusterMembership {
  id: string
  cluster: FindingCluster
  distance_to_centroid: number
}

export interface DashboardStats {
  total_scans: number
  total_findings: number
  open_findings: number
  false_positives: number
  scans_by_status: Record<string, number>
  findings_by_severity: Record<string, number>
  findings_by_tool: Record<string, number>
  recent_scans: Scan[]
  top_vulnerabilities: {
    rule_id: string
    count: number
    severity: string
  }[]
}

export interface PatternComparison {
  pattern_name: string
  total_findings: number
  true_positives: number
  false_positives: number
  uncertain: number
  total_cost_usd: number
  avg_cost_per_finding: number
  avg_time_per_finding_ms: number
  false_positive_reduction_rate: number
}
