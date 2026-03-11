"use client";

import { Search } from "lucide-react";
import { useState } from "react";

interface GraphFiltersProps {
  onApply: (filters: GraphFilterValues) => void;
  isLoading?: boolean;
}

export interface GraphFilterValues {
  year?: number;
  sector?: string;
  min_connections?: number;
  search?: string;
}

const YEARS = [2026, 2025, 2024, 2023, 2022, 2021];

const SECTORS = [
  "Financeiro",
  "Energia",
  "Saude",
  "Tecnologia",
  "Varejo",
  "Industria",
  "Telecomunicacoes",
  "Mineracao",
  "Alimentos",
  "Construcao",
];

export function GraphFilters({ onApply, isLoading }: GraphFiltersProps) {
  const [year, setYear] = useState<number | undefined>(undefined);
  const [sector, setSector] = useState<string>("");
  const [minConnections, setMinConnections] = useState<number>(1);
  const [search, setSearch] = useState<string>("");

  const handleApply = () => {
    onApply({
      year,
      sector: sector || undefined,
      min_connections: minConnections,
      search: search || undefined,
    });
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") handleApply();
  };

  const inputClass =
    "py-1.5 px-3 text-sm border border-[var(--color-border)] bg-white text-[var(--color-text)] focus:outline-none focus:ring-1 focus:ring-[var(--color-accent)]/40 transition-colors";

  return (
    <div className="flex items-center gap-3 px-4 py-3 bg-[var(--color-surface)] border-b border-[var(--color-border)]">
      {/* Search by name */}
      <div className="relative flex-shrink-0">
        <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-[var(--color-text-3)]" />
        <input
          type="text"
          placeholder="Buscar membro..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          onKeyDown={handleKeyDown}
          className={`${inputClass} pl-8 pr-3 w-48`}
        />
      </div>

      {/* Year selector */}
      <label className="text-xs text-[var(--color-text-3)]">Ano</label>
      <select
        value={year ?? ""}
        onChange={(e) => setYear(e.target.value ? Number(e.target.value) : undefined)}
        className={inputClass}
      >
        <option value="">Todos</option>
        {YEARS.map((y) => (
          <option key={y} value={y}>
            {y}
          </option>
        ))}
      </select>

      {/* Sector filter */}
      <label className="text-xs text-[var(--color-text-3)]">Setor</label>
      <select
        value={sector}
        onChange={(e) => setSector(e.target.value)}
        className={inputClass}
      >
        <option value="">Todos</option>
        {SECTORS.map((s) => (
          <option key={s} value={s}>
            {s}
          </option>
        ))}
      </select>

      {/* Min connections slider */}
      <div className="flex items-center gap-2 flex-shrink-0">
        <label className="text-xs text-[var(--color-text-3)] whitespace-nowrap">
          Min. conexoes
        </label>
        <input
          type="range"
          min={1}
          max={20}
          value={minConnections}
          onChange={(e) => setMinConnections(Number(e.target.value))}
          className="w-24 accent-[var(--color-accent)]"
        />
        <span className="text-xs font-[family-name:var(--font-mono)] font-medium text-[var(--color-text-2)] w-5 text-center">
          {minConnections}
        </span>
      </div>

      {/* Apply button */}
      <button
        onClick={handleApply}
        disabled={isLoading}
        type="button"
        className="ml-auto px-4 py-1.5 text-sm font-medium text-white bg-[var(--color-accent)] hover:opacity-90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {isLoading ? "Carregando..." : "Aplicar"}
      </button>
    </div>
  );
}
