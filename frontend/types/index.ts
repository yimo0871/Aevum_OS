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
