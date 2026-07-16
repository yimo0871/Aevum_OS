"use client"

import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { agentApi } from "@/lib/api-client"

export default function AgentsPage() {
  const [name, setName] = useState("")
  const [description, setDescription] = useState("")
  const [newKey, setNewKey] = useState<string | null>(null)
  const queryClient = useQueryClient()

  const { data: agents, isLoading } = useQuery({
    queryKey: ["agents"],
    queryFn: () => agentApi.list(),
  })

  const createAgent = useMutation({
    mutationFn: () => agentApi.create({ name, description }),
    onSuccess: (data) => {
      setNewKey(data.api_key)
      setName("")
      setDescription("")
      queryClient.invalidateQueries({ queryKey: ["agents"] })
    },
  })

  const deleteAgent = useMutation({
    mutationFn: (id: string) => agentApi.delete(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["agents"] }),
  })

  const regenerate = useMutation({
    mutationFn: (id: string) => agentApi.regenerateKey(id),
    onSuccess: (data) => setNewKey(data.api_key),
  })

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold">Agent 管理</h1>

      {newKey && (
        <div className="mb-4 rounded-md bg-yellow-50 p-4">
          <p className="text-sm font-medium text-yellow-800">API Key（仅显示一次，请妥善保存）:</p>
          <code className="mt-2 block break-all bg-yellow-100 p-2 text-xs">{newKey}</code>
          <button onClick={() => setNewKey(null)} className="mt-2 text-xs text-yellow-700 hover:underline">
            关闭
          </button>
        </div>
      )}

      <div className="mb-6 rounded-lg border p-4">
        <h2 className="mb-3 font-semibold">注册新 Agent</h2>
        <div className="flex gap-3">
          <input
            type="text"
            placeholder="Agent 名称"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="flex-1 rounded-md border px-3 py-2 text-sm"
          />
          <input
            type="text"
            placeholder="描述（可选）"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="flex-1 rounded-md border px-3 py-2 text-sm"
          />
          <button
            onClick={() => createAgent.mutate()}
            disabled={!name || createAgent.isPending}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
          >
            注册
          </button>
        </div>
      </div>

      {isLoading ? (
        <p className="text-gray-500">加载中...</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="border-b text-left text-gray-600">
              <tr>
                <th className="py-2 pr-4">名称</th>
                <th className="py-2 pr-4">描述</th>
                <th className="py-2 pr-4">状态</th>
                <th className="py-2 pr-4">创建时间</th>
                <th className="py-2 pr-4">操作</th>
              </tr>
            </thead>
            <tbody>
              {agents?.map((a) => (
                <tr key={a.id} className="border-b">
                  <td className="py-2 pr-4">{a.name}</td>
                  <td className="py-2 pr-4 max-w-xs truncate">{a.description || "-"}</td>
                  <td className="py-2 pr-4">
                    <span className={a.is_active ? "text-green-600" : "text-gray-500"}>
                      {a.is_active ? "活跃" : "停用"}
                    </span>
                  </td>
                  <td className="py-2 pr-4 text-xs text-gray-500">
                    {a.created_at ? new Date(a.created_at).toLocaleDateString() : "-"}
                  </td>
                  <td className="py-2 pr-4 space-x-2">
                    <button
                      onClick={() => regenerate.mutate(a.id)}
                      className="text-blue-600 hover:underline"
                    >
                      重置Key
                    </button>
                    <button
                      onClick={() => deleteAgent.mutate(a.id)}
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
      )}
    </div>
  )
}
