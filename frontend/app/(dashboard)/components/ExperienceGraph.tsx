"use client"

import { useMemo } from "react"
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  type Node,
  type Edge,
  Position,
} from "reactflow"
import "reactflow/dist/style.css"
import type { Relation } from "@/lib/api-client"

const RELATION_COLORS: Record<string, string> = {
  reuse: "#10b981",
  citation: "#3b82f6",
  fork: "#8b5cf6",
  improvement: "#f59e0b",
  dependency: "#ef4444",
}

const RELATION_LABELS: Record<string, string> = {
  reuse: "复用",
  citation: "引用",
  fork: "分叉",
  improvement: "改进",
  dependency: "依赖",
}

interface ExperienceGraphProps {
  experienceId: string
  relations: Relation[]
  onNodeClick?: (id: string) => void
}

export function ExperienceGraph({ experienceId, relations, onNodeClick }: ExperienceGraphProps) {
  const { nodes, edges } = useMemo(() => {
    const nodeMap = new Map<string, Node>()
    const edgeList: Edge[] = []

    // 中心节点（当前经验）
    nodeMap.set(experienceId, {
      id: experienceId,
      type: "input",
      data: { label: "当前经验" },
      position: { x: 0, y: 0 },
      sourcePosition: Position.Right,
      targetPosition: Position.Left,
      style: {
        background: "#1e40af",
        color: "#fff",
        border: "2px solid #3b82f6",
        borderRadius: "8px",
        padding: "8px 16px",
        fontSize: "14px",
        fontWeight: 600,
      },
    })

    // 处理每条关系
    relations.forEach((rel, idx) => {
      const isSource = rel.source_id === experienceId
      const otherId = isSource ? rel.target_id : rel.source_id
      const otherLabel = isSource ? `目标经验` : `来源经验`

      // 添加关联节点
      if (!nodeMap.has(otherId)) {
        const angle = (idx / Math.max(relations.length, 1)) * Math.PI * 2
        const radius = 200
        nodeMap.set(otherId, {
          id: otherId,
          data: { label: `${otherLabel} ${idx + 1}` },
          position: {
            x: Math.cos(angle) * radius,
            y: Math.sin(angle) * radius,
          },
          style: {
            background: "#f3f4f6",
            border: `2px solid ${RELATION_COLORS[rel.relation_type] || "#9ca3af"}`,
            borderRadius: "8px",
            padding: "6px 12px",
            fontSize: "13px",
          },
        })
      }

      // 添加边
      edgeList.push({
        id: rel.id,
        source: rel.source_id,
        target: rel.target_id,
        label: RELATION_LABELS[rel.relation_type] || rel.relation_type,
        labelStyle: { fontSize: 12, fill: "#6b7280" },
        labelBgStyle: { fill: "#f9fafb" },
        style: {
          stroke: RELATION_COLORS[rel.relation_type] || "#9ca3af",
          strokeWidth: 2,
        },
        animated: rel.relation_type === "dependency",
      })
    })

    return { nodes: Array.from(nodeMap.values()), edges: edgeList }
  }, [experienceId, relations])

  if (relations.length === 0) {
    return (
      <div className="text-center py-8 text-gray-400 text-sm">
        暂无图谱关系
      </div>
    )
  }

  return (
    <div style={{ width: "100%", height: 400 }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        fitView
        attributionPosition="bottom-left"
        onNodeClick={(_, node) => onNodeClick?.(node.id)}
        nodesDraggable
        nodesConnectable={false}
        elementsSelectable
        minZoom={0.5}
        maxZoom={2}
      >
        <Background color="#f1f5f9" gap={16} />
        <Controls showInteractive={false} />
        <MiniMap
          nodeColor={(node) => {
            if (node.id === experienceId) return "#1e40af"
            return "#e5e7eb"
          }}
          maskColor="rgba(0, 0, 0, 0.1)"
        />
      </ReactFlow>
    </div>
  )
}
