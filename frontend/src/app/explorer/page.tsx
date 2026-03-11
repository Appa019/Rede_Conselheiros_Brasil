"use client";

import { useState, useCallback } from "react";
import dynamic from "next/dynamic";
import { Loader2 } from "lucide-react";
import { Header } from "@/components/layout/header";
import { GraphTooltip } from "@/components/graph/graph-tooltip";
import { GraphFilters, type GraphFilterValues } from "@/components/filters/graph-filters";
import { useGraphNetwork } from "@/hooks/use-graph";
import type { GraphNodeData } from "@/components/graph/network-graph";

// Sigma.js requires WebGL — disable SSR
const NetworkGraph = dynamic(
  () => import("@/components/graph/network-graph").then((mod) => mod.NetworkGraph),
  { ssr: false }
);

export default function ExplorerPage() {
  const [filters, setFilters] = useState<GraphFilterValues>({});
  const [hoveredNode, setHoveredNode] = useState<GraphNodeData | null>(null);
  const [tooltipPosition, setTooltipPosition] = useState<{ x: number; y: number } | null>(null);

  const { data, isLoading, isError } = useGraphNetwork({
    year: filters.year,
    sector: filters.sector,
    min_connections: filters.min_connections,
    search: filters.search,
    limit: 500,
  });

  const handleApplyFilters = useCallback((values: GraphFilterValues) => {
    setFilters(values);
  }, []);

  const handleNodeHover = useCallback((node: GraphNodeData | null) => {
    setHoveredNode(node);
  }, []);

  const handleNodePosition = useCallback((position: { x: number; y: number } | null) => {
    setTooltipPosition(position);
  }, []);

  return (
    <>
      <Header title="Graph Explorer" />

      <div className="flex flex-col" style={{ height: "calc(100vh - 4rem)" }}>
        <GraphFilters onApply={handleApplyFilters} isLoading={isLoading} />

        <div className="flex-1 relative bg-[var(--color-bg)]">
          {isLoading && (
            <div className="absolute inset-0 z-30 flex items-center justify-center bg-[var(--color-bg)]/80">
              <div className="flex items-center gap-3 text-[var(--color-text-3)]">
                <Loader2 className="h-5 w-5 animate-spin text-[var(--color-accent)]" />
                <span className="text-sm font-medium">Carregando rede...</span>
              </div>
            </div>
          )}

          {isError && (
            <div className="absolute inset-0 z-30 flex items-center justify-center">
              <p className="text-sm text-[var(--color-danger)]">
                Erro ao carregar dados da rede. Verifique se a API esta disponivel.
              </p>
            </div>
          )}

          {data && (
            <>
              <NetworkGraph
                nodes={data.nodes}
                edges={data.edges ?? []}
                onNodeHover={handleNodeHover}
                onNodePosition={handleNodePosition}
              />

              {hoveredNode && tooltipPosition && (
                <GraphTooltip node={hoveredNode} position={tooltipPosition} />
              )}
            </>
          )}
        </div>
      </div>
    </>
  );
}
