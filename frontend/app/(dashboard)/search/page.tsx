"use client"

import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { retrievalApi, type SearchResult } from "@/lib/api-client"
import { Search, Database, TrendingUp, ChevronRight } from "lucide-react"
import Link from "next/link"

const domains = ["", "后端开发", "前端开发", "运维部署", "数据处理", "测试质量", "安全审计", "机器学习", "综合通用"]

export default function SearchPage() {
  const [query, setQuery] = useState("")
  const [domain, setDomain] = useState("")
  const [searchKey, setSearchKey] = useState(0)

  const { data: results, isLoading, isFetching } = useQuery({
    queryKey: ["search", query, domain, searchKey],
    queryFn: () => retrievalApi.search({
      query,
      domain: domain || undefined,
      limit: 20,
    }),
    enabled: query.length > 0,
  })

  const handleSearch = () => {
    if (query.trim()) setSearchKey(k => k + 1)
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">经验检索</h1>

      {/* 搜索栏 */}
      <div className="flex gap-3 mb-6">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            placeholder="输入任务描述、意图关键词..."
            className="w-full pl-10 pr-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <select
          value={domain}
          onChange={(e) => setDomain(e.target.value)}
          className="px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          {domains.map(d => (
            <option key={d} value={d}>{d || "全部领域"}</option>
          ))}
        </select>
        <button
          onClick={handleSearch}
          disabled={!query.trim() || isFetching}
          className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isFetching ? "搜索中..." : "搜索"}
        </button>
      </div>

      {/* 搜索结果 */}
      {isLoading && (
        <div className="text-center py-12 text-gray-400">
          <div className="animate-pulse">正在检索经验库...</div>
        </div>
      )}

      {!isLoading && !results && (
        <div className="text-center py-12">
          <Database className="w-12 h-12 text-gray-300 mx-auto mb-4" />
          <p className="text-gray-400">输入关键词开始搜索经验库</p>
          <p className="text-sm text-gray-400 mt-2">共 1001 条已评估经验可供检索</p>
        </div>
      )}

      {results && results.length === 0 && (
        <div className="text-center py-12">
          <p className="text-gray-400">未找到相关经验</p>
        </div>
      )}

      {results && results.length > 0 && (
        <div>
          <p className="text-sm text-gray-500 mb-4">
            找到 <span className="font-semibold text-gray-700">{results.length}</span> 条相关经验
          </p>
          <div className="space-y-3">
            {results.map((result: SearchResult, idx: number) => (
              <Link
                key={idx}
                href={`/experiences/${result.experience.id}`}
                className="block rounded-lg border p-4 hover:border-blue-300 hover:bg-blue-50 transition-colors"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs px-2 py-0.5 rounded bg-gray-100 text-gray-600">
                        {result.experience.context.domain}
                      </span>
                      <span className="text-xs px-2 py-0.5 rounded bg-gray-100 text-gray-600">
                        {result.experience.context.task_type}
                      </span>
                      {result.experience.outcome.success ? (
                        <span className="text-xs px-2 py-0.5 rounded bg-green-100 text-green-700">成功</span>
                      ) : (
                        <span className="text-xs px-2 py-0.5 rounded bg-red-100 text-red-700">失败</span>
                      )}
                    </div>
                    <h3 className="font-medium text-gray-900 truncate">
                      {result.experience.intent}
                    </h3>
                    <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
                      <span>置信度: {(result.experience.confidence_score * 100).toFixed(1)}%</span>
                      <span>工具: {result.experience.execution.tools?.join(", ") || "无"}</span>
                      {result.experience.reflection.what_worked.length > 0 && (
                        <span>优势: {result.experience.reflection.what_worked.length}项</span>
                      )}
                    </div>
                  </div>
                  <div className="flex flex-col items-end gap-2">
                    <div className="flex items-center gap-1">
                      <TrendingUp className="w-4 h-4 text-blue-500" />
                      <span className="font-bold text-blue-600">
                        {(result.score * 100).toFixed(1)}%
                      </span>
                    </div>
                    <ChevronRight className="w-5 h-5 text-gray-300" />
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
