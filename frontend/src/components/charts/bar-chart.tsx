"use client";

interface BarDataPoint {
  label: string;
  value: number;
}

interface BarChartProps {
  data: BarDataPoint[];
  title: string;
  color?: string;
}

const CHART_WIDTH = 600;
const BAR_HEIGHT = 28;
const BAR_GAP = 8;
const PADDING = { top: 8, right: 64, bottom: 8, left: 140 };

export function BarChart({ data, title, color = "#1B5E4B" }: BarChartProps) {
  const maxValue = Math.max(...data.map((d) => d.value), 1);
  const innerW = CHART_WIDTH - PADDING.left - PADDING.right;
  const chartHeight =
    PADDING.top + data.length * (BAR_HEIGHT + BAR_GAP) - BAR_GAP + PADDING.bottom;

  return (
    <div className="bg-[var(--color-surface)] border border-[var(--color-border)] p-5">
      <h3 className="text-base font-semibold font-[family-name:var(--font-heading)] text-[var(--color-text)] mb-4">
        {title}
      </h3>

      {data.length === 0 ? (
        <div className="flex items-center justify-center h-32 text-sm text-[var(--color-text-3)]">
          Sem dados disponiveis
        </div>
      ) : (
        <svg
          viewBox={`0 0 ${CHART_WIDTH} ${chartHeight}`}
          className="w-full h-auto"
        >
          {data.map((d, i) => {
            const y = PADDING.top + i * (BAR_HEIGHT + BAR_GAP);
            const barW = (d.value / maxValue) * innerW;

            return (
              <g key={`bar-${i}`}>
                {/* Label */}
                <text
                  x={PADDING.left - 8}
                  y={y + BAR_HEIGHT / 2 + 4}
                  textAnchor="end"
                  fill="#8b8b8f"
                  className="text-[12px]"
                >
                  {truncateLabel(d.label, 20)}
                </text>

                {/* Background track */}
                <rect
                  x={PADDING.left}
                  y={y}
                  width={innerW}
                  height={BAR_HEIGHT}
                  rx={0}
                  fill="#f0f1f3"
                />

                {/* Bar fill */}
                <rect
                  x={PADDING.left}
                  y={y}
                  width={Math.max(barW, 2)}
                  height={BAR_HEIGHT}
                  rx={0}
                  fill={color}
                  opacity={0.8}
                />

                {/* Value label */}
                <text
                  x={PADDING.left + innerW + 8}
                  y={y + BAR_HEIGHT / 2 + 4}
                  textAnchor="start"
                  fill="#8b8b8f"
                  className="text-[12px] font-medium"
                >
                  {d.value.toLocaleString("pt-BR")}
                </text>
              </g>
            );
          })}
        </svg>
      )}
    </div>
  );
}

// Skeleton placeholder for loading state
export function BarChartSkeleton() {
  return (
    <div className="bg-[var(--color-surface)] border border-[var(--color-border)] p-5">
      <div className="h-5 w-40 animate-pulse bg-[var(--color-surface-alt)] mb-4" />
      <div className="space-y-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <div
            key={i}
            className="h-7 animate-pulse bg-[var(--color-surface-alt)]"
          />
        ))}
      </div>
    </div>
  );
}

function truncateLabel(label: string, maxLen: number): string {
  if (label.length <= maxLen) return label;
  return label.slice(0, maxLen - 1) + "\u2026";
}
