import React from "react"
import { render, screen, fireEvent } from "@testing-library/react"
import { ExperienceGraph } from "@/app/(dashboard)/components/ExperienceGraph"
import type { Relation } from "@/lib/api-client"

// Mock reactflow as simple divs to avoid complex SVG rendering in jsdom
jest.mock("reactflow", () => ({
  __esModule: true,
  default: ({ nodes, edges, onNodeClick }: any) => (
    <div data-testid="react-flow">
      <span data-testid="nodes-count">{nodes.length}</span>
      <span data-testid="edges-count">{edges.length}</span>
      {nodes.map((n: any) => (
        <div key={n.id} data-testid={`node-${n.id}`} onClick={() => onNodeClick?.(null, n)}>
          {n.data.label}
        </div>
      ))}
      {edges.map((e: any) => (
        <div key={e.id} data-testid={`edge-${e.id}`}>{e.label}</div>
      ))}
    </div>
  ),
  Background: () => <div data-testid="background" />,
  Controls: () => <div data-testid="controls" />,
  MiniMap: () => <div data-testid="minimap" />,
  Position: { Left: "left", Right: "right", Top: "top", Bottom: "bottom" },
}))

jest.mock("@/lib/api-client", () => require("__mocks__/api-client"))

const mockRelations: Relation[] = [
  {
    id: "rel-1",
    source_id: "exp-1",
    target_id: "exp-2",
    relation_type: "reuse",
    weight: 0.8,
    metadata: {},
    created_at: "2024-01-01T00:00:00Z",
  },
  {
    id: "rel-2",
    source_id: "exp-3",
    target_id: "exp-1",
    relation_type: "citation",
    weight: 0.6,
    metadata: {},
    created_at: "2024-01-01T00:00:00Z",
  },
]

describe("ExperienceGraph", () => {
  it("shows empty state when no relations", () => {
    render(<ExperienceGraph experienceId="exp-1" relations={[]} />)
    expect(screen.getByText("暂无图谱关系")).toBeInTheDocument()
  })

  it("renders graph nodes when relations exist", () => {
    render(<ExperienceGraph experienceId="exp-1" relations={mockRelations} />)
    expect(screen.getByTestId("react-flow")).toBeInTheDocument()
    // exp-1 (center) + exp-2 + exp-3 = 3 nodes
    expect(screen.getByTestId("nodes-count").textContent).toBe("3")
    // 2 edges
    expect(screen.getByTestId("edges-count").textContent).toBe("2")
  })

  it("renders relation labels on edges", () => {
    render(<ExperienceGraph experienceId="exp-1" relations={mockRelations} />)
    expect(screen.getByTestId("edge-rel-1").textContent).toBe("复用")
    expect(screen.getByTestId("edge-rel-2").textContent).toBe("引用")
  })

  it("calls onNodeClick when a node is clicked", () => {
    const onNodeClick = jest.fn()
    render(
      <ExperienceGraph
        experienceId="exp-1"
        relations={mockRelations}
        onNodeClick={onNodeClick}
      />
    )
    fireEvent.click(screen.getByTestId("node-exp-2"))
    expect(onNodeClick).toHaveBeenCalledWith("exp-2")
  })

  it("renders the center node with correct label", () => {
    render(<ExperienceGraph experienceId="exp-1" relations={mockRelations} />)
    expect(screen.getByTestId("node-exp-1").textContent).toBe("当前经验")
  })
})
