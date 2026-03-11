import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type { BoardResponse, InterlockingCompany } from "@/types";

export function useCompanyBoard(cdCvm: string) {
  return useQuery<BoardResponse>({
    queryKey: ["company", cdCvm, "board"],
    queryFn: () => apiFetch<BoardResponse>(`/companies/${cdCvm}/board`),
    enabled: !!cdCvm,
  });
}

export function useCompanyNetwork(cdCvm: string) {
  return useQuery<InterlockingCompany[]>({
    queryKey: ["company", cdCvm, "network"],
    queryFn: () =>
      apiFetch<InterlockingCompany[]>(`/companies/${cdCvm}/network`),
    enabled: !!cdCvm,
  });
}
