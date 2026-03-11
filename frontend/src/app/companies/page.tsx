"use client";

import { useState } from "react";
import Link from "next/link";
import { Header } from "@/components/layout/header";
import { useMembers } from "@/hooks/use-members";
import { Search } from "lucide-react";

export default function CompaniesPage() {
  const [search, setSearch] = useState("");

  // We use the members endpoint to extract unique companies
  // In a production app this would be a dedicated /api/companies endpoint
  const { data, isLoading } = useMembers(search, 1, 100);

  // Extract unique companies from the members response
  const companies = data?.items
    ? Array.from(
        new Map(
          data.items.flatMap((item) =>
            item.companies.map((c) => [c.cd_cvm, c])
          )
        ).values()
      )
    : [];

  return (
    <>
      <Header title="Empresas" />
      <main className="p-6 space-y-6">
        <div className="relative max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[var(--color-text-3)]" />
          <input
            type="text"
            placeholder="Buscar empresa..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 text-sm bg-white border border-[var(--color-border)] text-[var(--color-text)] placeholder:text-[var(--color-text-3)] focus:outline-none focus:ring-1 focus:ring-[var(--color-accent)]/40 transition-colors"
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {isLoading
            ? Array.from({ length: 9 }).map((_, i) => (
                <div
                  key={i}
                  className="bg-[var(--color-surface)] border border-[var(--color-border)] p-5"
                >
                  <div className="h-5 w-40 bg-[var(--color-surface-alt)] animate-pulse" />
                  <div className="h-4 w-24 bg-[var(--color-surface-alt)] animate-pulse rounded mt-2" />
                </div>
              ))
            : companies.map((company) => (
                <Link
                  key={company.cd_cvm}
                  href={`/companies/${company.cd_cvm}`}
                  className="bg-[var(--color-surface)] border border-[var(--color-border)] p-5 hover:bg-[var(--color-surface-alt)] hover:border-[var(--color-border-strong)] transition-colors"
                >
                  <p className="text-sm font-medium text-[var(--color-text)]">
                    {company.nome}
                  </p>
                </Link>
              ))}
        </div>

        {!isLoading && companies.length === 0 && (
          <div className="text-center py-12">
            <p className="text-sm text-[var(--color-text-3)]">Nenhuma empresa encontrada</p>
          </div>
        )}
      </main>
    </>
  );
}
