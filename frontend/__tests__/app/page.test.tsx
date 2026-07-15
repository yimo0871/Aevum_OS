import React from "react"
import { render, screen, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import DashboardPage from "@/app/(dashboard)/page"

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

describe("Dashboard Page", () => {
  it("renders the page heading", async () => {
    renderWithQueryClient(<DashboardPage />)
    expect(screen.getByText("Dashboard")).toBeInTheDocument()
  })

  it("renders statistics cards after data loads", async () => {
    renderWithQueryClient(<DashboardPage />)

    await waitFor(() => {
      expect(screen.getByText("经验总数")).toBeInTheDocument()
    })
    expect(screen.getByText("已评估")).toBeInTheDocument()
    expect(screen.getByText("待评估")).toBeInTheDocument()
    expect(screen.getByText("平均置信度")).toBeInTheDocument()
  })

  it("renders system metrics section", async () => {
    renderWithQueryClient(<DashboardPage />)

    await waitFor(() => {
      expect(screen.getByText("系统指标")).toBeInTheDocument()
    })
  })

  it("renders metric labels", async () => {
    renderWithQueryClient(<DashboardPage />)

    await waitFor(() => {
      expect(screen.getByText("经验复用率")).toBeInTheDocument()
    })
    expect(screen.getByText("工作流成功率")).toBeInTheDocument()
    expect(screen.getByText("跨Agent迁移率")).toBeInTheDocument()
    expect(screen.getByText("外部依赖比例")).toBeInTheDocument()
    expect(screen.getByText("学习速度")).toBeInTheDocument()
    expect(screen.getByText("收敛速度")).toBeInTheDocument()
    expect(screen.getByText("人类干预率")).toBeInTheDocument()
  })

  it("displays correct stat values from mock data", async () => {
    renderWithQueryClient(<DashboardPage />)

    await waitFor(() => {
      // "10000" appears for both 经验总数 and 已评估 (both are 10000 in mock data)
      expect(screen.getAllByText("10000").length).toBeGreaterThanOrEqual(1)
    })
    // avg confidence 0.49 -> 49.0%
    expect(screen.getByText("49.0%")).toBeInTheDocument()
  })

  it("displays formatted metric values", async () => {
    renderWithQueryClient(<DashboardPage />)

    await waitFor(() => {
      // experience_reuse_rate 0.3 -> 30.0%
      expect(screen.getByText("30.0%")).toBeInTheDocument()
    })
    // learning_velocity 10 -> 10.0/天
    expect(screen.getByText("10.0/天")).toBeInTheDocument()
  })

  it("shows '越低越好' for inverse metrics", async () => {
    renderWithQueryClient(<DashboardPage />)

    await waitFor(() => {
      const labels = screen.getAllByText("越低越好")
      // external_dependency_ratio and human_intervention_rate
      expect(labels.length).toBeGreaterThanOrEqual(1)
    })
  })
})
