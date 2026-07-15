import React from "react"
import { render, screen, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import MetricsPage from "@/app/(dashboard)/metrics/page"

jest.mock("@/lib/api-client", () => require("__mocks__/api-client"))

function renderWithQueryClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
  )
}

beforeEach(() => {
  jest.clearAllMocks()
})

describe("Metrics Page", () => {
  it("renders the page heading", async () => {
    renderWithQueryClient(<MetricsPage />)
    expect(screen.getByText("指标监控")).toBeInTheDocument()
  })

  it("renders auto-refresh label", async () => {
    renderWithQueryClient(<MetricsPage />)

    // "每 15 秒自动刷新" only renders after data loads (not in loading state)
    // Wait for it to appear
    await waitFor(() => {
      expect(screen.getByText("每 15 秒自动刷新")).toBeInTheDocument()
    })
  })

  it("renders all metric cards after data loads", async () => {
    renderWithQueryClient(<MetricsPage />)

    await waitFor(() => {
      // "经验复用率" appears both as a metric card label and in the explanation section
      expect(screen.getAllByText("经验复用率").length).toBeGreaterThanOrEqual(1)
    })
    expect(screen.getAllByText("工作流成功率").length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText("跨Agent迁移率").length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText("外部依赖比例").length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText("学习速度").length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText("收敛速度").length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText("人类干预率").length).toBeGreaterThanOrEqual(1)
  })

  it("displays formatted metric values", async () => {
    renderWithQueryClient(<MetricsPage />)

    await waitFor(() => {
      // experience_reuse_rate 0.3 -> 30.00%
      expect(screen.getByText("30.00%")).toBeInTheDocument()
    })
    // workflow_success_rate 0.75 -> 75.00%
    expect(screen.getByText("75.00%")).toBeInTheDocument()
    // learning_velocity 10 -> 10.00/天
    expect(screen.getByText("10.00/天")).toBeInTheDocument()
  })

  it("renders metric explanation section", async () => {
    renderWithQueryClient(<MetricsPage />)

    await waitFor(() => {
      expect(screen.getByText("指标说明")).toBeInTheDocument()
    })
    expect(
      screen.getByText("被复用的经验数占总经验数的比例，越高说明经验价值越大")
    ).toBeInTheDocument()
  })

  it("shows '越低越好' for inverse metrics", async () => {
    renderWithQueryClient(<MetricsPage />)

    await waitFor(() => {
      const labels = screen.getAllByText("越低越好")
      // external_dependency_ratio and human_intervention_rate
      expect(labels.length).toBe(2)
    })
  })
})
