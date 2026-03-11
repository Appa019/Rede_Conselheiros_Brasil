"use client";

import { useState, useMemo } from "react";

interface DataPoint {
  year: number;
  value: number;
  label?: string;
}

interface TimelineChartProps {
  data: DataPoint[];
  title: string;
  color?: string;
}

const CHART_WIDTH = 600;
const CHART_HEIGHT = 280;
const PADDING = { top: 24, right: 32, bottom: 40, left: 56 };

export function TimelineChart({
  data,
  title,
  color = "#1B5E4B",
}: TimelineChartProps) {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

  const { points, xLabels, yLabels, gridLines, linePath } = useMemo(() => {
    if (data.length === 0) {
      return { points: [], xLabels: [], yLabels: [], gridLines: [], linePath: "" };
    }

    const innerW = CHART_WIDTH - PADDING.left - PADDING.right;
    const innerH = CHART_HEIGHT - PADDING.top - PADDING.bottom;

    const minY = 0;
    const maxY = Math.max(...data.map((d) => d.value)) * 1.1 || 1;
    const minX = Math.min(...data.map((d) => d.year));
    const maxX = Math.max(...data.map((d) => d.year));
    const xRange = maxX - minX || 1;

    // Compute point positions
    const pts = data.map((d, i) => ({
      x: PADDING.left + (innerW * (d.year - minX)) / xRange,
      y: PADDING.top + innerH - (innerH * (d.value - minY)) / (maxY - minY),
      data: d,
      index: i,
    }));

    // Build SVG path
    const path = pts
      .map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`)
      .join(" ");

    // Y-axis grid lines (5 lines)
    const numGridLines = 5;
    const grids = Array.from({ length: numGridLines + 1 }, (_, i) => {
      const val = minY + ((maxY - minY) * i) / numGridLines;
      const y = PADDING.top + innerH - (innerH * (val - minY)) / (maxY - minY);
      return { y, label: formatNumber(val) };
    });

    // X-axis labels
    const xLbls = data.map((d) => ({
      x: PADDING.left + (innerW * (d.year - minX)) / xRange,
      label: String(d.year),
    }));

    return { points: pts, xLabels: xLbls, yLabels: grids, gridLines: grids, linePath: path };
  }, [data]);

  return (
    <div className="bg-[var(--color-surface)] border border-[var(--color-border)] p-5">
      <h3 className="text-base font-semibold font-[family-name:var(--font-heading)] text-[var(--color-text)] mb-4">
        {title}
      </h3>

      {data.length === 0 ? (
        <div className="flex items-center justify-center h-48 text-sm text-[var(--color-text-3)]">
          Sem dados disponiveis
        </div>
      ) : (
        <svg
          viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`}
          className="w-full h-auto"
          onMouseLeave={() => setHoveredIndex(null)}
        >
          {/* Grid lines */}
          {gridLines.map((line, i) => (
            <g key={`grid-${i}`}>
              <line
                x1={PADDING.left}
                y1={line.y}
                x2={CHART_WIDTH - PADDING.right}
                y2={line.y}
                stroke="#e5e7eb"
                strokeWidth={1}
              />
              <text
                x={PADDING.left - 8}
                y={line.y + 4}
                textAnchor="end"
                fill="#9ca3af"
                className="text-[11px]"
              >
                {line.label}
              </text>
            </g>
          ))}

          {/* X-axis labels */}
          {xLabels.map((lbl, i) => (
            <text
              key={`x-${i}`}
              x={lbl.x}
              y={CHART_HEIGHT - 8}
              textAnchor="middle"
              fill="#9ca3af"
              className="text-[11px]"
            >
              {lbl.label}
            </text>
          ))}

          {/* Line path */}
          <path
            d={linePath}
            fill="none"
            stroke={color}
            strokeWidth={2}
            strokeLinejoin="round"
            strokeLinecap="round"
          />

          {/* Data points */}
          {points.map((p) => (
            <g key={`pt-${p.index}`}>
              {/* Invisible hit area */}
              <circle
                cx={p.x}
                cy={p.y}
                r={12}
                fill="transparent"
                onMouseEnter={() => setHoveredIndex(p.index)}
              />
              {/* Visible dot */}
              <circle
                cx={p.x}
                cy={p.y}
                r={hoveredIndex === p.index ? 5 : 3.5}
                fill={color}
                stroke="#ffffff"
                strokeWidth={2}
                className="transition-all duration-150"
              />
            </g>
          ))}

          {/* Tooltip */}
          {hoveredIndex !== null && points[hoveredIndex] && (
            <g>
              <rect
                x={points[hoveredIndex].x - 40}
                y={points[hoveredIndex].y - 36}
                width={80}
                height={24}
                rx={0}
                fill="#ffffff"
                stroke="#e5e7eb"
                strokeWidth={1}
              />
              <text
                x={points[hoveredIndex].x}
                y={points[hoveredIndex].y - 20}
                textAnchor="middle"
                fill="#111827"
                className="text-[11px] font-medium"
              >
                {points[hoveredIndex].data.label ||
                  `${points[hoveredIndex].data.year}: ${formatNumber(points[hoveredIndex].data.value)}`}
              </text>
            </g>
          )}
        </svg>
      )}
    </div>
  );
}

// Skeleton placeholder for loading state
export function TimelineChartSkeleton() {
  return (
    <div className="bg-[var(--color-surface)] border border-[var(--color-border)] p-5">
      <div className="h-5 w-40 animate-pulse bg-[var(--color-surface-alt)] mb-4" />
      <div className="h-48 animate-pulse bg-[var(--color-surface-alt)]" />
    </div>
  );
}

function formatNumber(value: number): string {
  if (value >= 1000) {
    return `${(value / 1000).toFixed(1)}k`;
  }
  return Math.round(value).toLocaleString("pt-BR");
}
