export interface Member {
  id: string;
  nome: string;
  nome_normalizado: string;
  formacao?: string;
  page_rank?: number;
  betweenness?: number;
  degree_centrality?: number;
  eigenvector?: number;
  closeness?: number;
  clustering_coeff?: number;
  community_id?: number;
  k_core?: number;
}

export interface Company {
  cd_cvm: number;
  cnpj?: string;
  nome: string;
  setor?: string;
  segmento_listagem?: string;
  situacao?: string;
}

export interface GraphNode {
  id: string;
  label: string;
  size: number;
  color: string;
  x: number;
  y: number;
  community?: number;
  pageRank?: number;
}

export interface GraphEdge {
  source: string;
  target: string;
  weight: number;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface MetricsOverview {
  total_members: number;
  total_companies: number;
  total_connections: number;
  avg_degree?: number;
  num_communities: number;
  modularity?: number;
}

export interface ConcentrationMetrics {
  gini_centrality: number;
  hhi_seats: number;
  hhi_memberships?: number;
  interlocking_index: number;
  network_density: number;
}

export interface CompanyInfo {
  cd_cvm: number;
  nome: string;
  cargo?: string;
}

export interface MemberWithCompanies {
  member: Member;
  companies: CompanyInfo[];
}

export interface BoardMember {
  id: string;
  nome: string;
  cargo: string;
  ano_referencia?: number;
  page_rank?: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface CompanyMembership {
  cd_cvm: number;
  nome: string;
  cargo: string;
  ano_referencia?: number;
  data_eleicao?: string;
}

export interface ConnectionSummary {
  id: string;
  nome: string;
  page_rank?: number;
}

export interface MemberDetail {
  member: Member;
  companies: CompanyMembership[];
  connections: ConnectionSummary[];
}

export interface BoardResponse {
  company: Company;
  board_members: BoardMember[];
}

export interface InterlockingCompany {
  company: Company;
  shared_members: string[];
  shared_count: number;
}

export interface JobStatus {
  job_id: string;
  type: string;
  status: "pending" | "running" | "completed" | "failed";
  progress: number;
  message: string;
  started_at: string | null;
  completed_at: string | null;
  result: Record<string, unknown> | null;
}
