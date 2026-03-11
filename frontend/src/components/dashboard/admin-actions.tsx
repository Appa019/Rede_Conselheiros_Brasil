"use client";

import { useState, useEffect, useRef } from "react";
import { RefreshCw, Brain, Check, X, Loader2 } from "lucide-react";
import { useAdminWorkflow } from "@/hooks/use-admin";

function formatDuration(seconds: number): string {
  if (seconds < 0) return "0s";
  if (seconds < 60) return `${Math.round(seconds)}s`;
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return `${m}m ${s}s`;
}

function getAucLabel(auc: number): { text: string; color: string } {
  if (auc >= 0.9) return { text: "Excelente", color: "text-[var(--color-accent)]" };
  if (auc >= 0.8) return { text: "Bom", color: "text-[var(--color-accent)]" };
  if (auc >= 0.7) return { text: "Moderado", color: "text-[var(--color-warm)]" };
  return { text: "Baixo", color: "text-[var(--color-danger)]" };
}

interface ActionCardProps {
  title: string;
  description: string;
  icon: typeof RefreshCw;
  isRunning: boolean;
  isComplete: boolean;
  isFailed: boolean;
  isDisabled: boolean;
  progress: number;
  message: string;
  startedAt: string | null;
  onTrigger: () => void;
  resultContent?: React.ReactNode;
}

function ActionCard({
  title,
  description,
  icon: Icon,
  isRunning,
  isComplete,
  isFailed,
  isDisabled,
  progress,
  message,
  startedAt,
  onTrigger,
  resultContent,
}: ActionCardProps) {
  const [elapsed, setElapsed] = useState(0);
  const progressHistoryRef = useRef<{ time: number; progress: number }[]>([]);

  useEffect(() => {
    if (!isRunning || !startedAt) {
      setElapsed(0);
      progressHistoryRef.current = [];
      return;
    }
    const start = new Date(startedAt).getTime();
    const tick = () => {
      setElapsed(Math.max(0, (Date.now() - start) / 1000));
    };
    tick();
    const interval = setInterval(tick, 1000);
    return () => clearInterval(interval);
  }, [isRunning, startedAt]);

  // Track progress history for ETA calculation
  useEffect(() => {
    if (!isRunning || progress <= 0) return;
    const history = progressHistoryRef.current;
    const now = Date.now();
    // Only add if progress actually changed
    if (history.length === 0 || history[history.length - 1].progress !== progress) {
      history.push({ time: now, progress });
      // Keep last 10 samples
      if (history.length > 10) history.shift();
    }
  }, [isRunning, progress]);

  // Calculate ETA from progress rate
  const eta = (() => {
    if (!isRunning || progress <= 0 || progress >= 100) return null;
    const history = progressHistoryRef.current;
    if (history.length < 2) return null;

    const first = history[0];
    const last = history[history.length - 1];
    const timeDelta = (last.time - first.time) / 1000; // seconds
    const progressDelta = last.progress - first.progress;

    if (timeDelta <= 0 || progressDelta <= 0) return null;

    const rate = progressDelta / timeDelta; // % per second
    const remaining = (100 - progress) / rate; // seconds

    if (remaining > 3600) return null; // Unreasonable
    return remaining;
  })();

  const hasActivity = isRunning || isComplete || isFailed;
  const buttonDisabled = isRunning || isDisabled;

  const buttonLabel = isRunning
    ? "Executando..."
    : isDisabled
      ? "Aguarde..."
      : isComplete
        ? "Executar novamente"
        : isFailed
          ? "Tentar novamente"
          : "Executar";

  const progressBarColor = isFailed
    ? "bg-[var(--color-danger)]"
    : "bg-[var(--color-accent)]";

  return (
    <div className="bg-[var(--color-surface)] border border-[var(--color-border)] p-5 flex flex-col gap-4">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-2.5">
          <Icon className="h-4 w-4 text-[var(--color-text-2)]" />
          <div>
            <h3 className="text-sm font-medium text-[var(--color-text)]">{title}</h3>
            <p className="text-xs text-[var(--color-text-3)] mt-0.5">{description}</p>
          </div>
        </div>

        <div className="flex-shrink-0">
          {isRunning && (
            <Loader2 className="h-4 w-4 text-[var(--color-text-3)] animate-spin" />
          )}
          {isComplete && (
            <Check className="h-4 w-4 text-[var(--color-accent)]" />
          )}
          {isFailed && (
            <X className="h-4 w-4 text-[var(--color-danger)]" />
          )}
        </div>
      </div>

      {hasActivity && (
        <div className="space-y-2">
          {/* Progress bar with percentage */}
          <div className="flex items-center gap-3">
            <div className="flex-1 h-1.5 bg-[var(--color-surface-alt)] rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full ${progressBarColor} transition-all duration-500 ease-out`}
                style={{ width: `${Math.min(progress, 100)}%` }}
              />
            </div>
            <span className="text-xs font-[family-name:var(--font-mono)] text-[var(--color-text-2)] w-10 text-right tabular-nums">
              {Math.round(progress)}%
            </span>
          </div>

          {/* Current step message */}
          <p className="text-xs font-medium text-[var(--color-text)] truncate">
            {message}
          </p>

          {/* Elapsed + ETA */}
          {isRunning && (
            <div className="flex items-center justify-between text-[11px] font-[family-name:var(--font-mono)] text-[var(--color-text-3)]">
              <span>Tempo: {formatDuration(elapsed)}</span>
              {eta !== null && (
                <span>ETA: ~{formatDuration(eta)}</span>
              )}
            </div>
          )}
        </div>
      )}

      {isComplete && resultContent && (
        <div className="text-xs text-[var(--color-text-2)] font-[family-name:var(--font-mono)] bg-white border border-[var(--color-border)] p-3">
          {resultContent}
        </div>
      )}

      <button
        onClick={onTrigger}
        disabled={buttonDisabled}
        className={`w-full py-1.5 px-4 text-xs font-medium transition-colors
          ${buttonDisabled
            ? "bg-[var(--color-surface-alt)] text-[var(--color-text-3)] opacity-40 cursor-not-allowed"
            : "bg-[var(--color-surface)] text-[var(--color-text)] hover:bg-[var(--color-surface-alt)] border border-[var(--color-border)] cursor-pointer"
          }`}
      >
        {buttonLabel}
      </button>
    </div>
  );
}

