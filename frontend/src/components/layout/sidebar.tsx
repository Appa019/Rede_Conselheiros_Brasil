"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Network,
  Users,
  Building2,
  Clock,
  BrainCircuit,
} from "lucide-react";
import { CvmLogo } from "@/components/icons/cvm-logo";

const navItems = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/explorer", label: "Explorer", icon: Network },
  { href: "/members", label: "Membros", icon: Users },
  { href: "/companies", label: "Empresas", icon: Building2 },
  { href: "/temporal", label: "Temporal", icon: Clock },
  { href: "/predictions", label: "Predicoes", icon: BrainCircuit },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed left-0 top-0 h-full w-56 bg-white flex flex-col border-r border-[var(--color-border)]">
      {/* Logo */}
      <div className="px-5 py-5">
        <Link href="/" className="flex items-center gap-2.5">
          <CvmLogo className="w-7 h-7" />
          <span className="text-[15px] font-semibold tracking-tight font-[family-name:var(--font-heading)]">
            Rede CVM
          </span>
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 mt-1 space-y-0.5">
        {navItems.map(({ href, label, icon: Icon }) => {
          const isActive =
            pathname === href ||
            (href !== "/" && pathname.startsWith(href));

          return (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-2.5 py-2 px-3 text-[13px] font-medium transition-colors ${
                isActive
                  ? "text-[var(--color-accent)] bg-[var(--color-accent-dim)]"
                  : "text-[var(--color-text-2)] hover:text-[var(--color-text)] hover:bg-[var(--color-surface-alt)]"
              }`}
            >
              <Icon className="h-[18px] w-[18px]" />
              {label}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="px-5 pb-4">
        <div className="flex items-center gap-2 text-[11px] text-[var(--color-text-3)]">
          <span className="h-1.5 w-1.5 rounded-full bg-[var(--color-accent)]" />
          Neo4j conectado
        </div>
      </div>
    </aside>
  );
}
