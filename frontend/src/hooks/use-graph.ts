import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";

interface GraphNetworkNode {
  id: string;
  nome: string;
  page_rank?: number;
  community_id?: number;
  degree_centrality?: number;
  connections: number;
}

interface GraphNetworkEdge {
  source: string;
  target: string;
  weight?: number;
}

interface GraphNetworkResponse {
  nodes: GraphNetworkNode[];
  edges?: GraphNetworkEdge[];
}

interface GraphNetworkParams {
  year?: number;
  sector?: string;
  min_connections?: number;
  limit?: number;
  search?: string;
}

export function useGraphNetwork(params: GraphNetworkParams = {}) {
  return useQuery<GraphNetworkResponse>({
    queryKey: ["graph-network", params],
    queryFn: async () => {
      const searchParams = new URLSearchParams();

      if (params.year) searchParams.set("year", String(params.year));
      if (params.sector) searchParams.set("sector", params.sector);
      if (params.min_connections) searchParams.set("min_connections", String(params.min_connections));
      if (params.limit) searchParams.set("limit", String(params.limit));
      if (params.search) searchParams.set("search", params.search);

      const query = searchParams.toString();
      const res = await apiFetch<GraphNetworkResponse>(`/graph/network${query ? `?${query}` : ""}`);
      return { ...res, edges: res.edges ?? [] };
    },
  });
}