export function AdminActions() {
  const {
    etlJob, metricsJob, trainJob,
    metricsJobId,
    handleETL, handleTrain,
    isETLMutating, isTrainMutating,
  } = useAdminWorkflow();

  // --- ETL combined state (ETL + auto-metrics) ---
  const etlData = etlJob.data;
  const metricsData = metricsJob.data;

  const etlActive = etlData?.status === "running" || etlData?.status === "pending";
  const metricsActive = metricsData?.status === "running" || metricsData?.status === "pending";
  const isETLRunning = etlActive || metricsActive;
  const isETLComplete = !isETLRunning && (
    metricsData?.status === "completed"
    || (etlData?.status === "completed" && !metricsJobId)
  );
  const isETLFailed = !isETLRunning && (
    etlData?.status === "failed" || metricsData?.status === "failed"
  );

  let etlProgress = 0;
  let etlMessage = "";
  if (etlActive) {
    etlProgress = (etlData?.progress ?? 0) * 0.7;
    etlMessage = etlData?.message ?? "Iniciando...";
  } else if (etlData?.status === "completed" && metricsActive) {
    etlProgress = 70 + ((metricsData?.progress ?? 0) * 0.3);
    etlMessage = metricsData?.message || "Computando metricas...";
  } else if (isETLComplete) {
    etlProgress = 100;
    etlMessage = "Dados atualizados e metricas computadas";
  } else if (isETLFailed) {
    etlProgress = etlData?.progress ?? metricsData?.progress ?? 0;
    etlMessage = etlData?.status === "failed"
      ? (etlData.message || "ETL falhou")
      : (metricsData?.message || "Metricas falharam");
  }

  const etlResult = etlData?.result as Record<string, unknown> | null;
  const etlResultContent = isETLComplete && etlResult ? (
    <span>
      {etlResult.persons ? `${Number(etlResult.persons).toLocaleString("pt-BR")} pessoas` : ""}
      {etlResult.companies ? ` · ${Number(etlResult.companies).toLocaleString("pt-BR")} empresas` : ""}
      {etlResult.memberships ? ` · ${Number(etlResult.memberships).toLocaleString("pt-BR")} vinculos` : ""}
    </span>
  ) : null;

  // --- Train state ---
  const trainData = trainJob.data;
  const isTrainRunning = trainData?.status === "running" || trainData?.status === "pending";
  const isTrainComplete = trainData?.status === "completed";
  const isTrainFailed = trainData?.status === "failed";

  const linkPred = trainData?.result?.link_prediction as Record<string, unknown> | undefined;
  const auc = typeof linkPred?.auc_roc === "number" ? linkPred.auc_roc : null;
  const aucInfo = auc != null ? getAucLabel(auc) : null;

  const trainResultContent = isTrainComplete && trainData?.result ? (
    <span>
      {auc != null && aucInfo ? (
        <>AUC-ROC: <span className={aucInfo.color}>{auc.toFixed(4)} ({aucInfo.text})</span></>
      ) : null}
      {trainData.result.embeddings ? (
        <> · {(trainData.result.embeddings as Record<string, unknown>).count} embeddings</>
      ) : null}
    </span>
  ) : null;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
      <ActionCard
        title="Atualizar Dados"
        description="ETL completo: download CVM, parse, clean, load Neo4j + metricas"
        icon={RefreshCw}
        isRunning={isETLRunning}
        isComplete={isETLComplete}
        isFailed={isETLFailed}
        isDisabled={isETLMutating}
        progress={etlProgress}
        message={etlMessage}
        startedAt={etlData?.started_at ?? null}
        onTrigger={handleETL}
        resultContent={etlResultContent}
      />
      <ActionCard
        title="Treinar Modelo"
        description="Node2Vec embeddings + link prediction (Random Forest)"
        icon={Brain}
        isRunning={isTrainRunning}
        isComplete={isTrainComplete}
        isFailed={isTrainFailed}
        isDisabled={isTrainMutating}
        progress={trainData?.progress ?? 0}
        message={trainData?.message ?? ""}
        startedAt={trainData?.started_at ?? null}
        onTrigger={handleTrain}
        resultContent={trainResultContent}
      />
    </div>
  );
}
