"use client"

import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useParams, useRouter } from "next/navigation"
import { experienceApi, evaluationApi, governanceApi } from "@/lib/api-client"
import { ArrowLeft, CheckCircle, XCircle, GitBranch, Clock, Tag, GitFork, Wrench, Quote } from "lucide-react"
import { ExperienceGraph } from "../../components/ExperienceGraph"

const RELATION_COLORS: Record<string, string> = {
  reuse: "#10b981", citation: "#3b82f6", fork: "#8b5cf6",
  improvement: "#f59e0b", dependency: "#ef4444",
}
const RELATION_LABELS: Record<string, string> = {
  reuse: "复用", citation: "引用", fork: "分叉",
  improvement: "改进", dependency: "依赖",
}

export default function ExperienceDetailPage() {
  const params = useParams()
  const router = useRouter()
  const queryClient = useQueryClient()
  const id = params.id as string
  const [showImprove, setShowImprove] = useState(false)
  const [showCite, setShowCite] = useState(false)

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

  // GEG: Fork - 创建经验副本
  const forkMutation = useMutation({
    mutationFn: () => governanceApi.fork(id),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["experiences"] })
      queryClient.invalidateQueries({ queryKey: ["experience-relations", id] })
      router.push(`/experiences/${data.forked_experience.id}`)
    },
  })

  // GEG: Improve - 创建改进版本
  const improveMutation = useMutation({
    mutationFn: (improvements: Record<string, unknown>) =>
      governanceApi.improve(id, improvements),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["experiences"] })
      queryClient.invalidateQueries({ queryKey: ["experience-relations", id] })
      setShowImprove(false)
      router.push(`/experiences/${data.improved_experience.id}`)
    },
  })

  // GEG: Cite - 添加引用关系
  const citeMutation = useMutation({
    mutationFn: (citingExperienceId: string) =>
      governanceApi.cite(id, citingExperienceId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["experience-relations", id] })
      setShowCite(false)
    },
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

      {/* GEG 操作: Fork / Improve / Cite */}
      <div className="rounded-lg border p-4 mb-6">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">GEG 经验协作</h3>
        <div className="flex flex-wrap gap-3">
          <button
            onClick={() => forkMutation.mutate()}
            disabled={forkMutation.isPending}
            className="flex items-center gap-2 px-4 py-2 bg-purple-50 text-purple-700 rounded-lg text-sm font-medium hover:bg-purple-100 disabled:opacity-50"
          >
            <GitFork className="w-4 h-4" />
            {forkMutation.isPending ? "分叉中..." : "Fork 分叉"}
          </button>
          <button
            onClick={() => setShowImprove(!showImprove)}
            className="flex items-center gap-2 px-4 py-2 bg-amber-50 text-amber-700 rounded-lg text-sm font-medium hover:bg-amber-100"
          >
            <Wrench className="w-4 h-4" />
            Improve 改进
          </button>
          <button
            onClick={() => setShowCite(!showCite)}
            className="flex items-center gap-2 px-4 py-2 bg-blue-50 text-blue-700 rounded-lg text-sm font-medium hover:bg-blue-100"
          >
            <Quote className="w-4 h-4" />
            Cite 引用
          </button>
        </div>

        {/* Fork 结果提示 */}
        {forkMutation.isError && (
          <p className="mt-2 text-xs text-red-600">分叉失败，请先登录</p>
        )}

        {/* Improve 表单 */}
        {showImprove && (
          <ImproveForm
            currentIntent={experience.intent}
            onSubmit={(improvements) => improveMutation.mutate(improvements)}
            onCancel={() => setShowImprove(false)}
            isPending={improveMutation.isPending}
          />
        )}

        {/* Cite 表单 */}
        {showCite && (
          <CiteForm
            onSubmit={(citingId) => citeMutation.mutate(citingId)}
            onCancel={() => setShowCite(false)}
            isPending={citeMutation.isPending}
            currentId={id}
          />
        )}

        {citeMutation.isSuccess && (
          <p className="mt-2 text-xs text-green-600">引用关系已添加</p>
        )}
      </div>

      {/* 图谱关系 */}
      <div className="rounded-lg border p-4 mb-6">
        <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
          <GitBranch className="w-4 h-4" /> 图谱关系
          {relations && relations.length > 0 && (
            <span className="text-xs text-gray-400">({relations.length} 条关系)</span>
          )}
        </h3>
        {relations && relations.length > 0 ? (
          <>
            <ExperienceGraph
              experienceId={id}
              relations={relations}
              onNodeClick={(nodeId) => router.push(`/experiences/${nodeId}`)}
            />
            <div className="mt-3 space-y-1">
              {relations.map((rel) => (
                <div key={rel.id} className="flex items-center gap-2 text-xs text-gray-500">
                  <span className="px-1.5 py-0.5 rounded" style={{
                    background: `${RELATION_COLORS[rel.relation_type] || "#9ca3af"}20`,
                    color: RELATION_COLORS[rel.relation_type] || "#6b7280"
                  }}>
                    {RELATION_LABELS[rel.relation_type] || rel.relation_type}
                  </span>
                  <span>{rel.source_id === id ? "指向" : "来自"}其他经验</span>
                  <span className="text-gray-400">权重: {rel.weight.toFixed(2)}</span>
                </div>
              ))}
            </div>
          </>
        ) : (
          <p className="text-sm text-gray-400 text-center py-4">暂无图谱关系</p>
        )}
      </div>

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

// ── Improve 改进表单 ──

