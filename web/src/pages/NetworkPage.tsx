import { useEffect, useState, useRef, useCallback } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import ForceGraph2D from "react-force-graph-2d";
import { Minus, Plus, Maximize2, X } from "lucide-react";
import { getNetworkGraph } from "../api/client";
import type { NetworkGraph, NetworkNode } from "../types";

const NODE_COLORS: Record<string, string> = {
  artist: "#dc2626",
  producer: "#3b82f6",
  label: "#22c55e",
  management: "#f59e0b",
  agency: "#a855f7",
};

const REL_LABELS: Record<string, string> = {
  produced_by: "produced by",
  signed_to: "signed to",
  managed_by: "managed by",
  booked_by: "booked by",
};

interface GraphNode extends Record<string, unknown> {
  id: string;
  label: string;
  type: string;
  score: number | null;
  val: number;
  x?: number;
  y?: number;
}

export function NetworkPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const initialCenter = searchParams.get("center") ?? "";

  const [graph, setGraph] = useState<NetworkGraph | null>(null);
  const [loading, setLoading] = useState(true);
  const [center, setCenter] = useState(initialCenter);
  const [searchInput, setSearchInput] = useState(initialCenter);
  const [depth, setDepth] = useState(2);
  const [selectedNode, setSelectedNode] = useState<NetworkNode | null>(null);
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);

  const containerRef = useRef<HTMLDivElement>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const graphRef = useRef<any>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });

  const fetchGraph = useCallback(async () => {
    setLoading(true);
    setSelectedNode(null);
    try {
      const data = await getNetworkGraph(center || undefined, depth);
      setGraph(data);
    } catch (err) {
      console.error("Failed to fetch network:", err);
    } finally {
      setLoading(false);
    }
  }, [center, depth]);

  useEffect(() => {
    fetchGraph();
  }, [fetchGraph]);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const obs = new ResizeObserver((entries) => {
      const { width, height } = entries[0].contentRect;
      setDimensions({ width, height: Math.max(height, 500) });
    });
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setCenter(searchInput);
  };

  const handleNodeClick = (node: GraphNode) => {
    const n = graph?.nodes.find((gn) => gn.id === node.id);
    if (n) setSelectedNode(n);
  };

  const navigateToArtist = (name: string) => {
    // Find by name in the graph data to get spotify_id
    // For now navigate to network centered on this entity
    setCenter(name);
    setSearchInput(name);
  };

  const graphData = graph
    ? {
        nodes: graph.nodes.map((n) => ({
          id: n.id,
          label: n.label,
          type: n.type,
          score: n.score,
          val: n.type === "artist" ? (n.score ? n.score / 15 : 2) : 1.5,
        })),
        links: graph.links.map((l) => ({
          source: l.source,
          target: l.target,
          relationship: l.relationship,
        })),
      }
    : { nodes: [], links: [] };

  const connectedToHovered = hoveredNode
    ? new Set(
        graphData.links
          .filter(
            (l) =>
              (typeof l.source === "string"
                ? l.source
                : (l.source as GraphNode).id) === hoveredNode ||
              (typeof l.target === "string"
                ? l.target
                : (l.target as GraphNode).id) === hoveredNode
          )
          .flatMap((l) => [
            typeof l.source === "string"
              ? l.source
              : (l.source as GraphNode).id,
            typeof l.target === "string"
              ? l.target
              : (l.target as GraphNode).id,
          ])
      )
    : null;

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Network Visualizer</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            {graph
              ? `${graph.nodes.length} nodes, ${graph.links.length} connections`
              : "Loading..."}
            {center && (
              <span className="text-brand-red-light ml-1">
                centered on {center}
              </span>
            )}
          </p>
        </div>

        <form onSubmit={handleSearch} className="flex items-center gap-2">
          <input
            type="text"
            placeholder="Center on artist..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            className="px-3 py-2 bg-surface-raised border border-surface-border rounded-lg text-sm text-gray-200 placeholder:text-gray-500 focus:outline-none focus:ring-1 focus:ring-brand-red/50 w-48"
          />
          <button
            type="submit"
            className="px-3 py-2 bg-brand-red text-white text-sm font-medium rounded-lg hover:bg-brand-red-dark transition-colors"
          >
            Focus
          </button>
          {center && (
            <button
              type="button"
              onClick={() => {
                setCenter("");
                setSearchInput("");
              }}
              className="px-3 py-2 bg-surface-overlay text-gray-300 text-sm rounded-lg hover:bg-surface-border transition-colors"
            >
              Reset
            </button>
          )}
        </form>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap gap-3 text-xs">
          {Object.entries(NODE_COLORS).map(([type, color]) => (
            <div key={type} className="flex items-center gap-1.5">
              <div
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: color }}
              />
              <span className="text-gray-400 capitalize">{type}</span>
            </div>
          ))}
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500">Depth:</span>
          <button
            onClick={() => setDepth((d) => Math.max(1, d - 1))}
            disabled={depth <= 1}
            className="p-1 rounded bg-surface-overlay border border-surface-border text-gray-400 hover:text-white disabled:opacity-30 transition-colors"
          >
            <Minus size={14} />
          </button>
          <span className="text-sm font-mono text-gray-300 w-4 text-center">
            {depth}
          </span>
          <button
            onClick={() => setDepth((d) => Math.min(3, d + 1))}
            disabled={depth >= 3}
            className="p-1 rounded bg-surface-overlay border border-surface-border text-gray-400 hover:text-white disabled:opacity-30 transition-colors"
          >
            <Plus size={14} />
          </button>
          <button
            onClick={() => graphRef.current?.zoomToFit(400)}
            className="p-1 rounded bg-surface-overlay border border-surface-border text-gray-400 hover:text-white transition-colors ml-2"
            title="Fit to view"
          >
            <Maximize2 size={14} />
          </button>
        </div>
      </div>

      <div className="relative">
        <div
          ref={containerRef}
          className="bg-surface-raised border border-surface-border rounded-xl overflow-hidden"
          style={{ height: "calc(100vh - 280px)", minHeight: 500 }}
        >
          {loading ? (
            <div className="flex items-center justify-center h-full text-gray-500">
              Loading graph...
            </div>
          ) : (
            <ForceGraph2D
              ref={graphRef}
              graphData={graphData}
              width={dimensions.width}
              height={dimensions.height}
              backgroundColor="#1a1a1a"
              onNodeClick={(node) => handleNodeClick(node as GraphNode)}
              onNodeHover={(node) =>
                setHoveredNode(node ? (node as GraphNode).id : null)
              }
              nodeCanvasObject={(
                node: Record<string, unknown>,
                ctx: CanvasRenderingContext2D,
                globalScale: number
              ) => {
                const x = node.x as number;
                const y = node.y as number;
                const type = node.type as string;
                const label = node.label as string;
                const id = node.id as string;
                const val = (node.val as number) ?? 2;
                const r = Math.sqrt(val) * 4;
                const color = NODE_COLORS[type] ?? "#666";

                const dimmed =
                  connectedToHovered && !connectedToHovered.has(id);
                const highlighted = hoveredNode === id;

                // Glow for hovered node
                if (highlighted) {
                  ctx.beginPath();
                  ctx.arc(x, y, r + 3, 0, 2 * Math.PI);
                  ctx.fillStyle = `${color}33`;
                  ctx.fill();
                }

                ctx.beginPath();
                ctx.arc(x, y, r, 0, 2 * Math.PI);
                ctx.fillStyle = dimmed ? `${color}44` : color;
                ctx.fill();

                // Score text inside artist nodes
                if (type === "artist" && node.score && globalScale > 0.5) {
                  ctx.font = `bold ${Math.max(8 / globalScale, 3)}px Inter, sans-serif`;
                  ctx.textAlign = "center";
                  ctx.textBaseline = "middle";
                  ctx.fillStyle = "rgba(255,255,255,0.9)";
                  ctx.fillText(
                    String(Math.round(node.score as number)),
                    x,
                    y
                  );
                }

                // Label below
                if (globalScale > 0.6 || highlighted) {
                  const fontSize = highlighted
                    ? Math.max(12 / globalScale, 4)
                    : Math.max(10 / globalScale, 3);
                  ctx.font = `${highlighted ? "bold " : ""}${fontSize}px Inter, sans-serif`;
                  ctx.textAlign = "center";
                  ctx.textBaseline = "top";
                  ctx.fillStyle = dimmed
                    ? "rgba(255,255,255,0.2)"
                    : "rgba(255,255,255,0.8)";
                  ctx.fillText(label, x, y + r + 2);
                }
              }}
              linkColor={(link: Record<string, unknown>) => {
                if (!connectedToHovered) return "rgba(255,255,255,0.08)";
                const src =
                  typeof link.source === "string"
                    ? link.source
                    : (link.source as GraphNode).id;
                const tgt =
                  typeof link.target === "string"
                    ? link.target
                    : (link.target as GraphNode).id;
                return connectedToHovered.has(src) &&
                  connectedToHovered.has(tgt)
                  ? "rgba(255,255,255,0.25)"
                  : "rgba(255,255,255,0.03)";
              }}
              linkWidth={(link: Record<string, unknown>) => {
                if (!connectedToHovered) return 0.5;
                const src =
                  typeof link.source === "string"
                    ? link.source
                    : (link.source as GraphNode).id;
                const tgt =
                  typeof link.target === "string"
                    ? link.target
                    : (link.target as GraphNode).id;
                return connectedToHovered.has(src) &&
                  connectedToHovered.has(tgt)
                  ? 1.5
                  : 0.3;
              }}
              linkCanvasObjectMode={() => "after"}
              linkCanvasObject={(
                link: Record<string, unknown>,
                ctx: CanvasRenderingContext2D,
                globalScale: number
              ) => {
                if (globalScale < 1.2) return;
                const src = link.source as GraphNode;
                const tgt = link.target as GraphNode;
                if (!src.x || !tgt.x) return;

                const rel = link.relationship as string;
                const label = REL_LABELS[rel] ?? rel;
                const mx = (src.x + tgt.x) / 2;
                const my = ((src.y ?? 0) + (tgt.y ?? 0)) / 2;

                ctx.font = `${Math.max(7 / globalScale, 2)}px Inter, sans-serif`;
                ctx.textAlign = "center";
                ctx.textBaseline = "middle";
                ctx.fillStyle = "rgba(255,255,255,0.25)";
                ctx.fillText(label, mx, my);
              }}
              d3AlphaDecay={0.02}
              d3VelocityDecay={0.3}
              cooldownTime={3000}
            />
          )}
        </div>

        {selectedNode && (
          <div className="absolute top-3 right-3 w-64 bg-surface-raised/95 backdrop-blur-sm border border-surface-border rounded-xl p-4 shadow-xl">
            <div className="flex items-start justify-between mb-3">
              <div>
                <div
                  className="w-3 h-3 rounded-full inline-block mr-2"
                  style={{
                    backgroundColor: NODE_COLORS[selectedNode.type] ?? "#666",
                  }}
                />
                <span className="text-xs text-gray-400 capitalize">
                  {selectedNode.type}
                </span>
              </div>
              <button
                onClick={() => setSelectedNode(null)}
                className="text-gray-500 hover:text-gray-300 transition-colors"
              >
                <X size={14} />
              </button>
            </div>
            <h3 className="font-bold text-gray-100 text-lg leading-tight">
              {selectedNode.label}
            </h3>
            {selectedNode.score !== null && (
              <div className="mt-2 text-sm">
                <span className="text-gray-500">Composite: </span>
                <span className="font-mono text-gray-200">
                  {selectedNode.score.toFixed(1)}
                </span>
              </div>
            )}
            <div className="mt-2 text-xs text-gray-500">
              {graph?.links.filter(
                (l) =>
                  l.source === selectedNode.id || l.target === selectedNode.id
              ).length ?? 0}{" "}
              connections
            </div>
            <div className="mt-3 flex gap-2">
              {selectedNode.type === "artist" && (
                <button
                  onClick={() => navigateToArtist(selectedNode.label)}
                  className="px-2.5 py-1.5 bg-brand-red/10 text-brand-red-light text-xs font-medium rounded-lg border border-brand-red/20 hover:bg-brand-red/20 transition-colors"
                >
                  Center here
                </button>
              )}
              <button
                onClick={() => {
                  navigate(`/`);
                }}
                className="px-2.5 py-1.5 bg-surface-overlay text-gray-300 text-xs rounded-lg border border-surface-border hover:bg-surface-border transition-colors"
              >
                Dashboard
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
