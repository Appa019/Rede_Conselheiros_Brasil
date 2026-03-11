"use client";

import { use } from "react";
import Link from "next/link";
import { Header } from "@/components/layout/header";
import { useCompanyBoard, useCompanyNetwork } from "@/hooks/use-companies";
import { ArrowLeft, Building2, Network } from "lucide-react";

export default function CompanyProfilePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);

  return <CompanyProfileContent cdCvm={id} />;
}

function CompanyProfileContent({ cdCvm }: { cdCvm: string }) {
  const { data: boardData, isLoading: boardLoading } = useCompanyBoard(cdCvm);
  const { data: networkData, isLoading: networkLoading } =
    useCompanyNetwork(cdCvm);

  return (
    <>
      <Header title="Perfil da Empresa" />
      <main className="p-6 space-y-6">
        <Link
          href="/companies"
          className="inline-flex items-center gap-1.5 text-sm text-[var(--color-text-3)] hover:text-[var(--color-text)] transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Voltar para empresas
        </Link>

        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] p-6">
          {boardLoading ? (
            <div className="space-y-2">
              <div className="h-7 w-64 bg-[var(--color-surface-alt)] animate-pulse" />
              <div className="h-4 w-40 bg-[var(--color-surface-alt)] animate-pulse" />
            </div>
          ) : boardData?.company ? (
            <div>
              <h2 className="text-2xl font-semibold font-[family-name:var(--font-heading)] text-[var(--color-text)]">
                {boardData.company.nome}
              </h2>
              <div className="flex items-center gap-3 mt-2">
                {boardData.company.setor && (
                  <span className="text-xs px-2 py-0.5 bg-[var(--color-accent-dim)] text-[var(--color-accent)]">
                    {boardData.company.setor}
                  </span>
                )}
                {boardData.company.segmento_listagem && (
                  <span className="text-xs px-2 py-0.5 bg-[var(--color-warm-dim)] text-[var(--color-warm)]">
                    {boardData.company.segmento_listagem}
                  </span>
                )}
              </div>
            </div>
          ) : null}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-[var(--color-surface)] border border-[var(--color-border)]">
            <div className="p-5 border-b border-[var(--color-border)]">
              <h3 className="text-sm font-medium text-[var(--color-text-2)] flex items-center gap-2">
                <Building2 className="h-4 w-4" />
                Composicao do Conselho
              </h3>
            </div>
            <div className="divide-y divide-[var(--color-border)]">
              {boardLoading
                ? Array.from({ length: 5 }).map((_, i) => (
                    <div key={i} className="px-5 py-3">
                      <div className="h-4 w-36 bg-[var(--color-surface-alt)] animate-pulse" />
                      <div className="h-3 w-24 bg-[var(--color-surface-alt)] animate-pulse rounded mt-1" />
                    </div>
                  ))
                : boardData?.board_members.map((m) => (
                    <Link
                      key={m.id}
                      href={`/members/${m.id}`}
                      className="flex items-center justify-between px-5 py-3 hover:bg-[var(--color-surface-alt)] transition-colors"
                    >
                      <div>
                        <p className="text-sm font-medium text-[var(--color-text)]">
                          {m.nome}
                        </p>
                        <p className="text-xs text-[var(--color-text-3)] mt-0.5">
                          {m.cargo}
                        </p>
                      </div>
                      {m.page_rank != null && (
                        <span className="text-xs text-[var(--color-text-3)]">
                          PR: {m.page_rank.toFixed(4)}
                        </span>
                      )}
                    </Link>
                  ))}
              {!boardLoading && boardData?.board_members.length === 0 && (
                <p className="px-5 py-4 text-sm text-[var(--color-text-3)]">
                  Nenhum membro encontrado
                </p>
              )}
            </div>
          </div>

          <div className="bg-[var(--color-surface)] border border-[var(--color-border)]">
            <div className="p-5 border-b border-[var(--color-border)]">
              <h3 className="text-sm font-medium text-[var(--color-text-2)] flex items-center gap-2">
                <Network className="h-4 w-4" />
                Empresas Interligadas
              </h3>
            </div>
            <div className="divide-y divide-[var(--color-border)]">
              {networkLoading
                ? Array.from({ length: 5 }).map((_, i) => (
                    <div key={i} className="px-5 py-3">
                      <div className="h-4 w-40 bg-[var(--color-surface-alt)] animate-pulse" />
                      <div className="h-3 w-28 bg-[var(--color-surface-alt)] animate-pulse rounded mt-1" />
                    </div>
                  ))
                : networkData?.map((item) => (
                    <Link
                      key={item.company.cd_cvm}
                      href={`/companies/${item.company.cd_cvm}`}
                      className="block px-5 py-3 hover:bg-[var(--color-surface-alt)] transition-colors"
                    >
                      <div className="flex items-center justify-between">
                        <p className="text-sm font-medium text-[var(--color-text)]">
                          {item.company.nome}
                        </p>
                        <span className="text-xs px-2 py-0.5 bg-[var(--color-surface-alt)] text-[var(--color-text-2)]">
                          {item.shared_count}{" "}
                          {item.shared_count === 1 ? "membro" : "membros"} em
                          comum
                        </span>
                      </div>
                      <p className="text-xs text-[var(--color-text-3)] mt-0.5 truncate">
                        {item.shared_members.join(", ")}
                      </p>
                    </Link>
                  ))}
              {!networkLoading && networkData?.length === 0 && (
                <p className="px-5 py-4 text-sm text-[var(--color-text-3)]">
                  Nenhuma empresa interligada encontrada
                </p>
              )}
            </div>
          </div>
        </div>
      </main>
    </>
  );
}