function ImproveForm({
  currentIntent,
  onSubmit,
  onCancel,
  isPending,
}: {
  currentIntent: string
  onSubmit: (improvements: Record<string, unknown>) => void
  onCancel: () => void
  isPending: boolean
}) {
  const [intent, setIntent] = useState(currentIntent)
  const [whatWorked, setWhatWorked] = useState("")
  const [whatFailed, setWhatFailed] = useState("")
  const [why, setWhy] = useState("")

  return (
    <div className="mt-4 space-y-3 rounded-lg border border-amber-200 bg-amber-50/50 p-4">
      <h4 className="text-sm font-medium text-amber-800">改进此经验</h4>
      <div>
        <label className="block text-xs text-gray-600 mb-1">改进后的意图</label>
        <input
          type="text"
          value={intent}
          onChange={(e) => setIntent(e.target.value)}
          className="w-full rounded-md border px-3 py-2 text-sm"
          placeholder="描述改进后的任务意图"
        />
      </div>
      <div>
        <label className="block text-xs text-gray-600 mb-1">新增有效做法（逗号分隔）</label>
        <input
          type="text"
          value={whatWorked}
          onChange={(e) => setWhatWorked(e.target.value)}
          className="w-full rounded-md border px-3 py-2 text-sm"
          placeholder="例如: docker build, kubectl apply"
        />
      </div>
      <div>
        <label className="block text-xs text-gray-600 mb-1">新增失败/坑（逗号分隔）</label>
        <input
          type="text"
          value={whatFailed}
          onChange={(e) => setWhatFailed(e.target.value)}
          className="w-full rounded-md border px-3 py-2 text-sm"
          placeholder="例如: 忘记加 -d 参数"
        />
      </div>
      <div>
        <label className="block text-xs text-gray-600 mb-1">改进原因</label>
        <input
          type="text"
          value={why}
          onChange={(e) => setWhy(e.target.value)}
          className="w-full rounded-md border px-3 py-2 text-sm"
          placeholder="为什么这次改进更好"
        />
      </div>
      <div className="flex gap-2">
        <button
          onClick={() =>
            onSubmit({
              intent,
              reflection: {
                what_worked: whatWorked ? whatWorked.split(",").map((s) => s.trim()) : [],
                what_failed: whatFailed ? whatFailed.split(",").map((s) => s.trim()) : [],
                why,
              },
            })
          }
          disabled={isPending || !intent}
          className="px-4 py-2 bg-amber-600 text-white rounded-md text-sm hover:bg-amber-700 disabled:opacity-50"
        >
          {isPending ? "提交中..." : "提交改进"}
        </button>
        <button
          onClick={onCancel}
          className="px-4 py-2 bg-gray-100 text-gray-600 rounded-md text-sm hover:bg-gray-200"
        >
          取消
        </button>
      </div>
    </div>
  )
}

// ── Cite 引用表单 ──

function CiteForm({
  onSubmit,
  onCancel,
  isPending,
  currentId,
}: {
  onSubmit: (citingExperienceId: string) => void
  onCancel: () => void
  isPending: boolean
  currentId: string
}) {
  const [citeId, setCiteId] = useState("")
  const [searchQuery, setSearchQuery] = useState("")
  const [searchResults, setSearchResults] = useState<{ id: string; intent: string }[]>([])

  const handleSearch = async () => {
    if (!searchQuery) return
    try {
      const res = await experienceApi.list({ page: 1, page_size: 5, domain: searchQuery })
      setSearchResults(
        res.items
          .filter((e) => e.id !== currentId)
          .map((e) => ({ id: e.id, intent: e.intent }))
      )
    } catch {
      setSearchResults([])
    }
  }

  return (
    <div className="mt-4 space-y-3 rounded-lg border border-blue-200 bg-blue-50/50 p-4">
      <h4 className="text-sm font-medium text-blue-800">引用其他经验</h4>
      <p className="text-xs text-gray-500">
        搜索并选择要引用的经验，将建立从当前经验到目标经验的 citation 关系。
      </p>
      <div className="flex gap-2">
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          className="flex-1 rounded-md border px-3 py-2 text-sm"
          placeholder="按领域搜索经验..."
        />
        <button
          onClick={handleSearch}
          className="px-3 py-2 bg-blue-600 text-white rounded-md text-sm hover:bg-blue-700"
        >
          搜索
        </button>
      </div>
      {searchResults.length > 0 && (
        <div className="space-y-1">
          {searchResults.map((r) => (
            <button
              key={r.id}
              onClick={() => setCiteId(r.id)}
              className={`block w-full text-left px-3 py-2 rounded-md text-sm ${
                citeId === r.id
                  ? "bg-blue-100 border border-blue-400"
                  : "bg-white border hover:bg-gray-50"
              }`}
            >
              <span className="text-xs text-gray-400">{r.id.slice(0, 8)}...</span>{" "}
              {r.intent.slice(0, 60)}
            </button>
          ))}
        </div>
      )}
      <div>
        <label className="block text-xs text-gray-600 mb-1">或直接输入经验 ID</label>
        <input
          type="text"
          value={citeId}
          onChange={(e) => setCiteId(e.target.value)}
          className="w-full rounded-md border px-3 py-2 text-sm"
          placeholder="目标经验 UUID"
        />
      </div>
      <div className="flex gap-2">
        <button
          onClick={() => citeId && onSubmit(citeId)}
          disabled={isPending || !citeId}
          className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm hover:bg-blue-700 disabled:opacity-50"
        >
          {isPending ? "添加中..." : "添加引用"}
        </button>
        <button
          onClick={onCancel}
          className="px-4 py-2 bg-gray-100 text-gray-600 rounded-md text-sm hover:bg-gray-200"
        >
          取消
        </button>
      </div>
    </div>
  )
}
