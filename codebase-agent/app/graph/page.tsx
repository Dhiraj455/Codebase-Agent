"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import ReactFlow, {
  Node,
  Edge,
  Background,
  Controls,
  MiniMap,
  Panel,
  useNodesState,
  useEdgesState,
  ConnectionMode,
  MarkerType,
} from "reactflow";
import "reactflow/dist/style.css";

interface GraphData {
  nodes: Array<{
    id: string;
    name: string;
    relative_path: string;
    module_name?: string;
  }>;
  edges: Array<{
    source: string;
    target: string;
  }>;
  cycles: string[][];
  statistics: {
    nodes: number;
    edges: number;
    density?: number;
    is_dag?: boolean;
    strongly_connected_components?: number;
    message?: string;
  };
}

export default function GraphPage() {
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const router = useRouter();

  // React Flow state
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  useEffect(() => {
    const repoName = sessionStorage.getItem("repo_name");
    if (!repoName) {
      router.push("/");
      return;
    }

    // Fetch graph data
    const fetchGraphData = async () => {
      try {
        const response = await fetch(`/api/proxy/graph?repo_name=${encodeURIComponent(repoName)}`);
        
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || "Failed to load graph");
        }

        const data = await response.json();
        setGraphData(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load graph");
      } finally {
        setLoading(false);
      }
    };

    fetchGraphData();
  }, [router]);

  // Transform graph data to React Flow format
  useEffect(() => {
    if (!graphData) return;

    // Create nodes with positions
    const flowNodes: Node[] = graphData.nodes.map((node, index) => {
      // Simple grid layout
      const cols = Math.ceil(Math.sqrt(graphData.nodes.length));
      const row = Math.floor(index / cols);
      const col = index % cols;
      const spacing = 300;

      // Check if node is in a cycle
      const isInCycle = graphData.cycles.some((cycle) =>
        cycle.some((cycleNode) => cycleNode.includes(node.id) || node.id.includes(cycleNode))
      );

      return {
        id: node.id,
        type: "default",
        position: { x: col * spacing, y: row * spacing },
        data: {
          label: node.name || node.relative_path.split("/").pop() || node.id,
          relative_path: node.relative_path,
          module_name: node.module_name,
          isInCycle,
        },
        style: {
          background: isInCycle ? "#fef2f2" : "#ffffff",
          border: isInCycle ? "2px solid #ef4444" : "1px solid #e5e7eb",
          borderRadius: "8px",
          padding: "10px",
          width: 200,
          minHeight: 60,
        },
        className: isInCycle ? "ring-2 ring-red-500" : "",
      };
    });

    // Create edges
    const flowEdges: Edge[] = graphData.edges.map((edge) => {
      // Check if this edge is part of a cycle
      const isCycleEdge = graphData.cycles.some((cycle) => {
        const cycleNodes = cycle.map((n) => n.toLowerCase());
        return (
          cycleNodes.some((n) => edge.source.toLowerCase().includes(n) || n.includes(edge.source.toLowerCase())) &&
          cycleNodes.some((n) => edge.target.toLowerCase().includes(n) || n.includes(edge.target.toLowerCase()))
        );
      });

      return {
        id: `e${edge.source}-${edge.target}`,
        source: edge.source,
        target: edge.target,
        type: "smoothstep",
        animated: isCycleEdge,
        style: {
          stroke: isCycleEdge ? "#ef4444" : "#94a3b8",
          strokeWidth: isCycleEdge ? 3 : 2,
        },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: isCycleEdge ? "#ef4444" : "#94a3b8",
        },
      };
    });

    setNodes(flowNodes);
    setEdges(flowEdges);
  }, [graphData, setNodes, setEdges]);

  // Handle node click
  const onNodeClick = useCallback((_event: React.MouseEvent, node: Node) => {
    setSelectedNode(node);
  }, []);

  // Handle pane click to deselect
  const onPaneClick = useCallback(() => {
    setSelectedNode(null);
  }, []);

  // Get nodes in cycles for highlighting
  const cycleNodeIds = useMemo(() => {
    if (!graphData) return new Set<string>();
    const ids = new Set<string>();
    graphData.cycles.forEach((cycle) => {
      cycle.forEach((nodeId) => {
        graphData.nodes.forEach((node) => {
          if (node.id.includes(nodeId) || nodeId.includes(node.id)) {
            ids.add(node.id);
          }
        });
      });
    });
    return ids;
  }, [graphData]);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-zinc-50 dark:bg-zinc-900">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-zinc-600 dark:text-zinc-400">Loading dependency graph...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-zinc-50 dark:bg-zinc-900">
        <div className="text-center">
          <p className="text-red-600 dark:text-red-400 mb-4">{error}</p>
          <Link href="/analysis" className="text-blue-600 hover:underline">
            ← Back to Analysis
          </Link>
        </div>
      </div>
    );
  }

  if (!graphData) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-zinc-50 dark:bg-zinc-900">
        <div className="text-center">
          <p className="text-zinc-600 dark:text-zinc-400 mb-4">No graph data available</p>
          <Link href="/analysis" className="text-blue-600 hover:underline">
            ← Back to Analysis
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-900 flex flex-col">
      {/* Header */}
      <div className="bg-white dark:bg-zinc-800 border-b border-zinc-200 dark:border-zinc-700 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div>
            <Link
              href="/analysis"
              className="text-blue-600 hover:underline mb-2 inline-block text-sm"
            >
              ← Back to Analysis
            </Link>
            <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-50">
              Dependency Graph
            </h1>
            <p className="text-sm text-zinc-600 dark:text-zinc-400 mt-1">
              {graphData.statistics.nodes} nodes • {graphData.statistics.edges} edges
              {graphData.cycles.length > 0 && (
                <span className="ml-2 text-red-600 dark:text-red-400">
                  • {graphData.cycles.length} circular dependency{graphData.cycles.length !== 1 ? "ies" : "y"}
                </span>
              )}
            </p>
          </div>
          <div className="flex items-center gap-4">
            {graphData.cycles.length > 0 && (
              <div className="flex items-center gap-2 text-sm">
                <div className="w-4 h-4 bg-red-500 rounded"></div>
                <span className="text-zinc-600 dark:text-zinc-400">Circular Dependencies</span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Graph Container */}
      <div className="flex-1 relative">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={onNodeClick}
          onPaneClick={onPaneClick}
          connectionMode={ConnectionMode.Loose}
          fitView
          attributionPosition="bottom-left"
          className="bg-zinc-50 dark:bg-zinc-900"
        >
          <Background color="#e5e7eb" gap={16} />
          <Controls />
          <MiniMap
            nodeColor={(node) => {
              return node.data?.isInCycle ? "#ef4444" : "#94a3b8";
            }}
            maskColor="rgba(0, 0, 0, 0.1)"
          />
          <Panel position="top-right" className="bg-white dark:bg-zinc-800 rounded-lg shadow-lg p-4 border border-zinc-200 dark:border-zinc-700">
            <div className="space-y-2 text-sm">
              <div>
                <span className="font-medium text-zinc-700 dark:text-zinc-300">Nodes:</span>{" "}
                <span className="text-zinc-900 dark:text-zinc-50">{graphData.statistics.nodes}</span>
              </div>
              <div>
                <span className="font-medium text-zinc-700 dark:text-zinc-300">Edges:</span>{" "}
                <span className="text-zinc-900 dark:text-zinc-50">{graphData.statistics.edges}</span>
              </div>
              {graphData.statistics.density !== undefined && (
                <div>
                  <span className="font-medium text-zinc-700 dark:text-zinc-300">Density:</span>{" "}
                  <span className="text-zinc-900 dark:text-zinc-50">
                    {graphData.statistics.density.toFixed(3)}
                  </span>
                </div>
              )}
              {graphData.statistics.is_dag !== undefined && (
                <div>
                  <span className="font-medium text-zinc-700 dark:text-zinc-300">Is DAG:</span>{" "}
                  <span className={graphData.statistics.is_dag ? "text-green-600" : "text-red-600"}>
                    {graphData.statistics.is_dag ? "Yes" : "No"}
                  </span>
                </div>
              )}
              {graphData.statistics.message && (
                <div className="mt-2 p-2 bg-yellow-50 dark:bg-yellow-900/20 rounded border border-yellow-200 dark:border-yellow-800">
                  <p className="text-xs text-yellow-800 dark:text-yellow-300">
                    {graphData.statistics.message}
                  </p>
                </div>
              )}
            </div>
          </Panel>
        </ReactFlow>

        {/* Node Details Panel */}
        {selectedNode && (
          <div className="absolute bottom-4 left-4 bg-white dark:bg-zinc-800 rounded-lg shadow-lg p-4 border border-zinc-200 dark:border-zinc-700 max-w-sm">
            <div className="flex items-start justify-between mb-2">
              <h3 className="font-semibold text-zinc-900 dark:text-zinc-50">
                {selectedNode.data.label}
              </h3>
              <button
                onClick={() => setSelectedNode(null)}
                className="text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-300"
              >
                ×
              </button>
            </div>
            <div className="space-y-2 text-sm">
              {selectedNode.data.relative_path && (
                <div>
                  <span className="font-medium text-zinc-700 dark:text-zinc-300">Path:</span>{" "}
                  <span className="text-zinc-900 dark:text-zinc-50">
                    {selectedNode.data.relative_path}
                  </span>
                </div>
              )}
              {selectedNode.data.module_name && (
                <div>
                  <span className="font-medium text-zinc-700 dark:text-zinc-300">Module:</span>{" "}
                  <span className="text-zinc-900 dark:text-zinc-50">
                    {selectedNode.data.module_name}
                  </span>
                </div>
              )}
              {selectedNode.data.isInCycle && (
                <div className="mt-2 p-2 bg-red-50 dark:bg-red-900/20 rounded border border-red-200 dark:border-red-800">
                  <p className="text-xs text-red-800 dark:text-red-300">
                    ⚠️ Part of a circular dependency
                  </p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
