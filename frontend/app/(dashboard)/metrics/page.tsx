"use client"

import { useQuery } from "@tanstack/react-query"
import { evaluationApi } from "@/lib/api-client"
import { TrendingUp, TrendingDown, Activity } from "lucide-react"

const METRIC_CONFIG = [
  { key: "experience_reuse_rate", label: "经验复用率", color: "text-blue-600", bg: "bg-blue-50", format: "percent", inverse: false },
  { key: "workflow_success_rate", label: "工作流成功率", color: "text-green-600", bg: "bg-green-50", format: "percent", inverse: false },
  { key: "cross_agent_transfer_rate", label: "跨Agent迁移率", color: "text-purple-600", bg: "bg-purple-50", format: "percent", inverse: false },
  { key: "external_dependency_ratio", label: "外部依赖比例", color: "text-orange-600", bg: "bg-orange-50", format: "percent", inverse: true },
  { key: "learning_velocity", label: "学习速度", color: "text-yellow-600", bg: "bg-yellow-50", format: "number", suffix: "/天", inverse: false },
  { key: "convergence_speed", label: "收敛速度", color: "text-cyan-600", bg: "bg-cyan-50", format: "percent", inverse: false },
  { key: "human_intervention_rate", label: "人类干预率", color: "text-red-600", bg: "bg-red-50", format: "percent", inverse: true },
] as const

function formatValue(value: number, format: string, suffix?: string) {
  if (format === "percent") return `${(value * 100).toFixed(2)}%`
  if (format === "number") return `${value.toFixed(2)}${suffix || ""}`
  return String(value)
}

function MetricBar({ value, inverse }: { value: number; inverse: boolean }) {
  const percentage = Math.min(100, value * 100)
  const displayValue = inverse ? 100 - percentage : percentage
  return (
    <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
      <div
        className={`h-2 rounded-full transition-all ${
          inverse ? "bg-orange-500" : "bg-blue-500"
        }`}
        style={{ width: `${displayValue}%` }}
      />
    </div>
  )
}

export default function MetricsPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["metrics"],
    queryFn: () => evaluationApi.getMetrics(),
    refetchInterval: 15000,
  })

  if (isLoading) {
    return (
      <div>
        <h1 className="text-2xl font-bold mb-6">指标监控</h1>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(7)].map((_, i) => (
            <div key={i} className="border rounded-lg p-6 animate-pulse">
              <div className="h-4 bg-gray-200 rounded w-24 mb-3"></div>
              <div className="h-8 bg-gray-200 rounded w-20 mb-3"></div>
              <div className="h-2 bg-gray-200 rounded"></div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div>
        <h1 className="text-2xl font-bold mb-6">指标监控</h1>
        <div className="rounded-lg border border-red-200 bg-red-50 p-6">
          <p className="text-red-600 font-medium">无法获取系统指标</p>
          <p className="text-sm text-red-400 mt-1">请确保后端服务正在运行</p>
        </div>
      </div>
    )
  }

  const metrics = data?.metrics

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">指标监控</h1>
        <div className="flex items-center gap-2 text-sm text-gray-400">
          <Activity className="w-4 h-4" />
          每 15 秒自动刷新
        </div>
      </div>

      {/* 指标卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
        {METRIC_CONFIG.map(({ key, label, color, bg, format, suffix, inverse }) => {
          const value = metrics?.[key] ?? 0
          const Icon = inverse ? TrendingDown : TrendingUp
          return (
            <div key={key} className={`rounded-lg border p-6 ${bg}`}>
              <div className="flex items-center justify-between mb-3">
                <p className="text-sm text-gray-600">{label}</p>
                <Icon className={`w-5 h-5 ${color}`} />
              </div>
              <p className={`text-3xl font-bold ${color}`}>
                {formatValue(value, format, suffix)}
              </p>
              <MetricBar value={value} inverse={inverse} />
              {inverse && (
                <p className="text-xs text-gray-400 mt-2">越低越好</p>
              )}
            </div>
          )
        })}
      </div>

      {/* 指标说明 */}
      <div className="rounded-lg border p-6">
        <h2 className="text-lg font-semibold mb-4">指标说明</h2>
        <div className="space-y-3 text-sm text-gray-600">
          <div className="flex gap-3">
            <span className="font-medium text-gray-900 min-w-32">经验复用率</span>
            <span>被复用的经验数占总经验数的比例，越高说明经验价值越大</span>
          </div>
          <div className="flex gap-3">
            <span className="font-medium text-gray-900 min-w-32">工作流成功率</span>
            <span>成功执行的经验占总经验数的比例</span>
          </div>
          <div className="flex gap-3">
            <span className="font-medium text-gray-900 min-w-32">跨Agent迁移率</span>
            <span>被其他 Agent 引用或分叉的经验比例，反映集体智能程度</span>
          </div>
          <div className="flex gap-3">
            <span className="font-medium text-gray-900 min-w-32">外部依赖比例</span>
            <span>依赖外部网络数据的经验比例，越低说明自身经验库越完善</span>
          </div>
          <div className="flex gap-3">
            <span className="font-medium text-gray-900 min-w-32">学习速度</span>
            <span>最近7天平均每天新增的经验数量</span>
          </div>
          <div className="flex gap-3">
            <span className="font-medium text-gray-900 min-w-32">收敛速度</span>
            <span>已评估经验占总经验的比例，反映系统评估能力</span>
          </div>
          <div className="flex gap-3">
            <span className="font-medium text-gray-900 min-w-32">人类干预率</span>
            <span>需要人类干预的经验比例，越低说明系统自动化程度越高</span>
          </div>
        </div>
      </div>
    </div>
  )
}
