"use client"

import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { humanApi } from "@/lib/api-client"

export default function HumanPage() {
  const [tab, setTab] = useState<"timeline" | "observe">("timeline")

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold">人类表达</h1>
      <div className="mb-4 flex gap-2 border-b">
        {(["timeline", "observe"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium ${
              tab === t ? "border-b-2 border-blue-600 text-blue-600" : "text-gray-500"
            }`}
          >
            {t === "timeline" ? "时间线" : "语义搜索"}
          </button>
        ))}
      </div>
      {tab === "timeline" && <TimelineTab />}
      {tab === "observe" && <ObserveTab />}
    </div>
  )
}

function TimelineTab() {
  const queryClient = useQueryClient()
  const [type, setType] = useState("text")
  const [contentText, setContentText] = useState("")

  const { data, isLoading } = useQuery({
    queryKey: ["human-expressions"],
    queryFn: () => humanApi.listExpressions(),
  })

  const create = useMutation({
    mutationFn: () =>
      humanApi.createExpression({ type, content: { text: contentText } }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["human-expressions"] })
      setContentText("")
    },
  })

  const deleteExpr = useMutation({
    mutationFn: (id: string) => humanApi.deleteExpression(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["human-expressions"] }),
  })

  return (
    <div>
      <div className="mb-6 rounded-lg border p-4">
        <h2 className="mb-3 font-semibold">新建表达</h2>
        <div className="mb-3 flex gap-3">
          <select
            value={type}
            onChange={(e) => setType(e.target.value)}
            className="rounded-md border px-3 py-2 text-sm"
          >
            <option value="text">文本</option>
            <option value="note">笔记</option>
            <option value="link">链接</option>
            <option value="image">图片</option>
            <option value="video">视频</option>
            <option value="audio">音频</option>
          </select>
          <input
            type="text"
            placeholder="输入内容..."
            value={contentText}
            onChange={(e) => setContentText(e.target.value)}
            className="flex-1 rounded-md border px-3 py-2 text-sm"
          />
          <button
            onClick={() => create.mutate()}
            disabled={!contentText || create.isPending}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
          >
            发布
          </button>
        </div>
      </div>

      {isLoading ? (
        <p className="text-gray-500">加载中...</p>
      ) : (
        <div className="space-y-3">
          {data?.items.map((expr) => (
            <div key={expr.id} className="rounded-lg border p-4">
              <div className="mb-2 flex items-center justify-between">
                <span className="rounded bg-gray-100 px-2 py-0.5 text-xs">{expr.type}</span>
                <span className="text-xs text-gray-500">
                  {expr.created_at ? new Date(expr.created_at).toLocaleString() : ""}
                </span>
              </div>
              <p className="text-sm">
                {typeof expr.content?.text === "string" ? expr.content.text : JSON.stringify(expr.content)}
              </p>
              <button
                onClick={() => deleteExpr.mutate(expr.id)}
                className="mt-2 text-xs text-red-600 hover:underline"
              >
                删除
              </button>
            </div>
          ))}
          {data?.items.length === 0 && (
            <p className="text-gray-500 text-sm">暂无表达</p>
          )}
        </div>
      )}
    </div>
  )
}

function ObserveTab() {
  const [query, setQuery] = useState("")
  const [results, setResults] = useState<Awaited<ReturnType<typeof humanApi.observe>> | null>(null)
  const [searching, setSearching] = useState(false)

  const handleSearch = async () => {
    if (!query) return
    setSearching(true)
    try {
      const res = await humanApi.observe(query)
      setResults(res)
    } finally {
      setSearching(false)
    }
  }

  return (
    <div>
      <div className="mb-4 flex gap-3">
        <input
          type="text"
          placeholder="语义搜索人类表达..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          className="flex-1 rounded-md border px-3 py-2 text-sm"
        />
        <button
          onClick={handleSearch}
          disabled={!query || searching}
          className="rounded-md bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {searching ? "搜索中..." : "搜索"}
        </button>
      </div>
      {results && (
        <div className="space-y-3">
          {results.map((r) => (
            <div key={r.id} className="rounded-lg border p-4">
              <div className="mb-2 flex items-center justify-between">
                <span className="rounded bg-gray-100 px-2 py-0.5 text-xs">{r.type}</span>
                <span className="text-xs text-blue-600">
                  相似度: {(r.similarity * 100).toFixed(1)}%
                </span>
              </div>
              <p className="text-sm">
                {typeof r.content?.text === "string" ? r.content.text : JSON.stringify(r.content)}
              </p>
            </div>
          ))}
          {results.length === 0 && (
            <p className="text-gray-500 text-sm">无匹配结果</p>
          )}
        </div>
      )}
    </div>
  )
}
