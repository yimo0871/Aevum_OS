"use client"

import { create } from "zustand"
import type { User } from "@/types"
import { authApi } from "@/lib/api-client"

interface AuthState {
  token: string | null
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (token: string, user: User) => void
  logout: () => void
  hydrate: () => Promise<void>
}

export const useAuthStore = create<AuthState>((set) => ({
  token: null,
  user: null,
  isAuthenticated: false,
  isLoading: true,
  login: (token, user) => {
    localStorage.setItem("aevum_token", token)
    set({ token, user, isAuthenticated: true, isLoading: false })
  },
  logout: () => {
    localStorage.removeItem("aevum_token")
    set({ token: null, user: null, isAuthenticated: false, isLoading: false })
  },
  hydrate: async () => {
    const token = localStorage.getItem("aevum_token")
    if (token) {
      try {
        const user = await authApi.getMe()
        set({ token, user, isAuthenticated: true, isLoading: false })
      } catch {
        // Token invalid or expired - clear it
        localStorage.removeItem("aevum_token")
        set({ token: null, user: null, isAuthenticated: false, isLoading: false })
      }
    } else {
      set({ isLoading: false })
    }
  },
}))
