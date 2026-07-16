"use client"

import { create } from "zustand"
import type { User } from "@/types"

interface AuthState {
  token: string | null
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (token: string, user: User) => void
  logout: () => void
  hydrate: () => void
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
  hydrate: () => {
    const token = localStorage.getItem("aevum_token")
    if (token) {
      set({ token, isAuthenticated: true, isLoading: false })
    } else {
      set({ isLoading: false })
    }
  },
}))
