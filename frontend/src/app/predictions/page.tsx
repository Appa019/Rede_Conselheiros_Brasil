"use client";

import { useState } from "react";
import { Search, ArrowRight } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { Header } from "@/components/layout/header";
import { apiFetch } from "@/lib/api";

interface PredictedLink {
  source: string;
  target: string;
  probability: number;
}

interface SimilarMember {
  id: string;
  nome: string;
  score: number;
  companies: string;
}

export default function PredictionsPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedMemberId, setSelectedMemberId] = useState<string | null>(null);

  // Predicted links query
  const {
    data: predictions,
    isLoading: predictionsLoading,
    error: predictionsError,
  } = useQuery<PredictedLink[]>({
    queryKey: ["predictions", "links"],
    queryFn: () => apiFetch<PredictedLink[]>("/predictions/links?top_k=20"),
  });

  // Similar members query (only when a member is selected)
  const {
    data: similarMembers,
    isLoading: similarLoading,
    error: similarError,
  } = useQuery<SimilarMember[]>({
    queryKey: ["predictions", "similar", selectedMemberId],
    queryFn: () =>
      apiFetch<SimilarMember[]>(`/predictions/similar/${selectedMemberId}?top_k=10`),
    enabled: !!selectedMemberId,
  });

  return (
    <>
      <Header title="Predicoes" />
      <main className="p-6 space-y-8">
        <section>
          <h2 className="text-base font-semibold font-[family-name:var(--font-heading)] text-[var(--color-text)] mb-1">
            Conexoes Previstas
          </h2>
          <p className="text-sm text-[var(--color-text-2)] mb-4">
            Conexoes com maior probabilidade de se formarem, baseadas em predicao de links
          </p>

          {predictionsError && (
            <div className="bg-[var(--color-danger)]/10 border border-[var(--color-danger)]/20 p-4 text-sm text-[var(--color-danger)] mb-4">
              Erro ao carregar predicoes. Verifique se o modelo foi treinado.
            </div>
          )}

          <div className="bg-[var(--color-surface)] border border-[var(--color-border)] overflow-hidden">
            {predictionsLoading ? (
              <div className="p-6 space-y-3">
                {Array.from({ length: 5 }).map((_, i) => (
                  <div key={i} className="flex items-center gap-4">
                    <div className="h-4 w-32 bg-[var(--color-surface-alt)] animate-pulse" />
                    <div className="h-4 w-8 bg-[var(--color-surface-alt)] animate-pulse" />
                    <div className="h-4 w-32 bg-[var(--color-surface-alt)] animate-pulse" />
                    <div className="h-4 w-16 bg-[var(--color-surface-alt)] animate-pulse rounded ml-auto" />
                  </div>
                ))}
              </div>
            ) : predictions && predictions.length > 0 ? (
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-[var(--color-border)]">
                    <th className="text-left text-xs font-medium text-[var(--color-text-3)] py-2.5 px-5">
                      Origem
                    </th>
                    <th className="py-2.5 px-2 text-[var(--color-text-3)]" />
                    <th className="text-left text-xs font-medium text-[var(--color-text-3)] py-2.5 px-5">
                      Destino
                    </th>
                    <th className="text-right text-xs font-medium text-[var(--color-text-3)] py-2.5 px-5">
                      Probabilidade
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {predictions.map((pred) => (
                    <tr
                      key={`${pred.source}-${pred.target}`}
                      className="border-b border-[var(--color-border)] hover:bg-[var(--color-surface-alt)] transition-colors"
                    >
                      <td className="py-3 px-5 text-[var(--color-text)]">{pred.source}</td>
                      <td className="py-3 px-2">
                        <ArrowRight className="h-3.5 w-3.5 text-[var(--color-text-3)]" />
                      </td>
                      <td className="py-3 px-5 text-[var(--color-text)]">{pred.target}</td>
                      <td className="py-3 px-5 text-right">
                        <span
                          className={`inline-block px-2 py-0.5 text-xs font-medium ${
                            pred.probability >= 0.8
                              ? "bg-[var(--color-warm-dim)] text-[var(--color-warm)]"
                              : pred.probability >= 0.5
                                ? "bg-[var(--color-accent-dim)] text-[var(--color-accent)]"
                                : "bg-[var(--color-surface-alt)] text-[var(--color-text-3)]"
                          }`}
                        >
                          {(pred.probability * 100).toFixed(1)}%
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="p-8 text-center text-sm text-[var(--color-text-3)]">
                Nenhuma predicao disponivel. Treine o modelo primeiro.
              </div>
            )}
          </div>
        </section>

        <section>
          <h2 className="text-base font-semibold font-[family-name:var(--font-heading)] text-[var(--color-text)] mb-1">
            Membros Similares
          </h2>
          <p className="text-sm text-[var(--color-text-2)] mb-4">
            Busque um membro para encontrar conselheiros com perfil de rede similar
          </p>

          <div className="relative max-w-md mb-6">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[var(--color-text-3)]" />
            <input
              type="text"
              placeholder="ID ou nome do membro..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && searchQuery.trim()) {
                  setSelectedMemberId(searchQuery.trim());
                }
              }}
              className="w-full pl-10 pr-4 py-2.5 text-sm bg-white border border-[var(--color-border)] text-[var(--color-text)] placeholder:text-[var(--color-text-3)] focus:outline-none focus:ring-1 focus:ring-[var(--color-accent)]/40 transition-colors"
            />
          </div>

          {similarError && (
            <div className="bg-[var(--color-danger)]/10 border border-[var(--color-danger)]/20 p-4 text-sm text-[var(--color-danger)] mb-4">
              Erro ao buscar membros similares. Verifique se o modelo foi treinado e o ID e valido.
            </div>
          )}

          <div className="bg-[var(--color-surface)] border border-[var(--color-border)]">
            {similarLoading ? (
              <div className="p-6 space-y-3">
                {Array.from({ length: 4 }).map((_, i) => (
                  <div key={i} className="flex items-center gap-4">
                    <div className="h-4 w-40 bg-[var(--color-surface-alt)] animate-pulse" />
                    <div className="h-4 w-24 bg-[var(--color-surface-alt)] animate-pulse rounded ml-auto" />
                  </div>
                ))}
              </div>
            ) : similarMembers && similarMembers.length > 0 ? (
              <ul className="divide-y divide-[var(--color-border)]">
                {similarMembers.map((member) => (
                  <li
                    key={member.id}
                    className="flex items-center justify-between px-5 py-3 hover:bg-[var(--color-surface-alt)] transition-colors"
                  >
                    <div>
                      <p className="text-sm font-medium text-[var(--color-text)]">
                        {member.nome}
                      </p>
                      {member.companies && (
                        <p className="text-xs text-[var(--color-text-3)] mt-0.5">
                          {member.companies}
                        </p>
                      )}
                    </div>
                    <span className="text-xs font-medium bg-[var(--color-surface-alt)] text-[var(--color-text-2)] px-2 py-0.5">
                      {(member.score * 100).toFixed(1)}% similar
                    </span>
                  </li>
                ))}
              </ul>
            ) : selectedMemberId ? (
              <div className="p-8 text-center text-sm text-[var(--color-text-3)]">
                Nenhum membro similar encontrado para este ID.
              </div>
            ) : (
              <div className="p-8 text-center text-sm text-[var(--color-text-3)]">
                Insira um ID de membro e pressione Enter para buscar.
              </div>
            )}
          </div>
        </section>
      </main>
    </>
  );
}
