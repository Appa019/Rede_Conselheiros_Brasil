"use client";

import Link from "next/link";
import { useTopMembers } from "@/hooks/use-metrics";

function TopConnectedSkeleton() {
  return (
    <div className="bg-[var(--color-surface)] border border-[var(--color-border)]">
      <div className="p-5">
        <div className="h-4 w-32 animate-pulse bg-[var(--color-surface-alt)]" />
        <div className="h-3 w-40 animate-pulse bg-[var(--color-surface-alt)] mt-2" />
      </div>
      <div className="px-5 pb-5 space-y-1">
        {Array.from({ length: 10 }).map((_, i) => (
          <div key={i} className="flex items-center gap-3 py-2.5 px-3">
            <div className="h-3 w-5 animate-pulse bg-[var(--color-surface-alt)]" />
            <div className="h-3 w-36 animate-pulse bg-[var(--color-surface-alt)] flex-1" />
            <div className="h-3 w-14 animate-pulse bg-[var(--color-surface-alt)]" />
            <div className="h-1 w-20 animate-pulse bg-[var(--color-surface-alt)] rounded-full" />
          </div>
        ))}
      </div>
    </div>
  );
}

export function TopConnected() {
  const { data: members, isLoading } = useTopMembers("page_rank", 10);

  if (isLoading) return <TopConnectedSkeleton />;

  const maxPR = members?.reduce(
    (max, m) => Math.max(max, m.page_rank ?? 0),
    0
  ) ?? 1;

  return (
    <div className="bg-[var(--color-surface)] border border-[var(--color-border)]">
      <div className="p-5">
        <h2 className="text-base font-semibold font-[family-name:var(--font-heading)] text-[var(--color-text)]">
          Top conectados
        </h2>
        <p className="text-xs text-[var(--color-text-3)] mt-1">Ranking por PageRank</p>
      </div>

      <div className="px-5 pb-5 space-y-1">
        {members?.map((member, i) => {
          const pr = member.page_rank ?? 0;
          const barWidth = maxPR > 0 ? (pr / maxPR) * 100 : 0;
          const rank = String(i + 1).padStart(2, "0");

          return (
            <Link
              key={member.id}
              href={`/members/${member.id}`}
              className="flex items-center gap-3 py-2.5 px-3 hover:bg-[var(--color-surface-alt)] transition-colors"
            >
              <span className="text-xs font-[family-name:var(--font-mono)] text-[var(--color-text-3)] w-5 text-right">
                {rank}
              </span>

              <span className="text-sm font-medium text-[var(--color-text)] flex-1 truncate">
                {member.nome}
              </span>

              <span className="text-xs font-[family-name:var(--font-mono)] text-[var(--color-text-2)] w-14 text-right">
                {pr.toFixed(4)}
              </span>

              <div className="w-20 h-1 bg-[var(--color-surface-alt)] rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full bg-[var(--color-accent)]"
                  style={{
                    width: `${barWidth}%`,
                    opacity: 0.5 + (barWidth / 200),
                  }}
                />
              </div>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
