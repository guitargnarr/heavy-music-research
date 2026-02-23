import { useEffect, useState, useRef, useCallback } from "react";
import { useSearchParams } from "react-router-dom";
import ForceGraph2D from "react-force-graph-2d";
import { getNetworkGraph } from "../api/client";
import type { NetworkGraph } from "../types";

const NODE_COLORS: Record<string, string> = {
  artist: "#dc2626",
  producer: "#3b82f6",
  label: "#22c55e",
  management: "#f59e0b",
  agency: "#a855f7",
};

export function NetworkPage() {
  const [searchParams] = useSearchParams();
  const initialCenter = searchParams.get("center") ?? "";
  const [graph, setGraph] = useState<NetworkGraph | null>(null);
  const [loading, setLoading] = useState(true);
  const [center, setCenter] = useState(initialCenter);
  const [searchInput, setSearchInput] = useState(initialCenter);
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });

  const fetchGraph = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getNetworkGraph(center || undefined, 2);
      setGraph(data);
    } catch (err) {
      console.error("Failed to fetch network:", err);
    } finally {
      setLoading(false);
    }
  }, [center]);

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

  const graphData = graph
    ? {
        nodes: graph.nodes.map((n) => ({
          id: n.id,
          label: n.label,
          type: n.type,
          score: n.score,
          val: n.type === "artist" ? (n.score ? n.score / 20 : 2) : 1.5,
        })),
        links: graph.links.map((l) => ({
          source: l.source,
          target: l.target,
          relationship: l.relationship,
        })),
      }
    : { nodes: [], links: [] };

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Network Visualizer</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            {graph ? `${graph.nodes.length} nodes, ${graph.links.length} links` : "Loading..."}
          </p>
        </div>

        <form onSubmit={handleSearch} className="flex items-center gap-2">
          <input
            type="text"
            placeholder="Center on artist..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            className="px-3 py-2 bg-surface-raised border border-surface-border rounded-lg text-sm text-gray-200 placeholder:text-gray-500 focus:outline-none focus:ring-1 focus:ring-brand-red/50"
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

      <div className="flex flex-wrap gap-3 text-xs">
        {Object.entries(NODE_COLORS).map(([type, color]) => (
          <div key={type} className="flex items-center gap-1.5">
            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: color }} />
            <span className="text-gray-400 capitalize">{type}</span>
          </div>
        ))}
      </div>

      <div
        ref={containerRef}
        className="bg-surface-raised border border-surface-border rounded-xl overflow-hidden"
        style={{ height: "calc(100vh - 260px)", minHeight: 500 }}
      >
        {loading ? (
          <div className="flex items-center justify-center h-full text-gray-500">
            Loading graph...
          </div>
        ) : (
          <ForceGraph2D
            graphData={graphData}
            width={dimensions.width}
            height={dimensions.height}
            backgroundColor="#1a1a1a"
            nodeColor={(node: Record<string, unknown>) =>
              NODE_COLORS[(node.type as string) ?? "artist"] ?? "#666"
            }
            nodeLabel={(node: Record<string, unknown>) => {
              const label = node.label as string;
              const score = node.score as number | null;
              return score ? `${label} (${score.toFixed(0)})` : label;
            }}
            nodeCanvasObject={(
              node: Record<string, unknown>,
              ctx: CanvasRenderingContext2D,
              globalScale: number,
            ) => {
              const x = node.x as number;
              const y = node.y as number;
              const type = node.type as string;
              const label = node.label as string;
              const val = (node.val as number) ?? 2;
              const r = Math.sqrt(val) * 4;
              const color = NODE_COLORS[type] ?? "#666";

              ctx.beginPath();
              ctx.arc(x, y, r, 0, 2 * Math.PI);
              ctx.fillStyle = color;
              ctx.fill();

              if (globalScale > 0.7) {
                ctx.font = `${Math.max(10 / globalScale, 3)}px Inter, sans-serif`;
                ctx.textAlign = "center";
                ctx.textBaseline = "top";
                ctx.fillStyle = "rgba(255,255,255,0.8)";
                ctx.fillText(label, x, y + r + 2);
              }
            }}
            linkColor={() => "rgba(255,255,255,0.08)"}
            linkWidth={0.5}
            d3AlphaDecay={0.02}
            d3VelocityDecay={0.3}
          />
        )}
      </div>
    </div>
  );
}
