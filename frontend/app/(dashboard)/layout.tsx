"use client"

import { useEffect } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { useAuthStore } from "@/lib/auth-store"

const navItems = [
  { href: "/", label: "Dashboard" },
  { href: "/experiences", label: "经验管理" },
  { href: "/search", label: "经验检索" },
  { href: "/execution", label: "任务执行" },
  { href: "/metrics", label: "指标监控" },
  { href: "/agents", label: "Agent 管理" },
  { href: "/governance", label: "经验治理" },
  { href: "/human", label: "人类表达" },
]

const adminNavItems = [
  { href: "/admin", label: "管理后台" },
]

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const router = useRouter()
  const { isAuthenticated, isLoading, user, logout, hydrate } = useAuthStore()

  useEffect(() => {
    hydrate()
  }, [hydrate])

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push("/login")
    }
  }, [isLoading, isAuthenticated, router])

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-gray-500">加载中...</p>
      </div>
    )
  }

  if (!isAuthenticated) {
    return null
  }

  return (
    <div className="flex min-h-screen">
      <aside className="w-64 border-r bg-gray-50 p-4">
        <div className="mb-8">
          <h2 className="text-xl font-bold">Aevum / 薪火</h2>
          <p className="text-xs text-gray-500">Experience OS</p>
        </div>
        <nav className="space-y-2">
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="block rounded-md px-3 py-2 text-sm font-medium text-gray-600 hover:bg-gray-200 hover:text-gray-900"
            >
              {item.label}
            </Link>
          ))}
        </nav>
        {user?.is_admin && (
          <div className="mt-4 border-t pt-2">
            <p className="mb-1 px-3 text-xs text-gray-400">管理</p>
            {adminNavItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="block rounded-md px-3 py-2 text-sm font-medium text-gray-600 hover:bg-gray-200 hover:text-gray-900"
              >
                {item.label}
              </Link>
            ))}
          </div>
        )}
        {user && (
          <div className="mt-8 border-t pt-4">
            <p className="text-sm font-medium text-gray-700">{user.username}</p>
            <p className="text-xs text-gray-500">{user.email}</p>
            <button
              onClick={() => {
                logout()
                router.push("/login")
              }}
              className="mt-2 text-xs text-red-600 hover:underline"
            >
              退出登录
            </button>
          </div>
        )}
      </aside>
      <main className="flex-1 p-8">{children}</main>
    </div>
  )
}
