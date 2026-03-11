"use client";

import { Component, type ReactNode } from "react";
import { AlertTriangle } from "lucide-react";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  render() {
    if (this.state.hasError) {
      return (
        this.props.fallback || (
          <div className="flex flex-col items-center justify-center p-12 text-center">
            <AlertTriangle className="h-12 w-12 text-[#F2A900] mb-4" />
            <h2 className="text-lg font-semibold text-[var(--color-text)] mb-2">Algo deu errado</h2>
            <p className="text-[var(--color-text-3)] text-sm max-w-md">
              {this.state.error?.message || "Erro inesperado. Tente recarregar a pagina."}
            </p>
            <button
              onClick={() => this.setState({ hasError: false })}
              className="mt-4 px-4 py-2 bg-[var(--color-accent)] text-white text-sm hover:bg-[var(--color-accent-light)] transition-colors"
            >
              Tentar novamente
            </button>
          </div>
        )
      );
    }

    return this.props.children;
  }
}
