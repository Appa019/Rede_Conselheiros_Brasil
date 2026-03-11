import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type { MetricsOverview, ConcentrationMetrics, Member } from "@/types";

export function useMetricsOverview() {
  return useQuery<MetricsOverview>({
    queryKey: ["metrics", "overview"],
    queryFn: () => apiFetch<MetricsOverview>("/metrics/overview"),
  });
}

export function useConcentration() {
  return useQuery<ConcentrationMetrics>({
    queryKey: ["metrics", "concentration"],
    queryFn: () => apiFetch<ConcentrationMetrics>("/metrics/concentration"),
  });
}

export function useTopMembers(metric: string = "page_rank", limit: number = 10) {
  return useQuery<Member[]>({
    queryKey: ["members", "top", metric, limit],
    queryFn: () =>
      apiFetch<Member[]>(`/members/top?metric=${metric}&limit=${limit}`),
  });
}
