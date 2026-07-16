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

export const authApi = {
  register: jest.fn().mockResolvedValue({
    access_token: "mock-token",
    token_type: "bearer",
    user: {
      id: "user-1",
      email: "test@test.com",
      username: "testuser",
      is_active: true,
      is_admin: false,
      bio: "",
      created_at: "2024-01-01T00:00:00Z",
      updated_at: "2024-01-01T00:00:00Z",
    },
  }),
  login: jest.fn().mockResolvedValue({
    access_token: "mock-token",
    token_type: "bearer",
    user: {
      id: "user-1",
      email: "test@test.com",
      username: "testuser",
      is_active: true,
      is_admin: false,
      bio: "",
      created_at: "2024-01-01T00:00:00Z",
      updated_at: "2024-01-01T00:00:00Z",
    },
  }),
  getMe: jest.fn().mockResolvedValue({
    id: "user-1",
    email: "test@test.com",
    username: "testuser",
    is_active: true,
    is_admin: false,
    bio: "",
    created_at: "2024-01-01T00:00:00Z",
    updated_at: "2024-01-01T00:00:00Z",
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

export const adminApi = {
  listUsers: jest.fn().mockResolvedValue({
    items: [
      { id: "u1", email: "admin@test.com", username: "admin", is_active: true, is_admin: true, bio: "", created_at: "2024-01-01T00:00:00Z", updated_at: "2024-01-01T00:00:00Z" },
    ],
    total: 1, page: 1, page_size: 20,
  }),
  updateUser: jest.fn().mockResolvedValue({ id: "u1", is_active: true, is_admin: false }),
  deleteUser: jest.fn().mockResolvedValue(undefined),
  listExperiences: jest.fn().mockResolvedValue({
    items: [{ id: "e1", intent: "test", context: { domain: "dev" }, evaluation_status: "evaluated", user: { id: "u1", username: "admin", email: "admin@test.com" } }],
    total: 1,
  }),
  deleteExperience: jest.fn().mockResolvedValue(undefined),
  updateExperienceStatus: jest.fn().mockResolvedValue({ id: "e1", evaluation_status: "approved" }),
  getStats: jest.fn().mockResolvedValue({
    users: { total: 10, active: 8, admins: 2, recent_7d: 3 },
    agents: { total: 5, active: 3 },
    experiences: { total: 100, evaluated: 80, pending: 20, recent_7d: 15 },
  }),
}

export const agentApi = {
  create: jest.fn().mockResolvedValue({ id: "a1", user_id: "u1", name: "test-agent", description: "", is_active: true, capabilities: {}, created_at: "2024-01-01T00:00:00Z", last_active_at: null, api_key: "test-key-123" }),
  list: jest.fn().mockResolvedValue([
    { id: "a1", user_id: "u1", name: "test-agent", description: "Test", is_active: true, capabilities: {}, created_at: "2024-01-01T00:00:00Z", last_active_at: null },
  ]),
  delete: jest.fn().mockResolvedValue(undefined),
  regenerateKey: jest.fn().mockResolvedValue({ id: "a1", user_id: "u1", name: "test-agent", description: "", is_active: true, capabilities: {}, created_at: "2024-01-01T00:00:00Z", last_active_at: null, api_key: "new-key-456" }),
}

export const governanceApi = {
  fork: jest.fn().mockResolvedValue({ forked_experience: { id: "e2", intent: "forked" }, source_id: "e1" }),
  improve: jest.fn().mockResolvedValue({ improved_experience: { id: "e3", intent: "improved" }, source_id: "e1" }),
  cite: jest.fn().mockResolvedValue({ id: "r1", source_id: "e1", target_id: "e2", relation_type: "citation", weight: 1.0, created_at: "2024-01-01T00:00:00Z" }),
  getTrust: jest.fn().mockResolvedValue({ experience_id: "e1", trust_score: 0.75, metrics: { usage_count: 10, success_rate: 0.8, citation_count: 5, reuse_count: 3, stability: 0.9 } }),
  getLineage: jest.fn().mockResolvedValue({ experience_id: "e1", ancestors: [], descendants: [{ relation_id: "r1", relation_type: "fork", target_experience_id: "e2", experience: { id: "e2", intent: "forked" } }] }),
}

export const humanApi = {
  createExpression: jest.fn().mockResolvedValue({
    id: "h1", user_id: "u1", type: "text", content: { text: "test" }, metadata: {}, created_at: "2024-01-01T00:00:00Z", updated_at: "2024-01-01T00:00:00Z",
  }),
  listExpressions: jest.fn().mockResolvedValue({
    items: [
      { id: "h1", user_id: "u1", type: "text", content: { text: "hello" }, metadata: {}, created_at: "2024-01-01T00:00:00Z", updated_at: "2024-01-01T00:00:00Z" },
    ],
    total: 1, page: 1, page_size: 20,
  }),
  getExpression: jest.fn().mockResolvedValue({
    id: "h1", user_id: "u1", type: "text", content: { text: "hello" }, metadata: {}, created_at: "2024-01-01T00:00:00Z", updated_at: "2024-01-01T00:00:00Z",
  }),
  updateExpression: jest.fn().mockResolvedValue({
    id: "h1", user_id: "u1", type: "text", content: { text: "updated" }, metadata: {}, created_at: "2024-01-01T00:00:00Z", updated_at: "2024-01-01T00:00:00Z",
  }),
  deleteExpression: jest.fn().mockResolvedValue(undefined),
  observe: jest.fn().mockResolvedValue([
    { id: "h1", user_id: "u1", type: "text", content: { text: "match" }, metadata: {}, created_at: "2024-01-01T00:00:00Z", similarity: 0.85 },
  ]),
  createBridge: jest.fn().mockResolvedValue({
    id: "b1", bridge_type: "inspiration", human_expression_id: "h1", experience_id: "e1", metadata: {}, created_by: "u1", created_at: "2024-01-01T00:00:00Z",
  }),
  listBridges: jest.fn().mockResolvedValue({ items: [], total: 0 }),
}
