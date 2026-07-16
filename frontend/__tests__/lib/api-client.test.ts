/**
 * Test the real API client implementation (lib/api-client.ts)
 * Mocks global.fetch and verifies correct API calls
 */

// Do NOT mock @/lib/api-client here — we test the real implementation

const mockFetch = jest.fn() as jest.MockedFunction<typeof fetch>
global.fetch = mockFetch

function jsonResponse(data: unknown): Response {
  return {
    ok: true,
    status: 200,
    json: async () => data,
  } as Response
}

beforeEach(() => {
  mockFetch.mockClear()
})

describe("experienceApi", () => {
  it("list calls correct endpoint with query params", async () => {
    const { experienceApi } = await import("@/lib/api-client")
    mockFetch.mockResolvedValueOnce(
      jsonResponse({ items: [], total: 0, page: 1, page_size: 20 })
    )

    await experienceApi.list({ page: 2, page_size: 10, domain: "后端开发" })

    expect(mockFetch).toHaveBeenCalledTimes(1)
    const url = mockFetch.mock.calls[0][0] as string
    expect(url).toContain("/api/v1/experiences")
    expect(url).toContain("page=2")
    expect(url).toContain("page_size=10")
    expect(url).toContain("domain=")
  })

  it("list omits empty/undefined params", async () => {
    const { experienceApi } = await import("@/lib/api-client")
    mockFetch.mockResolvedValueOnce(
      jsonResponse({ items: [], total: 0, page: 1, page_size: 20 })
    )

    await experienceApi.list({ page: 1, page_size: 20, domain: "" })

    const url = mockFetch.mock.calls[0][0] as string
    expect(url).not.toContain("domain=")
  })

  it("get calls correct endpoint", async () => {
    const { experienceApi } = await import("@/lib/api-client")
    mockFetch.mockResolvedValueOnce(jsonResponse({ id: "123", intent: "test" }))

    await experienceApi.get("123")

    const url = mockFetch.mock.calls[0][0] as string
    expect(url).toContain("/api/v1/experiences/123")
  })

  it("getRelations calls correct endpoint", async () => {
    const { experienceApi } = await import("@/lib/api-client")
    mockFetch.mockResolvedValueOnce(jsonResponse([]))

    await experienceApi.getRelations("abc")

    const url = mockFetch.mock.calls[0][0] as string
    expect(url).toContain("/api/v1/experiences/abc/relations")
  })

  it("delete calls DELETE method", async () => {
    const { experienceApi } = await import("@/lib/api-client")
    mockFetch.mockResolvedValueOnce(jsonResponse(undefined))

    await experienceApi.delete("xyz")

    const options = mockFetch.mock.calls[0][1] as RequestInit
    expect(options?.method).toBe("DELETE")
  })
})

describe("evaluationApi", () => {
  it("getDashboard calls correct endpoint", async () => {
    const { evaluationApi } = await import("@/lib/api-client")
    mockFetch.mockResolvedValueOnce(jsonResponse({ system_metrics: {}, experience_stats: {} }))

    await evaluationApi.getDashboard()

    const url = mockFetch.mock.calls[0][0] as string
    expect(url).toContain("/api/v1/evaluation/dashboard")
  })

  it("getMetrics calls correct endpoint", async () => {
    const { evaluationApi } = await import("@/lib/api-client")
    mockFetch.mockResolvedValueOnce(jsonResponse({ metrics: {}, timestamp: "" }))

    await evaluationApi.getMetrics()

    const url = mockFetch.mock.calls[0][0] as string
    expect(url).toContain("/api/v1/evaluation/metrics")
  })

  it("evaluateExperience calls POST method", async () => {
    const { evaluationApi } = await import("@/lib/api-client")
    mockFetch.mockResolvedValueOnce(jsonResponse({ overall_score: 0.9 }))

    await evaluationApi.evaluateExperience("exp-1")

    const url = mockFetch.mock.calls[0][0] as string
    const options = mockFetch.mock.calls[0][1] as RequestInit
    expect(url).toContain("/api/v1/evaluation/experiences/exp-1")
    expect(options?.method).toBe("POST")
  })
})

describe("retrievalApi", () => {
  it("search calls correct endpoint with query params", async () => {
    const { retrievalApi } = await import("@/lib/api-client")
    mockFetch.mockResolvedValueOnce(jsonResponse([]))

    await retrievalApi.search({ query: "test", domain: "后端开发", limit: 10 })

    const url = mockFetch.mock.calls[0][0] as string
    expect(url).toContain("/api/v1/retrieval/search")
    expect(url).toContain("query=test")
    expect(url).toContain("limit=10")
  })
})

describe("executionApi", () => {
  it("listTools calls correct endpoint", async () => {
    const { executionApi } = await import("@/lib/api-client")
    mockFetch.mockResolvedValueOnce(jsonResponse([]))

    await executionApi.listTools()

    const url = mockFetch.mock.calls[0][0] as string
    expect(url).toContain("/api/v1/execution/tools")
  })

  it("submitTask calls POST with JSON body", async () => {
    const { executionApi } = await import("@/lib/api-client")
    mockFetch.mockResolvedValueOnce(jsonResponse({ id: "t1", status: "completed" }))

    await executionApi.submitTask({
      intent: "部署应用",
      context: { domain: "运维部署", task_type: "部署上线", constraints: {} },
    })

    const url = mockFetch.mock.calls[0][0] as string
    const options = mockFetch.mock.calls[0][1] as RequestInit
    expect(url).toContain("/api/v1/execution/tasks")
    expect(options?.method).toBe("POST")
    expect(options?.body).toBeDefined()
    const body = JSON.parse(options?.body as string)
    expect(body.intent).toBe("部署应用")
  })
})

describe("fetchAPI error handling", () => {
  it("throws on non-ok response", async () => {
    const { experienceApi } = await import("@/lib/api-client")
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: async () => ({}),
    } as Response)

    await expect(experienceApi.get("err")).rejects.toThrow("API Error: 500")
  })
})
