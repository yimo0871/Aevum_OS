"use client"

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"
import { experienceApi } from "@/lib/api-client"
import Link from "next/link"
import { Search, Trash2, ExternalLink } from "lucide-react"

export default function ExperiencesPage() {
  const queryClient = useQueryClient()
  const [page, setPage] = useState(1)
  const [domain, setDomain] = useState("")
  const [searchQuery, setSearchQuery] = useState("")

  const { data, isLoading } = useQuery({
    queryKey: ["experiences", page, domain],
    queryFn: () => experienceApi.list({ page, page_size: 20, domain: domain || undefined }),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => experienceApi.delete(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["experiences"] }),
  })

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">经验管理</h1>
        <span className="text-sm text-gray-500">共 {data?.total ?? 0} 条经验</span>
      </div>

      {/* 筛选栏 */}
      <div className="flex gap-4 mb-6">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="搜索经验..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <select
          value={domain}
          onChange={(e) => { setDomain(e.target.value); setPage(1) }}
          className="px-4 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">全部领域</option>
          <option value="后端开发">后端开发</option>
          <option value="前端开发">前端开发</option>
          <option value="运维部署">运维部署</option>
          <option value="数据处理">数据处理</option>
          <option value="测试质量">测试质量</option>
          <option value="安全审计">安全审计</option>
          <option value="机器学习">机器学习</option>
          <option value="综合通用">综合通用</option>
        </select>
      </div>

      {/* 经验列表 */}
      {isLoading ? (
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="border rounded-lg p-4 animate-pulse">
              <div className="h-5 bg-gray-200 rounded w-3/4 mb-2"></div>
              <div className="h-4 bg-gray-200 rounded w-1/2"></div>
            </div>
          ))}
        </div>
      ) : data?.items?.length === 0 ? (
        <div className="text-center py-12 border rounded-lg">
          <p className="text-gray-400">暂无经验数据</p>
          <p className="text-sm text-gray-400 mt-2">提交任务后将自动生成经验</p>
        </div>
      ) : (
        <div className="space-y-3">
          {data?.items?.map((exp) => (
            <div key={exp.id} className="border rounded-lg p-4 hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <Link href={`/experiences/${exp.id}`} className="block">
                    <h3 className="font-medium text-gray-900 truncate hover:text-blue-600">
                      {exp.intent}
                    </h3>
                  </Link>
                  <div className="flex items-center gap-3 mt-2 text-xs text-gray-500">
                    <span className="px-2 py-0.5 bg-blue-50 text-blue-700 rounded">
                      {exp.context.domain}
                    </span>
                    <span className="px-2 py-0.5 bg-gray-50 text-gray-600 rounded">
                      {exp.context.task_type}
                    </span>
                    <span className={`px-2 py-0.5 rounded ${
                      exp.outcome.success
                        ? "bg-green-50 text-green-700"
                        : "bg-red-50 text-red-700"
                    }`}>
                      {exp.outcome.success ? "成功" : "失败"}
                    </span>
                    <span className={`px-2 py-0.5 rounded ${
                      exp.evaluation_status === "evaluated"
                        ? "bg-green-50 text-green-700"
                        : "bg-yellow-50 text-yellow-700"
                    }`}>
                      {exp.evaluation_status === "evaluated" ? "已评估" : "待评估"}
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-2 ml-4">
                  <div className="text-right">
                    <p className="text-xs text-gray-400">置信度</p>
                    <p className="text-sm font-bold text-blue-600">
                      {(exp.confidence_score * 100).toFixed(0)}%
                    </p>
                  </div>
                  <Link href={`/experiences/${exp.id}`}>
                    <button className="p-1.5 text-gray-400 hover:text-blue-600 rounded">
                      <ExternalLink className="w-4 h-4" />
                    </button>
                  </Link>
                  <button
                    onClick={() => {
                      if (confirm("确定删除这条经验？")) deleteMutation.mutate(exp.id)
                    }}
                    className="p-1.5 text-gray-400 hover:text-red-600 rounded"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
              {exp.reflection.what_failed.length > 0 && (
                <p className="text-xs text-red-500 mt-2">
                  失败项: {exp.reflection.what_failed.join(", ")}
                </p>
              )}
            </div>
          ))}
        </div>
      )}

      {/* 分页 */}
      {data && data.total > 20 && (
        <div className="flex items-center justify-center gap-2 mt-6">
          <button
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-3 py-1.5 border rounded text-sm disabled:opacity-50"
          >
            上一页
          </button>
          <span className="text-sm text-gray-500">
            第 {page} 页 / 共 {Math.ceil(data.total / 20)} 页
          </span>
          <button
            onClick={() => setPage(p => p + 1)}
            disabled={page * 20 >= data.total}
            className="px-3 py-1.5 border rounded text-sm disabled:opacity-50"
          >
            下一页
          </button>
        </div>
      )}
    </div>
  )
}
