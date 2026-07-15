import React from "react"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import ExecutionPage from "@/app/(dashboard)/execution/page"
import { executionApi } from "@/lib/api-client"

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

describe("Execution Page", () => {
  it("renders the page heading", () => {
    renderWithQueryClient(<ExecutionPage />)
    expect(screen.getByText("任务执行")).toBeInTheDocument()
  })

  it("renders task intent textarea", () => {
    renderWithQueryClient(<ExecutionPage />)
    expect(
      screen.getByPlaceholderText("例如：将 FastAPI 应用部署到生产环境")
    ).toBeInTheDocument()
  })

  it("renders domain dropdown with all options", () => {
    renderWithQueryClient(<ExecutionPage />)

    // Default value is 运维部署
    const select = screen.getByDisplayValue("运维部署")
    expect(select).toBeInTheDocument()

    const options = screen.getAllByRole("option")
    const optionTexts = options.map((o) => o.textContent)
    expect(optionTexts).toContain("后端开发")
    expect(optionTexts).toContain("前端开发")
    expect(optionTexts).toContain("运维部署")
    expect(optionTexts).toContain("数据处理")
    expect(optionTexts).toContain("测试质量")
    expect(optionTexts).toContain("安全审计")
    expect(optionTexts).toContain("机器学习")
    expect(optionTexts).toContain("综合通用")
  })

  it("renders task type input with default value", () => {
    renderWithQueryClient(<ExecutionPage />)
    expect(screen.getByDisplayValue("部署上线")).toBeInTheDocument()
  })

  it("submit button is disabled when intent is empty", () => {
    renderWithQueryClient(<ExecutionPage />)
    const button = screen.getByRole("button", { name: /执行任务/ })
    expect(button).toBeDisabled()
  })

  it("submit button is enabled when intent is provided", async () => {
    const user = userEvent.setup()
    renderWithQueryClient(<ExecutionPage />)

    const textarea = screen.getByPlaceholderText(
      "例如：将 FastAPI 应用部署到生产环境"
    )
    await user.type(textarea, "部署应用到生产环境")

    const button = screen.getByRole("button", { name: /执行任务/ })
    expect(button).toBeEnabled()
  })

  it("submits task and displays result", async () => {
    const user = userEvent.setup()
    renderWithQueryClient(<ExecutionPage />)

    const textarea = screen.getByPlaceholderText(
      "例如：将 FastAPI 应用部署到生产环境"
    )
    await user.type(textarea, "部署应用到生产环境")
    await user.click(screen.getByRole("button", { name: /执行任务/ }))

    await waitFor(() => {
      expect(screen.getByText("执行结果")).toBeInTheDocument()
    })
    expect(screen.getByText("已完成")).toBeInTheDocument()
    expect(executionApi.submitTask).toHaveBeenCalledWith(
      expect.objectContaining({
        intent: "部署应用到生产环境",
      })
    )
  })

  it("renders available tools section after data loads", async () => {
    renderWithQueryClient(<ExecutionPage />)

    await waitFor(() => {
      expect(screen.getByText(/可用工具/)).toBeInTheDocument()
    })
    expect(screen.getByText("filesystem")).toBeInTheDocument()
    expect(screen.getByText("shell")).toBeInTheDocument()
  })

  it("displays pipeline steps label", () => {
    renderWithQueryClient(<ExecutionPage />)
    // The form section should be visible
    expect(screen.getByText("提交新任务")).toBeInTheDocument()
  })

  it("can change domain selection", async () => {
    const user = userEvent.setup()
    renderWithQueryClient(<ExecutionPage />)

    const select = screen.getByDisplayValue("运维部署")
    await user.selectOptions(select, "后端开发")

    expect(screen.getByDisplayValue("后端开发")).toBeInTheDocument()
  })

  it("can change task type", async () => {
    const user = userEvent.setup()
    renderWithQueryClient(<ExecutionPage />)

    const input = screen.getByDisplayValue("部署上线")
    await user.clear(input)
    await user.type(input, "API开发")

    expect(screen.getByDisplayValue("API开发")).toBeInTheDocument()
  })
})
