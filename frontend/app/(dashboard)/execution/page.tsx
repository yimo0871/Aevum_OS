"use client"

import { useState, useEffect, useRef } from "react"
import { useMutation, useQuery } from "@tanstack/react-query"
import { executionApi } from "@/lib/api-client"
import { Play, Loader2, CheckCircle, XCircle, Clock, ArrowRight, Wrench, Radio } from "lucide-react"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

const PIPELINE_STEPS = [
  { num: 1, name: "检索相似经验", key: "retrieve_similar_experiences" },
  { num: 2, name: "选择最佳工作流", key: "select_best_workflows" },
  { num: 3, name: "执行任务", key: "execute_task" },
  { num: 4, name: "记录完整追踪", key: "record_full_trace" },
  { num: 5, name: "生成经验对象", key: "generate_experience_object" },
  { num: 6, name: "评估经验", key: "evaluate_experience" },
  { num: 7, name: "存入图谱", key: "store_into_graph" },
  { num: 8, name: "更新复用索引", key: "update_reuse_index" },
]

const STATUS_LABELS: Record<string, string> = {
  completed: "已完成",
  failed: "失败",
  invalid: "无效",
  running: "运行中",
  pending: "等待中",
}

interface SSEStepState {
  step: number
  total: number
  name: string
  status: "pending" | "running" | "completed"
  timestamp?: string
}

