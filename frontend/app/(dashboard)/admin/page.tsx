"use client"

import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { adminApi } from "@/lib/api-client"

export default function AdminPage() {
  const [tab, setTab] = useState<"stats" | "users" | "experiences">("stats")

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold">管理后台</h1>
      <div className="mb-4 flex gap-2 border-b">
        {(["stats", "users", "experiences"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium ${
              tab === t ? "border-b-2 border-blue-600 text-blue-600" : "text-gray-500"
            }`}
          >
            {t === "stats" ? "系统统计" : t === "users" ? "用户管理" : "经验审核"}
          </button>
        ))}
      </div>
      {tab === "stats" && <StatsTab />}
      {tab === "users" && <UsersTab />}
      {tab === "experiences" && <ExperiencesTab />}
    </div>
  )
}

function StatsTab() {
  const { data, isLoading } = useQuery({
    queryKey: ["admin-stats"],
    queryFn: () => adminApi.getStats(),
  })

  if (isLoading) return <p className="text-gray-500">加载中...</p>
  if (!data) return <p className="text-gray-500">无数据</p>

  const sections = [
    { title: "用户", items: [
      { label: "总数", value: data.users.total },
      { label: "活跃", value: data.users.active },
      { label: "管理员", value: data.users.admins },
      { label: "近7天新增", value: data.users.recent_7d },
    ]},
    { title: "Agent", items: [
      { label: "总数", value: data.agents.total },
      { label: "活跃", value: data.agents.active },
    ]},
    { title: "经验", items: [
      { label: "总数", value: data.experiences.total },
      { label: "已评估", value: data.experiences.evaluated },
      { label: "待评估", value: data.experiences.pending },
      { label: "近7天新增", value: data.experiences.recent_7d },
    ]},
  ]

  return (
    <div className="grid gap-6 md:grid-cols-3">
      {sections.map((s) => (
        <div key={s.title} className="rounded-lg border p-4">
          <h3 className="mb-3 font-semibold">{s.title}</h3>
          <dl className="space-y-2">
            {s.items.map((item) => (
              <div key={item.label} className="flex justify-between">
                <dt className="text-sm text-gray-600">{item.label}</dt>
                <dd className="text-sm font-medium">{item.value}</dd>
              </div>
            ))}
          </dl>
        </div>
      ))}
    </div>
  )
}

function UsersTab() {
  const queryClient = useQueryClient()
  const { data, isLoading } = useQuery({
    queryKey: ["admin-users"],
    queryFn: () => adminApi.listUsers(),
  })

  const toggleActive = useMutation({
    mutationFn: ({ id, is_active }: { id: string; is_active: boolean }) =>
      adminApi.updateUser(id, { is_active }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin-users"] }),
  })

  if (isLoading) return <p className="text-gray-500">加载中...</p>

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead className="border-b text-left text-gray-600">
          <tr>
            <th className="py-2 pr-4">用户名</th>
            <th className="py-2 pr-4">邮箱</th>
            <th className="py-2 pr-4">状态</th>
            <th className="py-2 pr-4">管理员</th>
            <th className="py-2 pr-4">操作</th>
          </tr>
        </thead>
        <tbody>
          {data?.items.map((u) => (
            <tr key={u.id} className="border-b">
              <td className="py-2 pr-4">{u.username}</td>
              <td className="py-2 pr-4">{u.email}</td>
              <td className="py-2 pr-4">
                <span className={u.is_active ? "text-green-600" : "text-red-600"}>
                  {u.is_active ? "活跃" : "禁用"}
                </span>
              </td>
              <td className="py-2 pr-4">{u.is_admin ? "是" : "否"}</td>
              <td className="py-2 pr-4">
                <button
                  onClick={() => toggleActive.mutate({ id: u.id, is_active: !u.is_active })}
                  className="text-blue-600 hover:underline"
                >
                  {u.is_active ? "禁用" : "激活"}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function ExperiencesTab() {
  const queryClient = useQueryClient()
  const { data, isLoading } = useQuery({
    queryKey: ["admin-experiences"],
    queryFn: () => adminApi.listExperiences(),
  })

  const deleteExp = useMutation({
    mutationFn: (id: string) => adminApi.deleteExperience(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin-experiences"] }),
  })

  if (isLoading) return <p className="text-gray-500">加载中...</p>

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead className="border-b text-left text-gray-600">
          <tr>
            <th className="py-2 pr-4">意图</th>
            <th className="py-2 pr-4">领域</th>
            <th className="py-2 pr-4">用户</th>
            <th className="py-2 pr-4">状态</th>
            <th className="py-2 pr-4">操作</th>
          </tr>
        </thead>
        <tbody>
          {data?.items.map((e) => (
            <tr key={e.id} className="border-b">
              <td className="py-2 pr-4 max-w-xs truncate">{e.intent}</td>
              <td className="py-2 pr-4">{e.context?.domain || "-"}</td>
              <td className="py-2 pr-4">{e.user?.username || "-"}</td>
              <td className="py-2 pr-4">{e.evaluation_status || "-"}</td>
              <td className="py-2 pr-4">
                <button
                  onClick={() => deleteExp.mutate(e.id)}
                  className="text-red-600 hover:underline"
                >
                  删除
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
