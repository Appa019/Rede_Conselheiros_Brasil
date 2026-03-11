"use client";

import { MetricCard, MetricCardSkeleton } from "@/components/dashboard/metric-card";
import { TopConnected } from "@/components/dashboard/top-connected";
import { ConcentrationIndex } from "@/components/dashboard/concentration-index";
import { AdminActions } from "@/components/dashboard/admin-actions";
import { useMetricsOverview } from "@/hooks/use-metrics";
import { Users, Building2, Link2, Network } from "lucide-react";

export default function DashboardPage() {
  const { data: overview, isLoading } = useMetricsOverview();

  return (
    <main className="p-6 space-y-6">
      <div className="pt-2 pb-2">
        <h1 className="text-xl font-semibold font-[family-name:var(--font-heading)] text-[var(--color-text)]">
          Dashboard
        </h1>
        {overview && (
          <p className="text-sm text-[var(--color-text-2)] mt-1">
            {overview.total_members.toLocaleString("pt-BR")} conselheiros
            {" · "}
            {overview.total_companies.toLocaleString("pt-BR")} empresas
            {" · "}
            {overview.num_communities.toLocaleString("pt-BR")} comunidades
          </p>
        )}
      </div>

      <AdminActions />

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        {isLoading ? (
          <>
            <MetricCardSkeleton />
            <MetricCardSkeleton />
            <MetricCardSkeleton />
            <MetricCardSkeleton />
          </>
        ) : overview ? (
          <>
            <MetricCard
              title="Membros"
              value={overview.total_members}
              subtitle="Conselheiros e diretores unicos"
              icon={Users}
              index={0}
              accentColor="green"
            />
            <MetricCard
              title="Empresas"
              value={overview.total_companies}
              subtitle="Companhias abertas"
              icon={Building2}
              index={1}
              accentColor="gold"
            />
            <MetricCard
              title="Conexoes"
              value={overview.total_connections}
              subtitle="Vinculos na rede"
              icon={Link2}
              index={2}
              accentColor="green"
            />
            <MetricCard
              title="Comunidades"
              value={overview.num_communities}
              subtitle={`Grau medio: ${overview.avg_degree?.toFixed(1) ?? "—"}`}
              icon={Network}
              index={3}
              accentColor="gold"
            />
          </>
        ) : null}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <TopConnected />
        </div>
        <div>
          <ConcentrationIndex />
        </div>
      </div>
    </main>
  );
}
