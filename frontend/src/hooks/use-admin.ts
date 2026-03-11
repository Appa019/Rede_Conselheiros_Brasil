import { useCallback, useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch, apiPost } from "@/lib/api";
import type { JobStatus } from "@/types";

const STORAGE_KEY = "admin_active_jobs";

interface PersistedJobs {
  etl?: string;
  metrics?: string;
  train?: string;
  metricsAutoTriggered?: boolean;
}

function loadPersistedJobs(): PersistedJobs {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

function savePersistedJobs(jobs: PersistedJobs) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(jobs));
  } catch {
    // localStorage unavailable
  }
}

function clearPersistedJob(key: keyof PersistedJobs) {
  const current = loadPersistedJobs();
  delete current[key];
  savePersistedJobs(current);
}

export function useTriggerETL() {
  return useMutation<JobStatus>({
    mutationFn: () => apiPost<JobStatus>("/admin/etl"),
  });
}

export function useTriggerMetrics() {
  return useMutation<JobStatus>({
    mutationFn: () => apiPost<JobStatus>("/admin/compute-metrics"),
  });
}

export function useTriggerTrain() {
  return useMutation<JobStatus>({
    mutationFn: () => apiPost<JobStatus>("/admin/train"),
  });
}

export function useJobStatus(jobId: string | null) {
  return useQuery<JobStatus>({
    queryKey: ["admin", "job", jobId],
    queryFn: async () => {
      const res = await apiFetch<JobStatus>(`/admin/jobs/${jobId}`);
      return res;
    },
    enabled: !!jobId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === "completed" || status === "failed") return false;
      return 2000;
    },
    retry: 1,
  });
}

/**
 * Central hook that manages the full admin workflow:
 * - Persists active job IDs to localStorage
 * - Recovers running jobs on mount (survives navigation)
 * - Auto-triggers compute-metrics after ETL completes
 * - Invalidates dashboard caches on completion
 */
export function useAdminWorkflow() {
  const queryClient = useQueryClient();
  const triggerETL = useTriggerETL();
  const triggerMetrics = useTriggerMetrics();
  const triggerTrain = useTriggerTrain();

  // Initialize from localStorage
  const persisted = loadPersistedJobs();
  const [etlJobId, setEtlJobId] = useState<string | null>(persisted.etl ?? null);
  const [metricsJobId, setMetricsJobId] = useState<string | null>(persisted.metrics ?? null);
  const [trainJobId, setTrainJobId] = useState<string | null>(persisted.train ?? null);

  const metricsAutoTriggeredRef = useRef(persisted.metricsAutoTriggered ?? false);

  // Poll job statuses
  const etlJob = useJobStatus(etlJobId);
  const metricsJob = useJobStatus(metricsJobId);
  const trainJob = useJobStatus(trainJobId);

  // Clear stale job IDs when backend returns 404 (e.g. after restart)
  useEffect(() => {
    if (etlJobId && etlJob.isError) {
      setEtlJobId(null);
      clearPersistedJob("etl");
    }
  }, [etlJobId, etlJob.isError]);

  useEffect(() => {
    if (metricsJobId && metricsJob.isError) {
      setMetricsJobId(null);
      clearPersistedJob("metrics");
      metricsAutoTriggeredRef.current = false;
    }
  }, [metricsJobId, metricsJob.isError]);

  useEffect(() => {
    if (trainJobId && trainJob.isError) {
      setTrainJobId(null);
      clearPersistedJob("train");
    }
  }, [trainJobId, trainJob.isError]);

  // Persist job IDs whenever they change
  useEffect(() => {
    const data: PersistedJobs = {};
    if (etlJobId) data.etl = etlJobId;
    if (metricsJobId) data.metrics = metricsJobId;
    if (trainJobId) data.train = trainJobId;
    data.metricsAutoTriggered = metricsAutoTriggeredRef.current;
    savePersistedJobs(data);
  }, [etlJobId, metricsJobId, trainJobId]);

  // Auto-trigger metrics after ETL completes (only once)
  const etlStatus = etlJob.data?.status;
  useEffect(() => {
    if (etlStatus !== "completed") return;
    if (metricsAutoTriggeredRef.current) return;

    metricsAutoTriggeredRef.current = true;
    savePersistedJobs({ ...loadPersistedJobs(), metricsAutoTriggered: true });

    triggerMetrics.mutate(undefined, {
      onSuccess: (data) => {
        setMetricsJobId(data.job_id);
      },
      onError: () => {
        // Metrics trigger failed, but ETL succeeded — still mark ETL as done
      },
    });
  }, [etlStatus]); // eslint-disable-line react-hooks/exhaustive-deps

  // Invalidate dashboard caches when metrics computation completes
  const metricsStatus = metricsJob.data?.status;
  useEffect(() => {
    if (metricsStatus === "completed") {
      queryClient.invalidateQueries({ queryKey: ["metrics"] });
      queryClient.invalidateQueries({ queryKey: ["members"] });
    }
  }, [metricsStatus, queryClient]);

  // Clean up persisted keys for finished jobs (after a short delay so results display)
  const trainStatus = trainJob.data?.status;
  useEffect(() => {
    if (etlStatus === "failed") clearPersistedJob("etl");
    if (metricsStatus === "failed") clearPersistedJob("metrics");
    if (trainStatus === "failed") clearPersistedJob("train");
  }, [etlStatus, metricsStatus, trainStatus]);

  const handleETL = useCallback(() => {
    metricsAutoTriggeredRef.current = false;
    setMetricsJobId(null);
    triggerETL.mutate(undefined, {
      onSuccess: (data) => setEtlJobId(data.job_id),
    });
  }, [triggerETL]);

  const handleTrain = useCallback(() => {
    triggerTrain.mutate(undefined, {
      onSuccess: (data) => setTrainJobId(data.job_id),
    });
  }, [triggerTrain]);

  return {
    etlJob, metricsJob, trainJob,
    etlJobId, metricsJobId, trainJobId,
    handleETL, handleTrain,
    isETLMutating: triggerETL.isPending,
    isTrainMutating: triggerTrain.isPending,
  };
}
