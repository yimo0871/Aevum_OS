import type {
  Experience,
  ExperienceListResponse,
  SystemMetrics,
  DashboardData,
  TokenResponse,
  User,
  Agent,
  AgentWithKey,
  AdminStats,
  AdminUser,
  TrustScoreResponse,
  LineageResponse,
  HumanExpression,
  ObserveResult,
  WorldBridge,
} from "@/types"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

async function fetchAPI<T>(path: string, options?: RequestInit): Promise<T> {
  const token = typeof window !== "undefined" ? localStorage.getItem("aevum_token") : null
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options?.headers,
    },
  })
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: `API Error: ${res.status}` }))
    throw new Error(error.detail || `API Error: ${res.status}`)
  }
  // Handle 204 No Content or empty responses
  if (res.status === 204 || res.headers?.get("content-length") === "0") {
    return undefined as T
  }
  return res.json() as Promise<T>
}

export interface Relation {
  id: string
  source_id: string
  target_id: string
  relation_type: string
  weight: number
  metadata: Record<string, unknown>
  created_at: string
}

export interface SearchResult {
  experience: Experience
  score: number
  matched_factors: Record<string, number>
}

export interface ToolInfo {
  name: string
  description: string
}

export interface TaskResult {
  id: string
  status: string
  experience_id?: string
  duration?: number
  error?: string
  pipeline_state?: Record<string, unknown>
}

export interface EvaluationResult {
  overall_score: number
  [key: string]: unknown
}

export interface MetricsResponse {
  metrics: SystemMetrics
  timestamp: string
}

function buildQuery(params: Record<string, unknown>): string {
  const sp = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") {
      sp.append(key, String(value))
    }
  }
  return sp.toString()
}

export const experienceApi = {
  list: (params: {
    page?: number
    page_size?: number
    domain?: string
  }): Promise<ExperienceListResponse> => {
    return fetchAPI<ExperienceListResponse>(
      `/api/v1/experiences?${buildQuery(params)}`
    )
  },

  get: (id: string): Promise<Experience> => {
    return fetchAPI<Experience>(`/api/v1/experiences/${id}`)
  },

  getRelations: (id: string): Promise<Relation[]> => {
    return fetchAPI<Relation[]>(`/api/v1/experiences/${id}/relations`)
  },

  delete: (id: string): Promise<void> => {
    return fetchAPI<void>(`/api/v1/experiences/${id}`, { method: "DELETE" })
  },
}

export const evaluationApi = {
  getDashboard: (): Promise<DashboardData> => {
    return fetchAPI<DashboardData>("/api/v1/evaluation/dashboard")
  },

  getMetrics: (): Promise<MetricsResponse> => {
    return fetchAPI<MetricsResponse>("/api/v1/evaluation/metrics")
  },

  evaluateExperience: (id: string): Promise<EvaluationResult> => {
    return fetchAPI<EvaluationResult>(`/api/v1/evaluation/experiences/${id}`, {
      method: "POST",
    })
  },
}

export const retrievalApi = {
  search: (params: {
    query: string
    domain?: string
    limit?: number
  }): Promise<SearchResult[]> => {
    return fetchAPI<SearchResult[]>(`/api/v1/retrieval/search?${buildQuery(params)}`)
  },
}

export const executionApi = {
  listTools: (): Promise<ToolInfo[]> => {
    return fetchAPI<ToolInfo[]>("/api/v1/execution/tools")
  },

  submitTask: (data: {
    intent: string
    context: {
      domain: string
      task_type: string
      constraints: Record<string, unknown>
    }
  }): Promise<TaskResult> => {
    return fetchAPI<TaskResult>("/api/v1/execution/tasks", {
      method: "POST",
      body: JSON.stringify(data),
    })
  },
}

export const authApi = {
  register: (data: { email: string; username: string; password: string }): Promise<TokenResponse> => {
    return fetchAPI<TokenResponse>("/api/v1/auth/register", {
      method: "POST",
      body: JSON.stringify(data),
    })
  },

  login: (data: { username: string; password: string }): Promise<TokenResponse> => {
    return fetchAPI<TokenResponse>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify(data),
    })
  },

  getMe: (): Promise<User> => {
    return fetchAPI<User>("/api/v1/auth/me")
  },
}

