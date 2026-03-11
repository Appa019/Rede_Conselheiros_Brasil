"use client";

import { Search } from "lucide-react";

interface HeaderProps {
  title: string;
  subtitle?: string;
}

export function Header({ title, subtitle }: HeaderProps) {
  return (
    <header className="px-6 pt-6 pb-4 flex items-end justify-between">
      <div>
        <h1 className="text-xl font-semibold font-[family-name:var(--font-heading)]">
          {title}
        </h1>
        {subtitle && (
          <p className="text-sm text-[var(--color-text-2)] mt-0.5">{subtitle}</p>
        )}
      </div>

      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-[var(--color-text-3)]" />
        <input
          type="text"
          placeholder="Buscar..."
          className="pl-9 pr-3 py-1.5 text-sm bg-white text-[var(--color-text)] placeholder:text-[var(--color-text-3)] focus:outline-none focus:ring-1 focus:ring-[var(--color-accent)]/40 transition-colors w-56 border border-[var(--color-border)]"
        />
      </div>
    </header>
  );
}
