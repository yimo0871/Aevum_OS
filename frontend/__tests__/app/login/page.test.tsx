import React from "react"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import LoginPage from "@/app/login/page"

// Mock next/navigation
const mockPush = jest.fn()
jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}))

// Mock api-client
const mockLogin = jest.fn()
jest.mock("@/lib/api-client", () => ({
  authApi: {
    login: (...args: unknown[]) => mockLogin(...args),
  },
}))

// Mock auth-store
const mockStoreLogin = jest.fn()
jest.mock("@/lib/auth-store", () => ({
  useAuthStore: (selector: (s: { login: typeof mockStoreLogin }) => unknown) => selector({ login: mockStoreLogin }),
}))

beforeEach(() => {
  jest.clearAllMocks()
})

function getInputs(container: HTMLElement) {
  const inputs = container.querySelectorAll("input")
  return {
    usernameInput: inputs[0] as HTMLInputElement,
    passwordInput: inputs[1] as HTMLInputElement,
    submitButton: container.querySelector('button[type="submit"]') as HTMLButtonElement,
  }
}

describe("Login Page", () => {
  it("renders login form with heading", () => {
    render(<LoginPage />)
    expect(screen.getByRole("button", { name: /登/ })).toBeInTheDocument()
    expect(screen.getByRole("link", { name: /注/ })).toBeInTheDocument()
  })

  it("submits login form and redirects on success", async () => {
    const user = userEvent.setup()
    const mockUser = {
      id: "user-1",
      email: "test@test.com",
      username: "testuser",
      is_active: true,
      is_admin: false,
      bio: "",
      created_at: "2024-01-01T00:00:00Z",
      updated_at: "2024-01-01T00:00:00Z",
    }
    mockLogin.mockResolvedValueOnce({
      access_token: "test-token",
      token_type: "bearer",
      user: mockUser,
    })

    const { container } = render(<LoginPage />)
    const { usernameInput, passwordInput, submitButton } = getInputs(container)

    await user.type(usernameInput, "testuser")
    await user.type(passwordInput, "password123")
    await user.click(submitButton)

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith({
        username: "testuser",
        password: "password123",
      })
    })
    expect(mockStoreLogin).toHaveBeenCalledWith("test-token", mockUser)
    expect(mockPush).toHaveBeenCalledWith("/")
  })

  it("displays error message on login failure", async () => {
    const user = userEvent.setup()
    mockLogin.mockRejectedValueOnce(new Error("Login failed"))

    const { container } = render(<LoginPage />)
    const { usernameInput, passwordInput, submitButton } = getInputs(container)

    await user.type(usernameInput, "wrong")
    await user.type(passwordInput, "wrongpass")
    await user.click(submitButton)

    await waitFor(() => {
      expect(screen.getByText("Login failed")).toBeInTheDocument()
    })
    expect(mockPush).not.toHaveBeenCalled()
  })
})
