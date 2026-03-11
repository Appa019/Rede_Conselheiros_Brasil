"use client";

import { use } from "react";
import Link from "next/link";
import { Header } from "@/components/layout/header";
import { MetricCard, MetricCardSkeleton } from "@/components/dashboard/metric-card";
import { useMember } from "@/hooks/use-members";
import {
  TrendingUp,
  GitFork,
  Circle,
  Target,
  Waypoints,
  Layers,
  Building2,
  ArrowLeft,
  Users,
} from "lucide-react";

export default function MemberProfilePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);

  return <MemberProfileContent id={id} />;
}

function MemberProfileContent({ id }: { id: string }) {
  const { data, isLoading } = useMember(id);

  const member = data?.member;

  return (
    <>
      <Header title="Perfil do Membro" />
      <main className="p-6 space-y-6">
        <Link
          href="/members"
          className="inline-flex items-center gap-1.5 text-sm text-[var(--color-text-3)] hover:text-[var(--color-text)] transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Voltar para membros
        </Link>

        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] p-6">
          {isLoading ? (
            <div className="space-y-2">
              <div className="h-7 w-64 bg-[var(--color-surface-alt)] animate-pulse" />
              <div className="h-4 w-40 bg-[var(--color-surface-alt)] animate-pulse" />
            </div>
          ) : (
            <div>
              <h2 className="text-2xl font-semibold font-[family-name:var(--font-heading)] text-[var(--color-text)]">
                {member?.nome}
              </h2>
              {member?.formacao && (
                <p className="text-sm text-[var(--color-text-2)] mt-1">{member.formacao}</p>
              )}
              {member?.community_id != null && (
                <span className="inline-block mt-2 text-xs px-2 py-0.5 bg-[var(--color-accent-dim)] text-[var(--color-accent)]">
                  Comunidade {member.community_id}
                </span>
              )}
            </div>
          )}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              {isLoading ? (
                Array.from({ length: 6 }).map((_, i) => (
                  <MetricCardSkeleton key={i} />
                ))
              ) : (
                <>
                  <MetricCard
                    title="PageRank"
                    value={member?.page_rank?.toFixed(4) ?? "-"}
                    tooltip="Importancia relativa na rede. Valores altos = conexao com membros influentes."
                    icon={TrendingUp}
                  />
                  <MetricCard
                    title="Betweenness"
                    value={member?.betweenness?.toFixed(4) ?? "-"}
                    tooltip="Frequencia nos caminhos mais curtos. Alto = ponte entre grupos."
                    icon={GitFork}
                  />
                  <MetricCard
                    title="Degree Centrality"
                    value={member?.degree_centrality?.toFixed(4) ?? "-"}
                    tooltip="Proporcao de membros conectados diretamente."
                    icon={Circle}
                  />
                  <MetricCard
                    title="Eigenvector"
                    value={member?.eigenvector?.toFixed(4) ?? "-"}
                    tooltip="Influencia baseada em quao conectados sao seus vizinhos."
                    icon={Target}
                  />
                  <MetricCard
                    title="Closeness"
                    value={member?.closeness?.toFixed(4) ?? "-"}
                    tooltip="Proximidade media a todos os membros da rede."
                    icon={Waypoints}
                  />
                  <MetricCard
                    title="K-Core"
                    value={member?.k_core ?? "-"}
                    tooltip="Pertence ao subgrupo onde todos tem pelo menos N conexoes."
                    icon={Layers}
                  />
                </>
              )}
            </div>
          </div>

          <div className="space-y-6">
            <div className="bg-[var(--color-surface)] border border-[var(--color-border)]">
              <div className="p-5 border-b border-[var(--color-border)]">
                <h3 className="text-sm font-medium text-[var(--color-text-2)] flex items-center gap-2">
                  <Building2 className="h-4 w-4" />
                  Empresas
                </h3>
              </div>
              <div className="divide-y divide-[var(--color-border)]">
                {isLoading
                  ? Array.from({ length: 3 }).map((_, i) => (
                      <div key={i} className="px-5 py-3">
                        <div className="h-4 w-36 bg-[var(--color-surface-alt)] animate-pulse" />
                        <div className="h-3 w-24 bg-[var(--color-surface-alt)] animate-pulse rounded mt-1" />
                      </div>
                    ))
                  : data?.companies.map((c, i) => (
                      <Link
                        key={`${c.cd_cvm}-${c.ano_referencia}-${i}`}
                        href={`/companies/${c.cd_cvm}`}
                        className="block px-5 py-3 hover:bg-[var(--color-surface-alt)] transition-colors"
                      >
                        <p className="text-sm font-medium text-[var(--color-text)]">
                          {c.nome}
                        </p>
                        <p className="text-xs text-[var(--color-text-3)] mt-0.5">
                          {c.cargo}
                        </p>
                      </Link>
                    ))}
                {!isLoading && data?.companies.length === 0 && (
                  <p className="px-5 py-4 text-sm text-[var(--color-text-3)]">
                    Nenhuma empresa encontrada
                  </p>
                )}
              </div>
            </div>

            <div className="bg-[var(--color-surface)] border border-[var(--color-border)]">
              <div className="p-5 border-b border-[var(--color-border)]">
                <h3 className="text-sm font-medium text-[var(--color-text-2)] flex items-center gap-2">
                  <Users className="h-4 w-4" />
                  Conexoes
                </h3>
              </div>
              <div className="divide-y divide-[var(--color-border)] max-h-80 overflow-y-auto">
                {isLoading
                  ? Array.from({ length: 5 }).map((_, i) => (
                      <div key={i} className="px-5 py-3">
                        <div className="h-4 w-32 bg-[var(--color-surface-alt)] animate-pulse" />
                      </div>
                    ))
                  : data?.connections.map((conn) => (
                      <Link
                        key={conn.id}
                        href={`/members/${conn.id}`}
                        className="flex items-center justify-between px-5 py-3 hover:bg-[var(--color-surface-alt)] transition-colors"
                      >
                        <span className="text-sm text-[var(--color-text)] truncate">
                          {conn.nome}
                        </span>
                        {conn.page_rank != null && (
                          <span className="text-xs text-[var(--color-text-3)] ml-2">
                            {conn.page_rank.toFixed(4)}
                          </span>
                        )}
                      </Link>
                    ))}
                {!isLoading && data?.connections.length === 0 && (
                  <p className="px-5 py-4 text-sm text-[var(--color-text-3)]">
                    Nenhuma conexao encontrada
                  </p>
                )}
              </div>
            </div>
          </div>
        </div>
      </main>
    </>
  );
}
