"use client"

import { useQuery, useMutation } from "@tanstack/react-query"
import { useParams, useRouter } from "next/navigation"
import { experienceApi, evaluationApi } from "@/lib/api-client"
import { ArrowLeft, CheckCircle, XCircle, GitBranch, Clock, Tag } from "lucide-react"

export default function ExperienceDetailPage() {
  const params = useParams()
  const router = useRouter()
  const id = params.id as string

  const { data: experience, isLoading } = useQuery({
    queryKey: ["experience", id],
    queryFn: () => experienceApi.get(id),
    enabled: !!id,
  })

  const { data: relations } = useQuery({
    queryKey: ["experience-relations", id],
    queryFn: () => experienceApi.getRelations(id),
    enabled: !!id,
  })

  const evaluateMutation = useMutation({
    mutationFn: () => evaluationApi.evaluateExperience(id),
  })

  if (isLoading) {
    return (
      <div>
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-3/4 mb-4"></div>
          <div className="h-4 bg-gray-200 rounded w-1/2 mb-8"></div>
          <div className="space-y-3">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-20 bg-gray-100 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  if (!experience) {
    return <p className="text-gray-400">经验未找到</p>
  }

  return (
    <div>
      {/* 返回按钮 */}
      <button
        onClick={() => router.push("/experiences")}
        className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-900 mb-4"
      >
        <ArrowLeft className="w-4 h-4" />
        返回经验列表
      </button>

      {/* 标题区 */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold mb-2">{experience.intent}</h1>
        <div className="flex flex-wrap items-center gap-3 text-sm">
          <span className="flex items-center gap-1 px-2 py-0.5 bg-blue-50 text-blue-700 rounded">
            <Tag className="w-3 h-3" /> {experience.context.domain}
          </span>
          <span className="px-2 py-0.5 bg-gray-50 text-gray-600 rounded">
            {experience.context.task_type}
          </span>
          <span className={`flex items-center gap-1 px-2 py-0.5 rounded ${
            experience.outcome.success ? "bg-green-50 text-green-700" : "bg-red-50 text-red-700"
          }`}>
            {experience.outcome.success ? <CheckCircle className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
            {experience.outcome.success ? "成功" : "失败"}
          </span>
          <span className="flex items-center gap-1 text-gray-400">
            <Clock className="w-3 h-3" />
            {experience.created_at ? new Date(experience.created_at).toLocaleString("zh-CN") : ""}
          </span>
          <span className="px-2 py-0.5 bg-purple-50 text-purple-700 rounded">
            v{experience.version}
          </span>
        </div>
      </div>

      {/* 置信度 + 评估 */}
      <div className="flex items-center gap-4 mb-6">
        <div className="flex-1 rounded-lg border p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">置信度</p>
              <p className="text-2xl font-bold text-blue-600">
                {(experience.confidence_score * 100).toFixed(1)}%
              </p>
            </div>
            <div className="text-right">
              <p className="text-sm text-gray-500">评估状态</p>
              <p className={`text-sm font-medium ${
                experience.evaluation_status === "evaluated" ? "text-green-600" : "text-yellow-600"
              }`}>
                {experience.evaluation_status === "evaluated" ? "已评估" : "待评估"}
              </p>
            </div>
          </div>
          <button
            onClick={() => evaluateMutation.mutate()}
            disabled={evaluateMutation.isPending}
            className="mt-3 w-full px-3 py-1.5 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 disabled:opacity-50"
          >
            {evaluateMutation.isPending ? "评估中..." : "重新评估"}
          </button>
          {evaluateMutation.data && (
            <p className="text-xs text-green-600 mt-2">
              评估完成: 总分 {(evaluateMutation.data.overall_score * 100).toFixed(1)}%
            </p>
          )}
        </div>
      </div>

      {/* 反思 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        <div className="rounded-lg border p-4">
          <h3 className="text-sm font-semibold text-green-700 mb-2 flex items-center gap-2">
            <CheckCircle className="w-4 h-4" /> 什么有效
          </h3>
          {experience.reflection.what_worked.length > 0 ? (
            <ul className="space-y-1">
              {experience.reflection.what_worked.map((item, i) => (
                <li key={i} className="text-sm text-gray-600">• {item}</li>
              ))}
            </ul>
          ) : <p className="text-sm text-gray-400">无记录</p>}
        </div>
        <div className="rounded-lg border p-4">
          <h3 className="text-sm font-semibold text-red-700 mb-2 flex items-center gap-2">
            <XCircle className="w-4 h-4" /> 什么失败
          </h3>
          {experience.reflection.what_failed.length > 0 ? (
            <ul className="space-y-1">
              {experience.reflection.what_failed.map((item, i) => (
                <li key={i} className="text-sm text-gray-600">• {item}</li>
              ))}
            </ul>
          ) : <p className="text-sm text-gray-400">无记录</p>}
        </div>
      </div>

      {/* 反思原因 */}
      {experience.reflection.why && (
        <div className="rounded-lg border p-4 mb-6">
          <h3 className="text-sm font-semibold text-gray-700 mb-2">原因分析</h3>
          <p className="text-sm text-gray-600">{experience.reflection.why}</p>
        </div>
      )}

      {/* 执行信息 */}
      <div className="rounded-lg border p-4 mb-6">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">执行信息</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <p className="text-gray-400">步骤数</p>
            <p className="font-medium">{experience.execution.steps.length}</p>
          </div>
          <div>
            <p className="text-gray-400">工具数</p>
            <p className="font-medium">{experience.execution.tools.length}</p>
          </div>
          <div>
            <p className="text-gray-400">可复用模式</p>
            <p className="font-medium">{experience.reusable_patterns.length}</p>
          </div>
          <div>
            <p className="text-gray-400">来源信号</p>
            <p className="font-medium">{experience.provenance.agent_signals.length}</p>
          </div>
        </div>
        {experience.execution.tools.length > 0 && (
          <div className="mt-3">
            <p className="text-xs text-gray-400 mb-1">使用的工具</p>
            <div className="flex flex-wrap gap-2">
              {experience.execution.tools.map((tool, i) => (
                <span key={i} className="px-2 py-0.5 bg-gray-100 text-gray-700 rounded text-xs">
                  {tool}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* 图谱关系 */}
      {relations && relations.length > 0 && (
        <div className="rounded-lg border p-4">
          <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
            <GitBranch className="w-4 h-4" /> 图谱关系 ({relations.length})
          </h3>
          <div className="space-y-2">
            {relations.map((rel) => (
              <div key={rel.id} className="flex items-center gap-2 text-sm">
                <span className="px-2 py-0.5 bg-blue-50 text-blue-700 rounded text-xs">
                  {rel.relation_type}
                </span>
                <span className="text-gray-400">
                  {rel.source_id === id ? "指向" : "来自"}
                </span>
                <span className="text-blue-600 font-mono text-xs">
                  {rel.source_id === id ? rel.target_id : rel.source_id}
                </span>
                <span className="text-gray-400 text-xs">
                  (权重: {rel.weight.toFixed(2)})
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 原始数据 */}
      <details className="mt-6">
        <summary className="text-sm text-gray-500 cursor-pointer hover:text-gray-700">
          查看原始 JSON 数据
        </summary>
        <pre className="mt-2 p-4 bg-gray-50 rounded-lg overflow-auto text-xs">
          {JSON.stringify(experience, null, 2)}
        </pre>
      </details>
    </div>
  )
}
