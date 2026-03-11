import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type {
  MemberWithCompanies,
  MemberDetail,
  PaginatedResponse,
} from "@/types";

export function useMembers(
  search: string = "",
  page: number = 1,
  pageSize: number = 20
) {
  return useQuery<PaginatedResponse<MemberWithCompanies>>({
    queryKey: ["members", search, page, pageSize],
    queryFn: () => {
      const params = new URLSearchParams({
        page: String(page),
        page_size: String(pageSize),
      });
      if (search) params.set("search", search);
      return apiFetch<PaginatedResponse<MemberWithCompanies>>(
        `/members?${params.toString()}`
      );
    },
  });
}

export function useMember(id: string) {
  return useQuery<MemberDetail>({
    queryKey: ["member", id],
    queryFn: () => apiFetch<MemberDetail>(`/members/${id}`),
    enabled: !!id,
  });
}
