"use client";

import { Header } from "@/components/layout/header";
import { TimelineChart, TimelineChartSkeleton } from "@/components/charts/timeline-chart";
import { useTemporalEvolution } from "@/hooks/use-temporal";

export default function TemporalPage() {
  const { data, isLoading, error } = useTemporalEvolution();

  const membersData =
    data?.map((d) => ({ year: d.year, value: d.members })) ?? [];

  const companiesData =
    data?.map((d) => ({ year: d.year, value: d.companies })) ?? [];

  const membershipsData =
    data?.map((d) => ({ year: d.year, value: d.memberships })) ?? [];

  return (
    <>
      <Header title="Analise Temporal" />
      <main className="p-6 space-y-6">
        <p className="text-sm text-[var(--color-text-2)]">
          Evolucao da rede de conselheiros ao longo do tempo
        </p>

        {error && (
          <div className="bg-[var(--color-danger)]/10 border border-[var(--color-danger)]/20 p-4 text-sm text-[var(--color-danger)]">
            Erro ao carregar dados temporais. Tente novamente mais tarde.
          </div>
        )}

        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
          {isLoading ? (
            <>
              <TimelineChartSkeleton />
              <TimelineChartSkeleton />
              <TimelineChartSkeleton />
            </>
          ) : (
            <>
              <TimelineChart
                data={membersData}
                title="Membros ao longo do tempo"
                color="#1B5E4B"
              />
              <TimelineChart
                data={companiesData}
                title="Empresas ao longo do tempo"
                color="#1B5E4B"
              />
              <TimelineChart
                data={membershipsData}
                title="Participacoes ao longo do tempo"
                color="#F2A900"
              />
            </>
          )}
        </div>
      </main>
    </>
  );
}
