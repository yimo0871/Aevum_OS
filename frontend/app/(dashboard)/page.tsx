"use client"

import { useQuery } from "@tanstack/react-query"
import { evaluationApi } from "@/lib/api-client"
import { Activity, Database, TrendingUp, Zap, Target, Globe, Shield, Clock } from "lucide-react"

const metricConfig = [
  { key: "experience_reuse_rate", label: "经验复用率", icon: TrendingUp, color: "text-blue-600", format: "percent", inverse: false, suffix: undefined },
  { key: "workflow_success_rate", label: "工作流成功率", icon: Target, color: "text-green-600", format: "percent", inverse: false, suffix: undefined },
  { key: "cross_agent_transfer_rate", label: "跨Agent迁移率", icon: Globe, color: "text-purple-600", format: "percent", inverse: false, suffix: undefined },
  { key: "external_dependency_ratio", label: "外部依赖比例", icon: Shield, color: "text-orange-600", format: "percent", inverse: true, suffix: undefined },
  { key: "learning_velocity", label: "学习速度", icon: Zap, color: "text-yellow-600", format: "number", inverse: false, suffix: "/天" },
  { key: "convergence_speed", label: "收敛速度", icon: Activity, color: "text-cyan-600", format: "percent", inverse: false, suffix: undefined },
  { key: "human_intervention_rate", label: "人类干预率", icon: Clock, color: "text-red-600", format: "percent", inverse: true, suffix: undefined },
] as const

function formatValue(value: number, format: string, suffix?: string) {
  if (format === "percent") return `${(value * 100).toFixed(1)}%`
  if (format === "number") return `${value.toFixed(1)}${suffix || ""}`
  return String(value)
}

export default function DashboardPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["dashboard"],
    queryFn: () => evaluationApi.getDashboard(),
    refetchInterval: 30000,
  })

  if (isLoading) {
    return (
      <div>
        <h1 className="text-2xl font-bold mb-6">Dashboard</h1>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="rounded-lg border p-6 animate-pulse">
              <div className="h-4 bg-gray-200 rounded w-20 mb-3"></div>
              <div className="h-8 bg-gray-200 rounded w-16"></div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div>
        <h1 className="text-2xl font-bold mb-6">Dashboard</h1>
        <div className="rounded-lg border border-red-200 bg-red-50 p-6">
          <p className="text-red-600 font-medium">无法连接后端 API</p>
          <p className="text-sm text-red-400 mt-1">请确保后端服务正在运行 (http://localhost:8000)</p>
        </div>
      </div>
    )
  }

  const metrics = data?.system_metrics
  const stats = data?.experience_stats

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Dashboard</h1>

      {/* 经验统计 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <div className="rounded-lg border p-6">
          <div className="flex items-center justify-between">
            <p className="text-sm text-gray-500">经验总数</p>
            <Database className="w-5 h-5 text-gray-400" />
          </div>
          <p className="text-3xl font-bold mt-2">{stats?.total ?? 0}</p>
        </div>
        <div className="rounded-lg border p-6">
          <div className="flex items-center justify-between">
            <p className="text-sm text-gray-500">已评估</p>
            <Target className="w-5 h-5 text-green-400" />
          </div>
          <p className="text-3xl font-bold mt-2 text-green-600">{stats?.evaluated ?? 0}</p>
        </div>
        <div className="rounded-lg border p-6">
          <div className="flex items-center justify-between">
            <p className="text-sm text-gray-500">待评估</p>
            <Clock className="w-5 h-5 text-orange-400" />
          </div>
          <p className="text-3xl font-bold mt-2 text-orange-600">{stats?.pending ?? 0}</p>
        </div>
        <div className="rounded-lg border p-6">
          <div className="flex items-center justify-between">
            <p className="text-sm text-gray-500">平均置信度</p>
            <TrendingUp className="w-5 h-5 text-blue-400" />
          </div>
          <p className="text-3xl font-bold mt-2 text-blue-600">
            {((stats?.avg_confidence ?? 0) * 100).toFixed(1)}%
          </p>
        </div>
      </div>

      {/* 系统指标 */}
      <h2 className="text-lg font-semibold mb-4">系统指标</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {metricConfig.map(({ key, label, icon: Icon, color, format, suffix, inverse }) => {
          const value = metrics?.[key] ?? 0
          return (
            <div key={key} className="rounded-lg border p-6">
              <div className="flex items-center justify-between mb-3">
                <p className="text-sm text-gray-500">{label}</p>
                <Icon className={`w-5 h-5 ${color}`} />
              </div>
              <p className={`text-2xl font-bold ${color}`}>
                {formatValue(value, format, suffix)}
              </p>
              {inverse && (
                <p className="text-xs text-gray-400 mt-1">越低越好</p>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
