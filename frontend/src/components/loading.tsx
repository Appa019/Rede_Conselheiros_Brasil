import { Loader2 } from "lucide-react";

interface LoadingProps {
  message?: string;
}

export function Loading({ message = "Carregando..." }: LoadingProps) {
  return (
    <div className="flex flex-col items-center justify-center p-12">
      <Loader2 className="h-8 w-8 text-[var(--color-accent)] animate-spin mb-3" />
      <p className="text-sm text-[var(--color-text-3)]">{message}</p>
    </div>
  );
}
