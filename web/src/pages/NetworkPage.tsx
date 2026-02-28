import { useEffect, useState, useRef, useCallback, useMemo } from "react";
import { useSearchParams, useNavigate, Link } from "react-router-dom";
import ForceGraph2D from "react-force-graph-2d";
import { Minus, Plus, Maximize2, X, Eye, EyeOff, User } from "lucide-react";
import { getNetworkGraph } from "../api/client";
import type { NetworkGraph, NetworkNode } from "../types";

const NODE_COLORS: Record<string, string> = {
  artist: "#dc2626",
  producer: "#3b82f6",
  label: "#22c55e",
  management: "#f59e0b",
  agency: "#a855f7",
};

const LINK_COLORS: Record<string, string> = {
  produced_by: "#3b82f6",
  shared_producer: "#f97316",
  similar_artist: "#06b6d4",
  signed_to: "#22c55e",
  managed_by: "#f59e0b",
  booked_by: "#a855f7",
  related_artist: "#06b6d4",
};

const REL_LABELS: Record<string, string> = {
  produced_by: "produced by",
  shared_producer: "shared producer",
  similar_artist: "similar",
  signed_to: "signed to",
  managed_by: "managed by",
  booked_by: "booked by",
  related_artist: "related",
};

interface GraphNode extends Record<string, unknown> {
  id: string;
  label: string;
  type: string;
  score: number | null;
  spotify_id?: string;
  val: number;
  x?: number;
  y?: number;
}

interface GraphLink extends Record<string, unknown> {
  source: string | GraphNode;
  target: string | GraphNode;
  relationship: string;
}

