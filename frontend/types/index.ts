// Experience Object - 系统核心数据结构
export interface Experience {
  id: string
  timestamp: string
  context: {
    domain: string
    task_type: string
    constraints: Record<string, unknown>
  }
  intent: string
  execution: {
    steps: unknown[]
    tools: string[]
    trace: Record<string, unknown>
  }
  outcome: {
    success: boolean
    metrics: Record<string, number | string>
  }
  reflection: {
    what_worked: string[]
    what_failed: string[]
    why: string
  }
  reusable_patterns: unknown[]
  confidence_score: number
  provenance: {
    human_signals: unknown[]
    agent_signals: unknown[]
    external_sources: unknown[]
  }
  version: number
  evaluation_status?: string
  created_at?: string
  updated_at?: string
}

export interface ExperienceListResponse {
  items: Experience[]
  total: number
  page: number
  page_size: number
}

export interface SystemMetrics {
  experience_reuse_rate: number
  workflow_success_rate: number
  cross_agent_transfer_rate: number
  external_dependency_ratio: number
  learning_velocity: number
  convergence_speed: number
  human_intervention_rate: number
}

export interface TaskExecution {
  id: string
  status: "pending" | "running" | "completed" | "failed"
  intent: string
  context: Record<string, unknown>
  created_at: string
  updated_at: string
  experience_id?: string
  trace?: Record<string, unknown>
  evaluation?: Record<string, unknown>
}

export interface PipelineStep {
  step: number
  name: string
  status: "pending" | "running" | "completed" | "failed"
  started_at: string
  completed_at: string
  duration_ms: number
  output: unknown
  error: string | null
}

export interface DashboardData {
  system_metrics: SystemMetrics
  experience_stats: {
    total: number
    evaluated: number
    pending: number
    avg_confidence: number
  }
}

export interface SearchResult {
  experience: Experience
  score: number
  matched_factors: Record<string, number>
}

export interface User {
  id: string
  email: string
  username: string
  is_active: boolean
  is_admin: boolean
  bio: string
  created_at: string
  updated_at: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
  user: User
}

export interface Agent {
  id: string
  user_id: string
  name: string
  description: string
  is_active: boolean
  capabilities: Record<string, unknown>
  created_at: string
  last_active_at: string | null
}

export interface AgentWithKey extends Agent {
  api_key: string
}

export interface AdminStats {
  users: { total: number; active: number; admins: number; recent_7d: number }
  agents: { total: number; active: number }
  experiences: { total: number; evaluated: number; pending: number; recent_7d: number }
}

export interface AdminUser {
  id: string
  email: string
  username: string
  is_active: boolean
  is_admin: boolean
  bio: string
  created_at: string
  updated_at: string
}

export interface TrustScoreResponse {
  experience_id: string
  trust_score: number
  metrics: {
    usage_count: number
    success_rate: number
    citation_count: number
    reuse_count: number
    stability: number
  }
}

export interface LineageResponse {
  experience_id: string
  ancestors: Array<{
    relation_id: string
    relation_type: string
    source_experience_id: string
    experience: Experience | null
  }>
  descendants: Array<{
    relation_id: string
    relation_type: string
    target_experience_id: string
    experience: Experience | null
  }>
}

export interface HumanExpression {
  id: string
  user_id: string
  type: string
  content: Record<string, unknown>
  metadata: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface ObserveResult extends HumanExpression {
  similarity: number
}

export interface WorldBridge {
  id: string
  bridge_type: string
  human_expression_id: string
  experience_id: string
  metadata: Record<string, unknown>
  created_by: string
  created_at: string
}
