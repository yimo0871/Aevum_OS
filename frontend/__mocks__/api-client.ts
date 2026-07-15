// Mock data for API client - used in tests via jest.mock('@/lib/api-client', () => require('__mocks__/api-client'))

const mockExperience = {
  id: "test-1",
  timestamp: "2024-01-01T00:00:00Z",
  intent: "测试意图",
  context: {
    domain: "后端开发",
    task_type: "API设计",
    constraints: { time_limit: 30, resource_limit: "中" },
  },
  execution: {
    steps: [{ name: "步骤1" }, { name: "步骤2" }],
    tools: ["tool-a", "tool-b"],
    trace: {},
  },
  outcome: {
    success: true,
    metrics: { duration_ms: 1000 },
  },
  reflection: {
    what_worked: ["标准流程"],
    what_failed: [],
    why: "按标准流程执行，无异常",
  },
  reusable_patterns: [],
  confidence_score: 0.8,
  provenance: {
    human_signals: [],
    agent_signals: [{ type: "auto" }],
    external_sources: [],
  },
  version: 1,
  evaluation_status: "evaluated",
  created_at: "2024-01-01T00:00:00Z",
  updated_at: "2024-01-01T00:00:00Z",
}

export const experienceApi = {
  list: jest.fn().mockResolvedValue({
    items: [mockExperience],
    total: 1,
    page: 1,
    page_size: 20,
  }),
  get: jest.fn().mockResolvedValue(mockExperience),
  getById: jest.fn().mockResolvedValue(mockExperience),
  getRelations: jest.fn().mockResolvedValue([
    {
      id: "rel-1",
      source_id: "test-1",
      target_id: "test-2",
      relation_type: "reuse",
      weight: 0.8,
      metadata: {},
      created_at: "2024-01-01T00:00:00Z",
    },
  ]),
  delete: jest.fn().mockResolvedValue(undefined),
}

export const evaluationApi = {
  getDashboard: jest.fn().mockResolvedValue({
    system_metrics: {
      experience_reuse_rate: 0.3,
      workflow_success_rate: 0.75,
      cross_agent_transfer_rate: 0.5,
      external_dependency_ratio: 0.2,
      learning_velocity: 10,
      convergence_speed: 0.9,
      human_intervention_rate: 0.1,
    },
    experience_stats: {
      total: 10000,
      evaluated: 10000,
      pending: 0,
      avg_confidence: 0.49,
    },
  }),
  getMetrics: jest.fn().mockResolvedValue({
    metrics: {
      experience_reuse_rate: 0.3,
      workflow_success_rate: 0.75,
      cross_agent_transfer_rate: 0.5,
      external_dependency_ratio: 0.2,
      learning_velocity: 10,
      convergence_speed: 0.9,
      human_intervention_rate: 0.1,
    },
    timestamp: "2024-01-01T00:00:00Z",
  }),
  evaluateExperience: jest.fn().mockResolvedValue({
    overall_score: 0.85,
    details: { quality: 0.9, relevance: 0.8 },
  }),
}

export const retrievalApi = {
  search: jest.fn().mockResolvedValue([
    {
      experience: mockExperience,
      score: 0.85,
      matched_factors: { intent: 0.5, context: 0.3 },
    },
  ]),
}

export const executionApi = {
  listTools: jest.fn().mockResolvedValue([
    { name: "filesystem", description: "文件系统操作工具" },
    { name: "shell", description: "Shell 命令执行工具" },
  ]),
  submitTask: jest.fn().mockResolvedValue({
    id: "task-1",
    status: "completed",
    experience_id: "exp-1",
    duration: 5.23,
  }),
}

// Keep workflowApi for backward compatibility with task spec
export const workflowApi = {
  submit: jest.fn().mockResolvedValue({
    id: "task-1",
    status: "completed",
    result: { experience_id: "exp-1" },
  }),
  getStatus: jest.fn().mockResolvedValue({
    id: "task-1",
    status: "completed",
    steps: [],
  }),
}

export type Relation = {
  id: string
  source_id: string
  target_id: string
  relation_type: string
  weight: number
  metadata: Record<string, unknown>
  created_at: string
}

export type SearchResult = {
  experience: typeof mockExperience
  score: number
  matched_factors: Record<string, number>
}

export type ToolInfo = {
  name: string
  description: string
}
