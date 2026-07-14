import Link from "next/link"

const navItems = [
  { href: "/", label: "Dashboard" },
  { href: "/experiences", label: "经验管理" },
  { href: "/search", label: "经验检索" },
  { href: "/execution", label: "任务执行" },
  { href: "/metrics", label: "指标监控" },
]

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
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
      </aside>
      <main className="flex-1 p-8">{children}</main>
    </div>
  )
}
