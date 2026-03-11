"use client";

import { SigmaContainer, useLoadGraph, useRegisterEvents, useSigma } from "@react-sigma/core";
import "@react-sigma/core/lib/style.css";
import Graph from "graphology";
import FA2Layout from "graphology-layout-forceatlas2/worker";
import { useEffect, useMemo, useRef } from "react";
import { useRouter } from "next/navigation";
import { GraphControls } from "./graph-controls";

// Community color palette (12 distinct colors)
const COMMUNITY_COLORS = [
  "#3b82f6", "#ef4444", "#10b981", "#f59e0b", "#8b5cf6",
  "#ec4899", "#06b6d4", "#84cc16", "#f97316", "#6366f1",
  "#14b8a6", "#e11d48",
];

export interface GraphNodeData {
  id: string;
  nome: string;
  page_rank?: number;
  community_id?: number;
  degree_centrality?: number;
  connections: number;
}

export interface GraphEdgeData {
  source: string;
  target: string;
  weight?: number;
}

interface NetworkGraphProps {
  nodes: GraphNodeData[];
  edges: GraphEdgeData[];
  onNodeHover?: (node: GraphNodeData | null) => void;
  onNodePosition?: (position: { x: number; y: number } | null) => void;
}

// Loads graph data into Sigma and runs ForceAtlas2 via Web Worker (non-blocking)
function GraphLoader({ nodes, edges }: Pick<NetworkGraphProps, "nodes" | "edges">) {
  const loadGraph = useLoadGraph();
  const layoutRef = useRef<InstanceType<typeof FA2Layout> | null>(null);

  useEffect(() => {
    // Stop any running layout before rebuilding
    if (layoutRef.current) {
      layoutRef.current.stop();
      layoutRef.current = null;
    }

    const graph = new Graph();

    // Normalize PageRank to size range 3-15
    const maxPageRank = Math.max(...nodes.map((n) => n.page_rank || 0), 0.001);

    nodes.forEach((node) => {
      const normalizedSize = 3 + ((node.page_rank || 0) / maxPageRank) * 12;
      const colorIndex = (node.community_id || 0) % COMMUNITY_COLORS.length;

      graph.addNode(node.id, {
        label: node.nome,
        size: normalizedSize,
        color: COMMUNITY_COLORS[colorIndex],
        x: Math.random() * 100,
        y: Math.random() * 100,
        community: node.community_id,
        pageRank: node.page_rank,
        connections: node.connections,
      });
    });

    (edges ?? []).forEach((edge) => {
      if (graph.hasNode(edge.source) && graph.hasNode(edge.target)) {
        try {
          graph.addEdge(edge.source, edge.target, {
            size: Math.min((edge.weight || 1) * 0.5, 3),
            color: "#d1d5db",
          });
        } catch {
          // Skip duplicate edges
        }
      }
    });

    loadGraph(graph);

    // Run ForceAtlas2 in a Web Worker — avoids blocking the UI thread
    const layout = new FA2Layout(graph, {
      settings: {
        gravity: 1,
        scalingRatio: 10,
        barnesHutOptimize: true,
      },
    });
    layoutRef.current = layout;
    layout.start();

    // Stop after convergence window (~3s for typical board network sizes)
    const timer = setTimeout(() => {
      layout.stop();
      layoutRef.current = null;
    }, 3000);

    return () => {
      clearTimeout(timer);
      layout.stop();
      layoutRef.current = null;
    };
  }, [loadGraph, nodes, edges]);

  return null;
}

// Handles click and hover events on graph nodes
function GraphEvents({ nodes, onNodeHover, onNodePosition }: {
  nodes: GraphNodeData[];
  onNodeHover?: (node: GraphNodeData | null) => void;
  onNodePosition?: (position: { x: number; y: number } | null) => void;
}) {
  const sigma = useSigma();
  const registerEvents = useRegisterEvents();
  const router = useRouter();

  // O(1) lookup map — avoids O(n²) nodes.find() inside forEachNode callbacks
  const nodeMap = useMemo(
    () => new Map(nodes.map((n) => [n.id, n])),
    [nodes],
  );

  useEffect(() => {
    registerEvents({
      clickNode: (event) => {
        router.push(`/members/${event.node}`);
      },
      enterNode: (event) => {
        const graph = sigma.getGraph();
        const nodeData = nodeMap.get(event.node);

        if (onNodeHover) onNodeHover(nodeData || null);

        // Get viewport position for tooltip
        const nodeDisplayData = sigma.getNodeDisplayData(event.node);
        if (nodeDisplayData && onNodePosition) {
          const viewportPos = sigma.graphToViewport({
            x: nodeDisplayData.x,
            y: nodeDisplayData.y,
          });
          onNodePosition({ x: viewportPos.x, y: viewportPos.y });
        }

        // Dim non-neighbor nodes
        const neighbors = new Set(graph.neighbors(event.node));
        neighbors.add(event.node);

        graph.forEachNode((node, attrs) => {
          if (neighbors.has(node)) {
            graph.setNodeAttribute(node, "highlighted", true);
            graph.setNodeAttribute(node, "color", attrs.color || COMMUNITY_COLORS[0]);
          } else {
            graph.setNodeAttribute(node, "color", "#d1d5db");
            graph.setNodeAttribute(node, "label", "");
          }
        });

        graph.forEachEdge((edge, attrs, source, target) => {
          if (neighbors.has(source) && neighbors.has(target)) {
            graph.setEdgeAttribute(edge, "color", "#9ca3af");
          } else {
            graph.setEdgeAttribute(edge, "color", "#e5e7eb");
          }
        });

        sigma.refresh();
      },
      leaveNode: () => {
        if (onNodeHover) onNodeHover(null);
        if (onNodePosition) onNodePosition(null);

        const graph = sigma.getGraph();

        // Restore original colors
        graph.forEachNode((node) => {
          const community = graph.getNodeAttribute(node, "community") ?? 0;
          const colorIndex = community % COMMUNITY_COLORS.length;
          graph.setNodeAttribute(node, "color", COMMUNITY_COLORS[colorIndex]);
          graph.removeNodeAttribute(node, "highlighted");

          // Restore label via O(1) map lookup (was O(n²) with nodes.find inside forEachNode)
          const original = nodeMap.get(node);
          if (original) {
            graph.setNodeAttribute(node, "label", original.nome);
          }
        });

        graph.forEachEdge((edge) => {
          graph.setEdgeAttribute(edge, "color", "#d1d5db");
        });

        sigma.refresh();
      },
    });
  }, [registerEvents, sigma, router, nodeMap, onNodeHover, onNodePosition]);

  return null;
}

export function NetworkGraph({ nodes, edges, onNodeHover, onNodePosition }: NetworkGraphProps) {
  if (nodes.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-[var(--color-text-3)]">
        Nenhum dado disponivel para visualizacao
      </div>
    );
  }

  return (
    <SigmaContainer
      style={{ height: "100%", width: "100%" }}
      settings={{
        renderLabels: true,
        labelRenderedSizeThreshold: 8,
        labelSize: 12,
        defaultEdgeType: "line",
        enableEdgeEvents: false,
      }}
    >
      <GraphLoader nodes={nodes} edges={edges} />
      <GraphEvents nodes={nodes} onNodeHover={onNodeHover} onNodePosition={onNodePosition} />
      <GraphControls />
    </SigmaContainer>
  );
}
