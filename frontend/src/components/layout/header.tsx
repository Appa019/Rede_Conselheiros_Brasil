interface HeaderProps {
  title: string;
  subtitle?: string;
}

export function Header({ title, subtitle }: HeaderProps) {
  return (
    <header className="px-6 pt-6 pb-4">
      <h1 className="text-xl font-semibold font-[family-name:var(--font-heading)]">
        {title}
      </h1>
      {subtitle && (
        <p className="text-sm text-[var(--color-text-2)] mt-0.5">{subtitle}</p>
      )}
    </header>
  );
}
