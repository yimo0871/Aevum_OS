import React from "react"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import SearchPage from "@/app/(dashboard)/search/page"
import { retrievalApi } from "@/lib/api-client"

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

describe("Search Page", () => {
  it("renders the page heading", () => {
    renderWithQueryClient(<SearchPage />)
    expect(screen.getByText("经验检索")).toBeInTheDocument()
  })

  it("renders search input with placeholder", () => {
    renderWithQueryClient(<SearchPage />)
    expect(
      screen.getByPlaceholderText("输入任务描述、意图关键词...")
    ).toBeInTheDocument()
  })

  it("renders search button", () => {
    renderWithQueryClient(<SearchPage />)
    expect(screen.getByRole("button", { name: "搜索" })).toBeInTheDocument()
  })

  it("renders initial empty state prompt before search", () => {
    renderWithQueryClient(<SearchPage />)
    expect(screen.getByText("输入关键词开始搜索经验库")).toBeInTheDocument()
  })

  it("displays search results after searching", async () => {
    const user = userEvent.setup()
    renderWithQueryClient(<SearchPage />)

    const input = screen.getByPlaceholderText("输入任务描述、意图关键词...")
    await user.type(input, "测试")
    await user.click(screen.getByRole("button", { name: "搜索" }))

    await waitFor(() => {
      expect(screen.getByText("测试意图")).toBeInTheDocument()
    })
    expect(screen.getByText(/找到/)).toBeInTheDocument()
    // score 0.85 -> 85.0%
    expect(screen.getByText("85.0%")).toBeInTheDocument()
  })

  it("displays empty result prompt when no results", async () => {
    // Use mockResolvedValue (not Once) because typing triggers multiple queries
    jest.mocked(retrievalApi.search).mockResolvedValue([])

    const user = userEvent.setup()
    renderWithQueryClient(<SearchPage />)

    const input = screen.getByPlaceholderText("输入任务描述、意图关键词...")
    await user.type(input, "不存在的关键词")
    await user.click(screen.getByRole("button", { name: "搜索" }))

    await waitFor(() => {
      expect(screen.getByText("未找到相关经验")).toBeInTheDocument()
    })
  })

  it("search button is disabled when query is empty", () => {
    renderWithQueryClient(<SearchPage />)
    const button = screen.getByRole("button", { name: "搜索" })
    expect(button).toBeDisabled()
  })

  it("triggers search on Enter key", async () => {
    const user = userEvent.setup()
    renderWithQueryClient(<SearchPage />)

    const input = screen.getByPlaceholderText("输入任务描述、意图关键词...")
    await user.type(input, "测试{Enter}")

    await waitFor(() => {
      expect(retrievalApi.search).toHaveBeenCalled()
    })
  })

  it("renders domain filter dropdown", () => {
    renderWithQueryClient(<SearchPage />)
    const select = screen.getByDisplayValue("全部领域")
    expect(select).toBeInTheDocument()
  })
})
