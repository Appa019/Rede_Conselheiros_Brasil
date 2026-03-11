"use client";

import { useConcentration } from "@/hooks/use-metrics";

function getSeverityColor(value: number): string {
  if (value < 0.3) return "var(--color-accent)";
  if (value < 0.6) return "var(--color-warm)";
  return "var(--color-danger)";
}

function getSeverityLabel(value: number): string {
  if (value < 0.3) return "Baixo";
  if (value < 0.6) return "Moderado";
  return "Alto";
}

interface IndicatorProps {
  label: string;
  value: number;
  description: string;
  benchmark?: string;
}

function ConcentrationIndicator({ label, value, description, benchmark }: IndicatorProps) {
  const barWidth = Math.min(value * 100, 100);
  const color = getSeverityColor(value);
  const severity = getSeverityLabel(value);

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <p className="text-sm text-[var(--color-text-2)]">{label}</p>
        <span className="text-xs text-[var(--color-text-3)]">{severity}</span>
      </div>
      <div className="flex items-center gap-3">
        <div className="flex-1 h-1 bg-[var(--color-surface-alt)] rounded-full overflow-hidden">
          <div
            className="h-full rounded-full transition-all"
            style={{ width: `${barWidth}%`, backgroundColor: color }}
          />
        </div>
        <span className="text-sm font-[family-name:var(--font-mono)] text-[var(--color-text)] w-12 text-right">
          {value.toFixed(2)}
        </span>
      </div>
      <p className="text-xs text-[var(--color-text-3)]">{description}</p>
      {benchmark && (
        <p className="text-xs text-[var(--color-text-3)]">{benchmark}</p>
      )}
    </div>
  );
}

function ConcentrationSkeleton() {
  return (
    <div className="bg-[var(--color-surface)] border border-[var(--color-border)] p-5 space-y-5">
      <div className="h-4 w-40 animate-pulse bg-[var(--color-surface-alt)]" />
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="space-y-2">
          <div className="h-3 w-28 animate-pulse bg-[var(--color-surface-alt)]" />
          <div className="h-1 w-full animate-pulse bg-[var(--color-surface-alt)] rounded-full" />
          <div className="h-3 w-44 animate-pulse bg-[var(--color-surface-alt)]" />
        </div>
      ))}
    </div>
  );
}

export function ConcentrationIndex() {
  const { data, isLoading } = useConcentration();

  if (isLoading) return <ConcentrationSkeleton />;
  if (!data) return null;

  const metrics: IndicatorProps[] = [
    {
      label: "Gini de Centralidade",
      value: data.gini_centrality,
      description: "Desigualdade na distribuicao de conexoes",
      benchmark: "Redes de boards tipicas: 0.35-0.55",
    },
    {
      label: "HHI de Assentos",
      value: data.hhi_seats,
      description: "Concentracao de cargos em poucos membros",
      benchmark: "Nao concentrado < 0.01 | Moderado 0.01-0.10 | Concentrado > 0.10",
    },
    {
      label: "Indice de Interlocking",
      value: data.interlocking_index,
      description: "Grau de interconexao entre empresas",
    },
    {
      label: "Densidade da Rede",
      value: data.network_density,
      description: "Proporcao de conexoes existentes vs possiveis",
      benchmark: "Interlocking tipico: 0.001-0.01",
    },
  ];

  return (
    <div className="bg-[var(--color-surface)] border border-[var(--color-border)] p-5">
      <h2 className="text-base font-semibold font-[family-name:var(--font-heading)] text-[var(--color-text)] mb-5">
        Concentracao de poder
      </h2>

      <div className="space-y-5">
        {metrics.map((m) => (
          <ConcentrationIndicator key={m.label} {...m} />
        ))}
      </div>
    </div>
  );
}