export default function ExecutionPage() {
  const [intent, setIntent] = useState("")
  const [domain, setDomain] = useState("运维部署")
  const [taskType, setTaskType] = useState("部署上线")
  const [result, setResult] = useState<any>(null)

  // SSE 实时进度状态
  const [sseSteps, setSseSteps] = useState<Record<number, SSEStepState>>({})
  const [sseFinished, setSseFinished] = useState(false)
  const [sseActive, setSseActive] = useState(false)
  const eventSourceRef = useRef<EventSource | null>(null)

  const { data: tools } = useQuery({
    queryKey: ["tools"],
    queryFn: () => executionApi.listTools(),
  })

  // 启动 SSE 实时进度追踪
  const startStreaming = (taskId: string) => {
    // 关闭已有连接
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
    }

    // 重置状态
    setSseFinished(false)
    setSseActive(true)

    // 初始化所有步骤为 pending
    const initialSteps: Record<number, SSEStepState> = {}
    PIPELINE_STEPS.forEach(({ num, key }) => {
      initialSteps[num] = { step: num, total: PIPELINE_STEPS.length, name: key, status: "pending" }
    })
    setSseSteps(initialSteps)

    // 连接 SSE 端点（如果环境不支持 EventSource 则静默跳过）
    if (typeof EventSource === "undefined") {
      setSseActive(false)
      return
    }

    const eventSource = new EventSource(
      `${API_BASE}/api/v1/execution/tasks/${taskId}/stream`
    )
    eventSourceRef.current = eventSource

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)

        if (data.status === "finished") {
          setSseFinished(true)
          setSseActive(false)
          eventSource.close()
          eventSourceRef.current = null
          return
        }

        if (data.step) {
          setSseSteps((prev) => ({
            ...prev,
            [data.step]: {
              step: data.step,
              total: data.total,
              name: data.name,
              status: data.status,
              timestamp: data.timestamp,
            },
          }))
        }
      } catch {
        // 忽略解析错误
      }
    }

    eventSource.onerror = () => {
      setSseActive(false)
      eventSource.close()
      eventSourceRef.current = null
    }
  }

  // 组件卸载时清理 EventSource
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close()
      }
    }
  }, [])

  const submitMutation = useMutation({
    mutationFn: () =>
      executionApi.submitTask({
        intent,
        context: { domain, task_type: taskType, constraints: {} },
      }),
    onSuccess: (data) => {
      setResult(data)
      // 提交成功后启动 SSE 实时进度追踪
      if (data.id) {
        startStreaming(data.id)
      }
    },
    onError: (err: any) => setResult({ status: "failed", error: err.message }),
  })

  const canSubmit = intent.trim().length > 0 && !submitMutation.isPending

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">任务执行</h1>

      {/* 任务提交表单 */}
      <div className="rounded-lg border p-6 mb-6">
        <h2 className="text-lg font-semibold mb-4">提交新任务</h2>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              任务意图 <span className="text-red-500">*</span>
            </label>
            <textarea
              value={intent}
              onChange={(e) => setIntent(e.target.value)}
              placeholder="例如：将 FastAPI 应用部署到生产环境"
              rows={3}
              className="w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">领域</label>
              <select
                value={domain}
                onChange={(e) => setDomain(e.target.value)}
                className="w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
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
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">任务类型</label>
              <input
                type="text"
                value={taskType}
                onChange={(e) => setTaskType(e.target.value)}
                className="w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
          <button
            onClick={() => submitMutation.mutate()}
            disabled={!canSubmit}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {submitMutation.isPending ? (
              <><Loader2 className="w-4 h-4 animate-spin" /> 执行中...</>
            ) : (
              <><Play className="w-4 h-4" /> 执行任务</>
            )}
          </button>
        </div>
      </div>

      {/* 执行结果 */}
      {result && (
        <div className="rounded-lg border p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">执行结果</h2>
            <span className={`flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium ${
              result.status === "completed" ? "bg-green-50 text-green-700" :
              result.status === "failed" ? "bg-red-50 text-red-700" :
              result.status === "invalid" ? "bg-orange-50 text-orange-700" :
              "bg-blue-50 text-blue-700"
            }`}>
              {result.status === "completed" ? <CheckCircle className="w-4 h-4" /> :
               result.status === "failed" ? <XCircle className="w-4 h-4" /> :
               <Loader2 className="w-4 h-4" />}
              {STATUS_LABELS[result.status] || result.status}
            </span>
          </div>

          {result.duration && (
            <p className="text-sm text-gray-500 mb-4">
              总耗时: {(result.duration).toFixed(2)}s
            </p>
          )}

          {result.error && (
            <div className="rounded border border-red-200 bg-red-50 p-3 mb-4">
              <p className="text-sm text-red-600">{result.error}</p>
            </div>
          )}

          {result.experience_id && (
            <a
              href={`/experiences/${result.experience_id}`}
              className="inline-flex items-center gap-2 text-sm text-blue-600 hover:underline"
            >
              查看生成的经验 <ArrowRight className="w-3 h-3" />
            </a>
          )}
        </div>
      )}

      {/* SSE 实时进度追踪 */}
      {(sseActive || sseFinished) && (
        <div className="rounded-lg border p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold flex items-center gap-2">
              <Radio className="w-5 h-5 text-blue-600" />
              实时进度追踪（SSE）
            </h2>
            <span className={`flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium ${
              sseFinished ? "bg-green-50 text-green-700" : "bg-blue-50 text-blue-700"
            }`}>
              {sseFinished ? (
                <><CheckCircle className="w-4 h-4" /> 已完成</>
              ) : (
                <><Loader2 className="w-4 h-4 animate-spin" /> 实时追踪中</>
              )}
            </span>
          </div>

          {/* 进度条 */}
          <div className="mb-4">
            <div className="flex items-center justify-between text-sm text-gray-500 mb-1">
              <span>总体进度</span>
              <span>
                {Object.values(sseSteps).filter((s) => s.status === "completed").length}
                /{PIPELINE_STEPS.length}
              </span>
            </div>
            <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
              <div
                className="h-full bg-blue-600 rounded-full transition-all duration-300"
                style={{
                  width: `${(Object.values(sseSteps).filter((s) => s.status === "completed").length / PIPELINE_STEPS.length) * 100}%`,
                }}
              />
            </div>
          </div>

          {/* 8 步进度指示器 */}
          <div className="space-y-2">
            {PIPELINE_STEPS.map(({ num, name }) => {
              const stepState = sseSteps[num]
              const status = stepState?.status || "pending"
              return (
                <div
                  key={num}
                  className={`flex items-center gap-3 p-3 rounded-lg border transition-colors ${
                    status === "completed" ? "border-green-200 bg-green-50" :
                    status === "running" ? "border-blue-200 bg-blue-50" :
                    "border-gray-200"
                  }`}
                >
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                    status === "completed" ? "bg-green-600 text-white" :
                    status === "running" ? "bg-blue-600 text-white" :
                    "bg-gray-200 text-gray-500"
                  }`}>
                    {status === "completed" ? <CheckCircle className="w-4 h-4" /> :
                     status === "running" ? <Loader2 className="w-4 h-4 animate-spin" /> : num}
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-medium">{name}</p>
                    {stepState?.timestamp && status !== "pending" && (
                      <p className="text-xs text-gray-400">
                        <Clock className="w-3 h-3 inline" /> {stepState.timestamp}
                      </p>
                    )}
                  </div>
                  <span className={`text-xs font-medium ${
                    status === "completed" ? "text-green-600" :
                    status === "running" ? "text-blue-600" :
                    "text-gray-400"
                  }`}>
                    {STATUS_LABELS[status] || status}
                  </span>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* 8步流水线状态 */}
      {result?.pipeline_state && (
        <div className="rounded-lg border p-6 mb-6">
          <h2 className="text-lg font-semibold mb-4">8 步经验流水线</h2>
          <div className="space-y-2">
            {PIPELINE_STEPS.map(({ num, name, key }) => {
              const stepData = result.pipeline_state?.[String(num)] || result.pipeline_state?.[key]
              const status = stepData?.status || "pending"
              return (
                <div
                  key={num}
                  className={`flex items-center gap-3 p-3 rounded-lg border ${
                    status === "completed" ? "border-green-200 bg-green-50" :
                    status === "failed" ? "border-red-200 bg-red-50" :
                    status === "running" ? "border-blue-200 bg-blue-50" :
                    "border-gray-200"
                  }`}
                >
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                    status === "completed" ? "bg-green-600 text-white" :
                    status === "failed" ? "bg-red-600 text-white" :
                    status === "running" ? "bg-blue-600 text-white" :
                    "bg-gray-200 text-gray-500"
                  }`}>
                    {status === "completed" ? <CheckCircle className="w-4 h-4" /> :
                     status === "failed" ? <XCircle className="w-4 h-4" /> :
                     status === "running" ? <Loader2 className="w-4 h-4 animate-spin" /> : num}
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-medium">{name}</p>
                    {stepData?.duration_ms && (
                      <p className="text-xs text-gray-400">
                        <Clock className="w-3 h-3 inline" /> {stepData.duration_ms.toFixed(0)}ms
                      </p>
                    )}
                    {stepData?.error && (
                      <p className="text-xs text-red-500">{stepData.error}</p>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* 可用工具 */}
      {tools && tools.length > 0 && (
        <div className="rounded-lg border p-6">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Wrench className="w-5 h-5" /> 可用工具 ({tools.length})
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {tools.map((tool) => (
              <div key={tool.name} className="border rounded p-3">
                <p className="text-sm font-mono font-medium text-blue-600">{tool.name}</p>
                <p className="text-xs text-gray-500 mt-1">{tool.description}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