export const adminApi = {
  listUsers: (page = 1, pageSize = 20): Promise<{ items: AdminUser[]; total: number; page: number; page_size: number }> => {
    return fetchAPI(`/api/v1/admin/users?${buildQuery({ page, page_size: pageSize })}`)
  },
  updateUser: (id: string, data: { is_active?: boolean; is_admin?: boolean }): Promise<Partial<AdminUser>> => {
    return fetchAPI(`/api/v1/admin/users/${id}`, { method: "PUT", body: JSON.stringify(data) })
  },
  deleteUser: (id: string): Promise<void> => {
    return fetchAPI<void>(`/api/v1/admin/users/${id}`, { method: "DELETE" })
  },
  listExperiences: (page = 1, pageSize = 20): Promise<{ items: Array<Experience & { user: { id: string; username: string; email: string } | null }>; total: number }> => {
    return fetchAPI(`/api/v1/admin/experiences?${buildQuery({ page, page_size: pageSize })}`)
  },
  deleteExperience: (id: string): Promise<void> => {
    return fetchAPI<void>(`/api/v1/admin/experiences/${id}`, { method: "DELETE" })
  },
  updateExperienceStatus: (id: string, status: string): Promise<{ id: string; evaluation_status: string }> => {
    return fetchAPI(`/api/v1/admin/experiences/${id}/status`, { method: "PUT", body: JSON.stringify({ evaluation_status: status }) })
  },
  getStats: (): Promise<AdminStats> => {
    return fetchAPI("/api/v1/admin/stats")
  },
}

export const agentApi = {
  create: (data: { name: string; description?: string; capabilities?: Record<string, unknown> }): Promise<AgentWithKey> => {
    return fetchAPI("/api/v1/agents", { method: "POST", body: JSON.stringify(data) })
  },
  list: (): Promise<Agent[]> => {
    return fetchAPI("/api/v1/agents")
  },
  delete: (id: string): Promise<void> => {
    return fetchAPI<void>(`/api/v1/agents/${id}`, { method: "DELETE" })
  },
  regenerateKey: (id: string): Promise<AgentWithKey> => {
    return fetchAPI(`/api/v1/agents/${id}/regenerate-key`, { method: "POST" })
  },
}

export const governanceApi = {
  fork: (experienceId: string): Promise<{ forked_experience: Experience; source_id: string }> => {
    return fetchAPI(`/api/v1/governance/experiences/${experienceId}/fork`, { method: "POST" })
  },
  improve: (experienceId: string, improvements: Record<string, unknown>): Promise<{ improved_experience: Experience; source_id: string }> => {
    return fetchAPI(`/api/v1/governance/experiences/${experienceId}/improve`, { method: "POST", body: JSON.stringify({ improvements }) })
  },
  cite: (experienceId: string, citingExperienceId: string): Promise<{ id: string; source_id: string; target_id: string; relation_type: string; weight: number; created_at: string }> => {
    return fetchAPI(`/api/v1/governance/experiences/${experienceId}/cite`, { method: "POST", body: JSON.stringify({ citing_experience_id: citingExperienceId }) })
  },
  getTrust: (experienceId: string): Promise<TrustScoreResponse> => {
    return fetchAPI(`/api/v1/governance/experiences/${experienceId}/trust`)
  },
  getLineage: (experienceId: string): Promise<LineageResponse> => {
    return fetchAPI(`/api/v1/governance/experiences/${experienceId}/lineage`)
  },
}

export const humanApi = {
  createExpression: (data: { type: string; content: Record<string, unknown>; metadata?: Record<string, unknown> }): Promise<HumanExpression> => {
    return fetchAPI("/api/v1/human/expressions", { method: "POST", body: JSON.stringify(data) })
  },
  listExpressions: (page = 1, pageSize = 20, type?: string): Promise<{ items: HumanExpression[]; total: number; page: number; page_size: number }> => {
    return fetchAPI(`/api/v1/human/expressions?${buildQuery({ page, page_size: pageSize, type })}`)
  },
  getExpression: (id: string): Promise<HumanExpression> => {
    return fetchAPI(`/api/v1/human/expressions/${id}`)
  },
  updateExpression: (id: string, data: { content?: Record<string, unknown>; metadata?: Record<string, unknown> }): Promise<HumanExpression> => {
    return fetchAPI(`/api/v1/human/expressions/${id}`, { method: "PUT", body: JSON.stringify(data) })
  },
  deleteExpression: (id: string): Promise<void> => {
    return fetchAPI<void>(`/api/v1/human/expressions/${id}`, { method: "DELETE" })
  },
  observe: (query: string, limit = 5): Promise<ObserveResult[]> => {
    return fetchAPI("/api/v1/human/observe", { method: "POST", body: JSON.stringify({ query, limit }) })
  },
  createBridge: (data: { bridge_type: string; human_expression_id: string; experience_id: string; metadata?: Record<string, unknown> }): Promise<WorldBridge> => {
    return fetchAPI("/api/v1/human/bridge", { method: "POST", body: JSON.stringify(data) })
  },
  listBridges: (params: { human_expression_id?: string; experience_id?: string; bridge_type?: string }): Promise<{ items: WorldBridge[]; total: number }> => {
    return fetchAPI(`/api/v1/human/bridge?${buildQuery(params)}`)
  },
}
