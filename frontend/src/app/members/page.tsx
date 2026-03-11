"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Header } from "@/components/layout/header";
import { useMembers } from "@/hooks/use-members";
import { Search, ChevronLeft, ChevronRight } from "lucide-react";

export default function MembersPage() {
  const router = useRouter();
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const pageSize = 20;

  const { data, isLoading } = useMembers(search, page, pageSize);

  // Reset page when search changes
  const handleSearch = (value: string) => {
    setSearch(value);
    setPage(1);
  };

  return (
    <>
      <Header title="Membros" />
      <main className="p-6 space-y-6">
        <div className="relative max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[var(--color-text-3)]" />
          <input
            type="text"
            placeholder="Buscar por nome..."
            value={search}
            onChange={(e) => handleSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 text-sm bg-white border border-[var(--color-border)] text-[var(--color-text)] placeholder:text-[var(--color-text-3)] focus:outline-none focus:ring-1 focus:ring-[var(--color-accent)]/40 transition-colors"
          />
        </div>

        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-[var(--color-border)]">
                <th className="text-left text-xs font-medium text-[var(--color-text-3)] py-2.5 px-5">
                  Nome
                </th>
                <th className="text-left text-xs font-medium text-[var(--color-text-3)] py-2.5 px-5">
                  Cargo
                </th>
                <th className="text-right text-xs font-medium text-[var(--color-text-3)] py-2.5 px-5">
                  PageRank
                </th>
                <th className="text-right text-xs font-medium text-[var(--color-text-3)] py-2.5 px-5">
                  Betweenness
                </th>
                <th className="text-right text-xs font-medium text-[var(--color-text-3)] py-2.5 px-5">
                  Comunidade
                </th>
              </tr>
            </thead>
            <tbody>
              {isLoading
                ? Array.from({ length: 10 }).map((_, i) => (
                    <tr key={i} className="border-b border-[var(--color-border)]">
                      <td className="py-3 px-5">
                        <div className="h-4 w-40 bg-[var(--color-surface-alt)] animate-pulse" />
                      </td>
                      <td className="py-3 px-5">
                        <div className="h-4 w-28 bg-[var(--color-surface-alt)] animate-pulse" />
                      </td>
                      <td className="py-3 px-5">
                        <div className="h-4 w-16 bg-[var(--color-surface-alt)] animate-pulse rounded ml-auto" />
                      </td>
                      <td className="py-3 px-5">
                        <div className="h-4 w-16 bg-[var(--color-surface-alt)] animate-pulse rounded ml-auto" />
                      </td>
                      <td className="py-3 px-5">
                        <div className="h-4 w-10 bg-[var(--color-surface-alt)] animate-pulse rounded ml-auto" />
                      </td>
                    </tr>
                  ))
                : data?.items.map((item) => (
                      <tr
                        key={item.member.id}
                        onClick={() => router.push(`/members/${item.member.id}`)}
                        className="hover:bg-[var(--color-surface-alt)] cursor-pointer transition-colors border-b border-[var(--color-border)]"
                      >
                        <td className="py-3 px-5 text-sm font-medium text-[var(--color-text)]">
                          {item.member.nome}
                        </td>
                        <td className="py-3 px-5 text-sm text-[var(--color-text-3)]">
                          {item.companies[0]?.cargo ?? "-"}
                        </td>
                        <td className="py-3 px-5 text-sm text-[var(--color-text-2)] text-right">
                          {item.member.page_rank?.toFixed(4) ?? "-"}
                        </td>
                        <td className="py-3 px-5 text-sm text-[var(--color-text-2)] text-right">
                          {item.member.betweenness?.toFixed(4) ?? "-"}
                        </td>
                        <td className="py-3 px-5 text-sm text-[var(--color-text-2)] text-right">
                          {item.member.community_id ?? "-"}
                        </td>
                      </tr>
                  ))}
            </tbody>
          </table>
        </div>

        {data && data.total_pages > 1 && (
          <div className="flex items-center justify-between">
            <p className="text-sm text-[var(--color-text-3)]">
              {data.total} resultados - pagina {data.page} de {data.total_pages}
            </p>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1}
                className="p-2 bg-[var(--color-surface)] hover:bg-[var(--color-surface-alt)] border border-[var(--color-border)] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronLeft className="h-4 w-4 text-[var(--color-text-2)]" />
              </button>
              <button
                onClick={() => setPage((p) => Math.min(data.total_pages, p + 1))}
                disabled={page >= data.total_pages}
                className="p-2 bg-[var(--color-surface)] hover:bg-[var(--color-surface-alt)] border border-[var(--color-border)] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronRight className="h-4 w-4 text-[var(--color-text-2)]" />
              </button>
            </div>
          </div>
        )}
      </main>
    </>
  );
}
