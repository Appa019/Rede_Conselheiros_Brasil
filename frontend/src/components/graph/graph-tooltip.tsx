"use client";

import type { GraphNodeData } from "./network-graph";

interface GraphTooltipProps {
  node: GraphNodeData;
  position: { x: number; y: number };
}

// Floating tooltip displayed near hovered node
export function GraphTooltip({ node, position }: GraphTooltipProps) {
  return (
    <div
      className="absolute z-20 bg-white shadow-xl p-3 border border-[var(--color-border)] pointer-events-none min-w-[200px]"
      style={{
        left: position.x + 12,
        top: position.y - 10,
        transform: "translateY(-50%)",
      }}
    >
      <p className="text-sm font-medium text-[var(--color-text)] font-[family-name:var(--font-heading)] mb-1.5">
        {node.nome}
      </p>

      <div className="space-y-1 text-xs text-[var(--color-text-3)]">
        {node.page_rank !== undefined && (
          <div className="flex justify-between gap-4">
            <span>PageRank</span>
            <span className="font-[family-name:var(--font-mono)] font-medium text-[var(--color-accent)]">
              {node.page_rank.toFixed(6)}
            </span>
          </div>
        )}
        {node.community_id !== undefined && (
          <div className="flex justify-between gap-4">
            <span>Comunidade</span>
            <span className="font-[family-name:var(--font-mono)] font-medium text-[var(--color-text)]">
              {node.community_id}
            </span>
          </div>
        )}
        <div className="flex justify-between gap-4">
          <span>Conexoes</span>
          <span className="font-[family-name:var(--font-mono)] font-medium text-[var(--color-text)]">
            {node.connections}
          </span>
          </div>
      </div>

      <p className="text-[10px] text-[var(--color-text-3)] mt-2">
        Clique para ver perfil
      </p>
    </div>
  );
}
