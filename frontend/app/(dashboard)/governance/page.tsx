"use client"

import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { governanceApi } from "@/lib/api-client"

export default function GovernancePage() {
  const [experienceId, setExperienceId] = useState("")

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold">经验治理</h1>
      <div className="mb-6 flex gap-3">
        <input
          type="text"
          placeholder="输入经验 ID"
          value={experienceId}
          onChange={(e) => setExperienceId(e.target.value)}
          className="flex-1 rounded-md border px-3 py-2 text-sm"
        />
      </div>
      {experienceId && (
        <div className="grid gap-6 md:grid-cols-2">
          <TrustPanel experienceId={experienceId} />
          <LineagePanel experienceId={experienceId} />
        </div>
      )}
    </div>
  )
}

function TrustPanel({ experienceId }: { experienceId: string }) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["trust", experienceId],
    queryFn: () => governanceApi.getTrust(experienceId),
    enabled: !!experienceId,
  })

  return (
    <div className="rounded-lg border p-4">
      <h3 className="mb-3 font-semibold">信任评分</h3>
      {isLoading && <p className="text-gray-500">加载中...</p>}
      {error && <p className="text-red-600 text-sm">{(error as Error).message}</p>}
      {data && (
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <span className="text-3xl font-bold text-blue-600">
              {(data.trust_score * 100).toFixed(1)}%
            </span>
          </div>
          <dl className="space-y-1 text-sm">
            <div className="flex justify-between">
              <dt className="text-gray-600">使用次数</dt>
              <dd>{data.metrics.usage_count}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-600">成功率</dt>
              <dd>{(data.metrics.success_rate * 100).toFixed(0)}%</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-600">引用次数</dt>
              <dd>{data.metrics.citation_count}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-600">复用次数</dt>
              <dd>{data.metrics.reuse_count}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-600">稳定性</dt>
              <dd>{(data.metrics.stability * 100).toFixed(0)}%</dd>
            </div>
          </dl>
        </div>
      )}
    </div>
  )
}

function LineagePanel({ experienceId }: { experienceId: string }) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["lineage", experienceId],
    queryFn: () => governanceApi.getLineage(experienceId),
    enabled: !!experienceId,
  })

  return (
    <div className="rounded-lg border p-4">
      <h3 className="mb-3 font-semibold">经验谱系</h3>
      {isLoading && <p className="text-gray-500">加载中...</p>}
      {error && <p className="text-red-600 text-sm">{(error as Error).message}</p>}
      {data && (
        <div className="space-y-4">
          <div>
            <h4 className="mb-2 text-sm font-medium text-gray-700">来源（祖先）</h4>
            {data.ancestors.length === 0 ? (
              <p className="text-xs text-gray-400">无</p>
            ) : (
              <ul className="space-y-1">
                {data.ancestors.map((a) => (
                  <li key={a.relation_id} className="text-xs">
                    <span className="inline-block rounded bg-gray-100 px-1.5 py-0.5 mr-1">
                      {a.relation_type}
                    </span>
                    {a.experience?.intent || a.source_experience_id}
                  </li>
                ))}
              </ul>
            )}
          </div>
          <div>
            <h4 className="mb-2 text-sm font-medium text-gray-700">分叉/改进（后代）</h4>
            {data.descendants.length === 0 ? (
              <p className="text-xs text-gray-400">无</p>
            ) : (
              <ul className="space-y-1">
                {data.descendants.map((d) => (
                  <li key={d.relation_id} className="text-xs">
                    <span className="inline-block rounded bg-gray-100 px-1.5 py-0.5 mr-1">
                      {d.relation_type}
                    </span>
                    {d.experience?.intent || d.target_experience_id}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
