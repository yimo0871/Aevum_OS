import React from "react"
import { render, screen, waitFor, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import ExperiencesPage from "@/app/(dashboard)/experiences/page"
import { experienceApi } from "@/lib/api-client"

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

describe("Experiences Page", () => {
  it("renders the page heading", async () => {
    renderWithQueryClient(<ExperiencesPage />)
    expect(screen.getByText("经验管理")).toBeInTheDocument()
  })

  it("renders total experience count", async () => {
    renderWithQueryClient(<ExperiencesPage />)

    await waitFor(() => {
      expect(screen.getByText(/共.*条经验/)).toBeInTheDocument()
    })
  })

  it("renders the experience list with data", async () => {
    renderWithQueryClient(<ExperiencesPage />)

    await waitFor(() => {
      expect(screen.getByText("测试意图")).toBeInTheDocument()
    })
    // "后端开发" appears both as a dropdown option and a span in the list item
    expect(screen.getAllByText("后端开发").length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText("API设计")).toBeInTheDocument()
    expect(screen.getByText("成功")).toBeInTheDocument()
    expect(screen.getByText("已评估")).toBeInTheDocument()
  })

  it("renders domain filter dropdown with all options", async () => {
    renderWithQueryClient(<ExperiencesPage />)

    await waitFor(() => {
      expect(screen.getByDisplayValue("全部领域")).toBeInTheDocument()
    })

    const select = screen.getByDisplayValue("全部领域")
    const options = within(select).getAllByRole("option")
    const optionTexts = options.map((o) => o.textContent)

    expect(optionTexts).toContain("全部领域")
    expect(optionTexts).toContain("后端开发")
    expect(optionTexts).toContain("前端开发")
    expect(optionTexts).toContain("运维部署")
    expect(optionTexts).toContain("数据处理")
    expect(optionTexts).toContain("测试质量")
    expect(optionTexts).toContain("安全审计")
    expect(optionTexts).toContain("机器学习")
    expect(optionTexts).toContain("综合通用")
  })

  it("shows confidence score", async () => {
    renderWithQueryClient(<ExperiencesPage />)

    await waitFor(() => {
      // confidence_score 0.8 -> 80%
      expect(screen.getByText("80%")).toBeInTheDocument()
    })
  })

  it("calls list with domain filter when selected", async () => {
    const user = userEvent.setup()
    renderWithQueryClient(<ExperiencesPage />)

    await waitFor(() => {
      expect(screen.getByDisplayValue("全部领域")).toBeInTheDocument()
    })

    const select = screen.getByDisplayValue("全部领域")
    await user.selectOptions(select, "前端开发")

    expect(experienceApi.list).toHaveBeenCalledWith(
      expect.objectContaining({ domain: "前端开发" })
    )
  })

  it("shows pagination when total > 20", async () => {
    jest.mocked(experienceApi.list).mockResolvedValueOnce({
      items: [
        {
          id: "exp-page",
          timestamp: "2024-01-01T00:00:00Z",
          intent: "分页测试经验",
          context: { domain: "后端开发", task_type: "API设计", constraints: {} },
          execution: { steps: [], tools: [], trace: {} },
          outcome: { success: true, metrics: {} },
          reflection: { what_worked: [], what_failed: [], why: "" },
          reusable_patterns: [],
          confidence_score: 0.5,
          provenance: { human_signals: [], agent_signals: [], external_sources: [] },
          version: 1,
          evaluation_status: "evaluated",
          created_at: "2024-01-01T00:00:00Z",
          updated_at: "2024-01-01T00:00:00Z",
        },
      ],
      total: 30,
      page: 1,
      page_size: 20,
    })

    renderWithQueryClient(<ExperiencesPage />)

    await waitFor(() => {
      expect(screen.getByText("上一页")).toBeInTheDocument()
    })
    expect(screen.getByText("下一页")).toBeInTheDocument()
    expect(screen.getByText(/第 1 页/)).toBeInTheDocument()
  })

  it("renders search input", async () => {
    renderWithQueryClient(<ExperiencesPage />)

    await waitFor(() => {
      expect(screen.getByPlaceholderText("搜索经验...")).toBeInTheDocument()
    })
  })
})
