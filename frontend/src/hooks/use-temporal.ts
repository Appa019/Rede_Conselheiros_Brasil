import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";

interface TemporalDataPoint {
  year: number;
  members: number;
  companies: number;
  memberships: number;
}

export function useTemporalEvolution() {
  return useQuery({
    queryKey: ["temporal", "evolution"],
    queryFn: () => apiFetch<TemporalDataPoint[]>("/temporal/evolution"),
  });
}