function getLinkId(link: GraphLink): [string, string] {
  const src = typeof link.source === "string" ? link.source : link.source.id;
  const tgt = typeof link.target === "string" ? link.target : link.target.id;
  return [src, tgt];
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
  const [artistOnly, setArtistOnly] = useState(false);
  const [topN, setTopN] = useState<number | null>(initialCenter ? null : 20);

  // Relationship type filters -- all on by default
  const [relFilters, setRelFilters] = useState<Record<string, boolean>>({
    produced_by: true,
    shared_producer: true,
    similar_artist: true,
    signed_to: true,
    managed_by: true,
    booked_by: true,
    related_artist: true,
  });

  const containerRef = useRef<HTMLDivElement>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const graphRef = useRef<any>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });

  const fetchGraph = useCallback(async () => {
    setLoading(true);
    setSelectedNode(null);
    try {
      const data = await getNetworkGraph(center || undefined, depth, center ? undefined : topN ?? undefined);
      setGraph(data);
    } catch (err) {
      console.error("Failed to fetch network:", err);
    } finally {
      setLoading(false);
    }
  }, [center, depth, topN]);

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
    if (searchInput) setTopN(null);
  };

  const handleNodeClick = (node: GraphNode) => {
    const n = graph?.nodes.find((gn) => gn.id === node.id);
    if (n) setSelectedNode(n);
  };

  const toggleRelFilter = (rel: string) => {
    setRelFilters((prev) => ({ ...prev, [rel]: !prev[rel] }));
  };

  // Build filtered graph data
  const graphData = useMemo(() => {
    if (!graph) return { nodes: [], links: [] };

    // Filter links by relationship type
    const filteredLinks = graph.links.filter((l) => relFilters[l.relationship] !== false);

    // In artist-only mode, only keep links between artists
    const finalLinks = artistOnly
      ? filteredLinks.filter((l) => {
          const srcNode = graph.nodes.find((n) => n.id === l.source);
          const tgtNode = graph.nodes.find((n) => n.id === l.target);
          return srcNode?.type === "artist" && tgtNode?.type === "artist";
        })
      : filteredLinks;

    // Only include nodes that have at least one visible link
    const connectedIds = new Set<string>();
    for (const l of finalLinks) {
      connectedIds.add(l.source);
      connectedIds.add(l.target);
    }

    const filteredNodes = artistOnly
      ? graph.nodes.filter((n) => n.type === "artist" && connectedIds.has(n.id))
      : graph.nodes.filter((n) => connectedIds.has(n.id));

    // Add isolated artists back (so they're visible even without connections)
    if (!artistOnly) {
      for (const n of graph.nodes) {
        if (n.type === "artist" && !connectedIds.has(n.id)) {
          filteredNodes.push(n);
        }
      }
    }

    return {
      nodes: filteredNodes.map((n) => ({
        id: n.id,
        label: n.label,
        type: n.type,
        score: n.score,
        spotify_id: n.spotify_id,
        val: n.type === "artist" ? (n.score ? n.score / 10 : 4) : 1.5,
      })),
      links: finalLinks.map((l) => ({
        source: l.source,
        target: l.target,
        relationship: l.relationship,
      })),
    };
  }, [graph, relFilters, artistOnly]);

  // Configure d3 forces for better spacing
  useEffect(() => {
    if (graphRef.current) {
      graphRef.current.d3Force('charge').strength(-200);
    }
  }, [graphData]);

  // Count visible links by type
  const linkCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    if (graph) {
      for (const l of graph.links) {
        counts[l.relationship] = (counts[l.relationship] || 0) + 1;
      }
    }
    return counts;
  }, [graph]);

  const connectedToHovered = hoveredNode
    ? new Set(
        graphData.links
          .filter((l) => {
            const [src, tgt] = getLinkId(l as GraphLink);
            return src === hoveredNode || tgt === hoveredNode;
          })
          .flatMap((l) => {
            const [src, tgt] = getLinkId(l as GraphLink);
            return [src, tgt];
          })
      )
    : null;

  // Get connections for selected node grouped by type
  const selectedConnections = useMemo(() => {
    if (!selectedNode || !graph) return null;
    const groups: Record<string, { name: string; type: string; direction: string }[]> = {};
    for (const l of graph.links) {
      if (l.source === selectedNode.id || l.target === selectedNode.id) {
        const rel = l.relationship;
        if (!groups[rel]) groups[rel] = [];
        const otherId = l.source === selectedNode.id ? l.target : l.source;
        const otherNode = graph.nodes.find((n) => n.id === otherId);
        if (otherNode) {
          groups[rel].push({
            name: otherNode.label,
            type: otherNode.type,
            direction: l.source === selectedNode.id ? "out" : "in",
          });
        }
      }
    }
    return groups;
  }, [selectedNode, graph]);

  return (
    <div className="space-y-3">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-display font-bold tracking-tight">Network Visualizer</h1>
          <p className="text-xs text-steel font-mono mt-0.5">
            {graph
              ? `${graphData.nodes.length} nodes, ${graphData.links.length} connections`
              : "Loading..."}
            {center && (
              <span className="text-accent ml-1">
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
            className="px-3 py-2 bg-surface-raised border border-surface-border rounded-lg text-sm text-gray-200 placeholder:text-steel focus:outline-none focus:ring-1 focus:ring-accent/50 w-48"
          />
          <button
            type="submit"
            className="px-3 py-2 bg-accent text-white text-sm font-medium rounded-lg hover:bg-brand-red-dark transition-colors"
          >
            Focus
          </button>
          {center && (
            <button
              type="button"
              onClick={() => {
                setCenter("");
                setSearchInput("");
                setTopN(20);
              }}
              className="px-3 py-2 bg-surface-raised border border-surface-border text-steel text-sm rounded-lg hover:text-gray-200 transition-colors"
            >
              Reset
            </button>
          )}
        </form>
      </div>

      {/* Controls row */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        {/* Relationship type filters */}
        <div className="flex flex-wrap gap-1.5">
          {Object.entries(linkCounts).map(([rel, count]) => (
            <button
              key={rel}
              onClick={() => toggleRelFilter(rel)}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium transition-all ${
                relFilters[rel] !== false
                  ? "ring-1 ring-opacity-50 text-white"
                  : "opacity-30 text-gray-400"
              }`}
              style={{
                backgroundColor: relFilters[rel] !== false ? `${LINK_COLORS[rel] ?? "#666"}22` : "transparent",
                border: `1px solid ${relFilters[rel] !== false ? (LINK_COLORS[rel] ?? "#666") + "66" : "#2a2d3a"}`,
              }}
            >
              <div
                className="w-2 h-2 rounded-full"
                style={{ backgroundColor: LINK_COLORS[rel] ?? "#666" }}
              />
              {REL_LABELS[rel] ?? rel}
              <span className="text-gray-500 ml-0.5">{count}</span>
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2">
          {/* Artist-only toggle */}
          <button
            onClick={() => setArtistOnly(!artistOnly)}
            className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium border transition-all ${
              artistOnly
                ? "bg-accent/10 border-accent/30 text-accent"
                : "bg-surface-raised border-surface-border text-gray-400 hover:text-gray-200"
            }`}
          >
            {artistOnly ? <Eye size={13} /> : <EyeOff size={13} />}
            Artists only
          </button>

          {/* Node type legend */}
          <div className="hidden sm:flex gap-2 text-xs ml-2">
            {Object.entries(NODE_COLORS).map(([type, color]) => (
              <div key={type} className="flex items-center gap-1">
                <div
                  className="w-2.5 h-2.5 rounded-full"
                  style={{ backgroundColor: color }}
                />
                <span className="text-gray-500 capitalize">{type}</span>
              </div>
            ))}
          </div>

          {/* Top N toggle */}
          {!center && (
            <div className="flex items-center gap-1 mr-2">
              {[20, null].map((n) => (
                <button
                  key={n ?? "all"}
                  onClick={() => setTopN(n)}
                  className={`px-2 py-1 text-xs rounded transition-all ${
                    topN === n
                      ? "bg-accent/10 text-accent border border-accent/30"
                      : "bg-surface-overlay border border-surface-border text-gray-400 hover:text-gray-200"
                  }`}
                >
                  {n ? `Top ${n}` : "All"}
                </button>
              ))}
            </div>
          )}

          <span className="text-xs text-gray-600 ml-2">Depth:</span>
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
            className="p-1 rounded bg-surface-overlay border border-surface-border text-gray-400 hover:text-white transition-colors ml-1"
            title="Fit to view"
          >
            <Maximize2 size={14} />
          </button>
        </div>
      </div>

      <div className="relative">
        <div
          ref={containerRef}
          className="border border-surface-border rounded-xl overflow-hidden"
          style={{ height: "calc(100vh - 300px)", minHeight: 500 }}
        >
          {loading ? (
            <div className="flex flex-col items-center justify-center h-full gap-3 text-gray-500">
              <div className="w-6 h-6 border-2 border-gray-600 border-t-brand-red rounded-full animate-spin" />
              Loading graph...
            </div>
          ) : (
            <ForceGraph2D
              ref={graphRef}
              graphData={graphData}
              width={dimensions.width}
              height={dimensions.height}
              backgroundColor="#05060a"
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
                const r = type === "artist" ? Math.sqrt(val) * 4.5 : Math.sqrt(val) * 3;
                const color = NODE_COLORS[type] ?? "#666";

                const dimmed =
                  connectedToHovered && !connectedToHovered.has(id);
                const highlighted = hoveredNode === id;

                // Glow for hovered node
                if (highlighted) {
                  ctx.beginPath();
                  ctx.arc(x, y, r + 4, 0, 2 * Math.PI);
                  ctx.fillStyle = `${color}40`;
                  ctx.fill();
                }

                ctx.beginPath();
                ctx.arc(x, y, r, 0, 2 * Math.PI);
                ctx.fillStyle = dimmed ? `${color}33` : color;
                ctx.fill();

                // Thin border ring on artist nodes
                if (type === "artist") {
                  ctx.strokeStyle = dimmed ? `${color}22` : `${color}aa`;
                  ctx.lineWidth = 0.5;
                  ctx.stroke();
                }

                // Score text inside artist nodes
                if (type === "artist" && node.score && globalScale > 0.4) {
                  ctx.font = `bold ${Math.max(9 / globalScale, 3)}px DM Sans, sans-serif`;
                  ctx.textAlign = "center";
                  ctx.textBaseline = "middle";
                  ctx.fillStyle = dimmed ? "rgba(255,255,255,0.3)" : "rgba(255,255,255,0.95)";
                  ctx.fillText(
                    String(Math.round(node.score as number)),
                    x,
                    y
                  );
                }

                // Label below -- always show for artists if not too zoomed out
                const showLabel = type === "artist"
                  ? globalScale > 0.35 || highlighted
                  : globalScale > 0.9 || highlighted;

                if (showLabel) {
                  const fontSize = highlighted
                    ? Math.max(12 / globalScale, 4)
                    : type === "artist"
                    ? Math.max(10 / globalScale, 3)
                    : Math.max(8 / globalScale, 2.5);
                  ctx.font = `${highlighted ? "bold " : ""}${fontSize}px DM Sans, sans-serif`;
                  ctx.textAlign = "center";
                  ctx.textBaseline = "top";
                  ctx.fillStyle = dimmed
                    ? "rgba(255,255,255,0.1)"
                    : type === "artist"
                    ? "rgba(255,255,255,0.85)"
                    : "rgba(255,255,255,0.5)";
                  ctx.fillText(label, x, y + r + 2);
                }
              }}
              linkColor={(link: Record<string, unknown>) => {
                const rel = link.relationship as string;
                const baseColor = LINK_COLORS[rel] ?? "#666";
                if (!connectedToHovered) return baseColor + "30";
                const [src, tgt] = getLinkId(link as GraphLink);
                return connectedToHovered.has(src) &&
                  connectedToHovered.has(tgt)
                  ? baseColor + "90"
                  : baseColor + "08";
              }}
              linkWidth={(link: Record<string, unknown>) => {
                const rel = link.relationship as string;
                const base = rel === "shared_producer" || rel === "similar_artist" || rel === "related_artist" ? 1.2 : 0.6;
                if (!connectedToHovered) return base;
                const [src, tgt] = getLinkId(link as GraphLink);
                return connectedToHovered.has(src) &&
                  connectedToHovered.has(tgt)
                  ? base * 2.5
                  : base * 0.3;
              }}
              linkCurvature={(link: Record<string, unknown>) => {
                const rel = link.relationship as string;
                // Curve shared_producer/similar links slightly to distinguish from industry links
                if (rel === "shared_producer") return 0.15;
                if (rel === "similar_artist" || rel === "related_artist") return 0.2;
                return 0;
              }}
              linkLineDash={(link: Record<string, unknown>) => {
                const rel = link.relationship as string;
                if (rel === "shared_producer") return [4, 2];
                if (rel === "similar_artist" || rel === "related_artist") return [2, 2];
                return [];
              }}
              linkCanvasObjectMode={() => "after"}
              linkCanvasObject={(
                link: Record<string, unknown>,
                ctx: CanvasRenderingContext2D,
                globalScale: number
              ) => {
                // Only show link labels when hovered and zoomed in enough
                if (globalScale < 1.5) return;
                const src = link.source as GraphNode;
                const tgt = link.target as GraphNode;
                if (!src.x || !tgt.x) return;

                const srcId = src.id;
                const tgtId = tgt.id;
                if (!connectedToHovered) return;
                if (!connectedToHovered.has(srcId) || !connectedToHovered.has(tgtId)) return;

                const rel = link.relationship as string;
                const label = REL_LABELS[rel] ?? rel;
                const mx = (src.x + tgt.x) / 2;
                const my = ((src.y ?? 0) + (tgt.y ?? 0)) / 2;

                ctx.font = `${Math.max(7 / globalScale, 2)}px DM Sans, sans-serif`;
                ctx.textAlign = "center";
                ctx.textBaseline = "middle";
                ctx.fillStyle = (LINK_COLORS[rel] ?? "#666") + "99";
                ctx.fillText(label, mx, my);
              }}
              d3AlphaDecay={0.015}
              d3VelocityDecay={0.25}
              cooldownTime={4000}
            />
          )}
        </div>

        {/* Selected node detail panel */}
        {selectedNode && selectedConnections && (
          <div className="absolute top-3 right-3 w-72 card p-4 max-h-[80%] overflow-y-auto">
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-center gap-2">
                <div
                  className="w-3 h-3 rounded-full"
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

            {/* Connections grouped by type */}
            <div className="mt-3 space-y-3">
              {Object.entries(selectedConnections).map(([rel, items]) => (
                <div key={rel}>
                  <div className="flex items-center gap-1.5 mb-1">
                    <div
                      className="w-2 h-2 rounded-full"
                      style={{ backgroundColor: LINK_COLORS[rel] ?? "#666" }}
                    />
                    <span className="text-xs font-medium text-gray-400 uppercase tracking-wider">
                      {REL_LABELS[rel] ?? rel}
                    </span>
                    <span className="text-xs text-gray-600">{items.length}</span>
                  </div>
                  <div className="space-y-0.5 ml-3.5">
                    {items.map((item, i) => (
                      <button
                        key={i}
                        onClick={() => {
                          setCenter(item.name);
                          setSearchInput(item.name);
                        }}
                        className="block text-xs text-gray-300 hover:text-white transition-colors"
                      >
                        {item.name}
                        <span className="text-gray-600 ml-1 capitalize">
                          ({item.type})
                        </span>
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-3 flex flex-wrap gap-2">
              {selectedNode.type === "artist" && (
                <button
                  onClick={() => {
                    setCenter(selectedNode.label);
                    setSearchInput(selectedNode.label);
                  }}
                  className="px-2.5 py-1.5 bg-brand-red/10 text-brand-red-light text-xs font-medium rounded-lg border border-brand-red/20 hover:bg-brand-red/20 transition-colors"
                >
                  Center here
                </button>
              )}
              {selectedNode.type === "artist" && selectedNode.spotify_id && (
                <Link
                  to={`/artist/${selectedNode.spotify_id}`}
                  className="flex items-center gap-1 px-2.5 py-1.5 bg-accent text-white text-xs font-medium rounded-lg hover:bg-brand-red-dark transition-colors"
                >
                  <User size={12} />
                  View Profile
                </Link>
              )}
              <button
                onClick={() => {
                  if (selectedNode.type === "label") {
                    navigate(`/?label=${encodeURIComponent(selectedNode.label)}`);
                  } else if (selectedNode.type === "management" || selectedNode.type === "agency" || selectedNode.type === "producer") {
                    navigate(`/?search=${encodeURIComponent(selectedNode.label)}`);
                  } else {
                    navigate("/");
                  }
                }}
                className="px-2.5 py-1.5 bg-surface-overlay text-gray-300 text-xs rounded-lg border border-surface-border hover:bg-surface-border transition-colors"
              >
                {selectedNode.type === "label"
                  ? `${selectedNode.label} roster`
                  : selectedNode.type === "artist"
                  ? "Dashboard"
                  : `Find artists`}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
