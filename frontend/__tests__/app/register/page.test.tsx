import React from "react"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import RegisterPage from "@/app/register/page"

// Mock next/navigation
const mockPush = jest.fn()
jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}))

// Mock api-client
const mockRegister = jest.fn()
jest.mock("@/lib/api-client", () => ({
  authApi: {
    register: (...args: unknown[]) => mockRegister(...args),
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
    emailInput: inputs[0] as HTMLInputElement,
    usernameInput: inputs[1] as HTMLInputElement,
    passwordInput: inputs[2] as HTMLInputElement,
    confirmPasswordInput: inputs[3] as HTMLInputElement,
    submitButton: container.querySelector('button[type="submit"]') as HTMLButtonElement,
  }
}

describe("Register Page", () => {
  it("renders register form with submit button", () => {
    render(<RegisterPage />)
    expect(screen.getByRole("button", { name: /注/ })).toBeInTheDocument()
    expect(screen.getByRole("link", { name: /登/ })).toBeInTheDocument()
  })

  it("shows error when passwords do not match", async () => {
    const user = userEvent.setup()
    const { container } = render(<RegisterPage />)
    const { emailInput, usernameInput, passwordInput, confirmPasswordInput, submitButton } = getInputs(container)

    await user.type(emailInput, "test@test.com")
    await user.type(usernameInput, "testuser")
    await user.type(passwordInput, "password123")
    await user.type(confirmPasswordInput, "different123")
    await user.click(submitButton)

    // Should show password mismatch error (contains the text)
    expect(container.querySelector(".bg-red-50")).toBeInTheDocument()
    expect(mockRegister).not.toHaveBeenCalled()
  })

  it("submits register form and redirects on success", async () => {
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
    mockRegister.mockResolvedValueOnce({
      access_token: "test-token",
      token_type: "bearer",
      user: mockUser,
    })

    const { container } = render(<RegisterPage />)
    const { emailInput, usernameInput, passwordInput, confirmPasswordInput, submitButton } = getInputs(container)

    await user.type(emailInput, "test@test.com")
    await user.type(usernameInput, "testuser")
    await user.type(passwordInput, "password123")
    await user.type(confirmPasswordInput, "password123")
    await user.click(submitButton)

    await waitFor(() => {
      expect(mockRegister).toHaveBeenCalledWith({
        email: "test@test.com",
        username: "testuser",
        password: "password123",
      })
    })
    expect(mockStoreLogin).toHaveBeenCalledWith("test-token", mockUser)
    expect(mockPush).toHaveBeenCalledWith("/")
  })
})
