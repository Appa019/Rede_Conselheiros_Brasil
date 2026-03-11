"use client";

import { useState } from "react";
import { Info } from "lucide-react";
import type { LucideIcon } from "lucide-react";

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  tooltip?: string;
  icon: LucideIcon;
  index?: number;
  accentColor?: "green" | "gold";
}

export function MetricCardSkeleton() {
  return (
    <div className="bg-[var(--color-surface)] border border-[var(--color-border)] p-5">
      <div className="space-y-3">
        <div className="h-3 w-20 animate-pulse bg-[var(--color-surface-alt)]" />
        <div className="h-7 w-16 animate-pulse bg-[var(--color-surface-alt)]" />
        <div className="h-3 w-28 animate-pulse bg-[var(--color-surface-alt)]" />
      </div>
    </div>
  );
}

export function MetricCard({ title, value, subtitle, tooltip, icon: Icon }: MetricCardProps) {
  const [showTooltip, setShowTooltip] = useState(false);

  return (
    <div className="bg-[var(--color-surface)] border border-[var(--color-border)] p-5 hover:bg-[var(--color-surface-alt)] transition-colors">
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-1.5">
            <p className="text-sm text-[var(--color-text-2)]">{title}</p>
            {tooltip && (
              <div className="relative">
                <button
                  type="button"
                  onMouseEnter={() => setShowTooltip(true)}
                  onMouseLeave={() => setShowTooltip(false)}
                  onClick={() => setShowTooltip((v) => !v)}
                  className="text-[var(--color-text-3)] hover:text-[var(--color-text-2)] transition-colors"
                  aria-label={`Info: ${title}`}
                >
                  <Info className="h-3 w-3" />
                </button>
                {showTooltip && (
                  <div className="absolute z-10 left-1/2 -translate-x-1/2 top-full mt-1.5 w-52 p-2 bg-[var(--color-text)] text-[var(--color-surface)] text-xs leading-relaxed shadow-lg">
                    {tooltip}
                  </div>
                )}
              </div>
            )}
          </div>
          <p className="mt-2 text-2xl font-semibold font-[family-name:var(--font-mono)] text-[var(--color-text)]">
            {typeof value === "number" ? value.toLocaleString("pt-BR") : value}
          </p>
          {subtitle && (
            <p className="mt-1 text-xs text-[var(--color-text-3)]">{subtitle}</p>
          )}
        </div>
        <Icon className="h-4 w-4 text-[var(--color-text-2)]" />
      </div>
    </div>
  );
}
