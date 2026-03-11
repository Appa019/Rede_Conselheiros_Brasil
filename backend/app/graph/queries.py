"""Cypher query templates for the Rede de Conselheiros CVM project."""

# Network queries
GET_NETWORK = """
MATCH (p:Person)-[r:MEMBER_OF]->(c:Company)
WHERE ($year IS NULL OR r.ano_referencia = $year)
  AND ($sector IS NULL OR EXISTS {
    MATCH (c)-[:BELONGS_TO]->(s:Sector {nome: $sector})
  })
WITH p, c, r
OPTIONAL MATCH (p)-[co:CO_MEMBER]-(p2:Person)
WITH p, collect(DISTINCT {
  cd_cvm: c.cd_cvm,
  nome: c.nome,
  cargo: r.cargo
}) AS companies,
count(DISTINCT p2) AS connections
WHERE connections >= $min_connections
RETURN p.id AS id, p.nome AS nome, p.page_rank AS page_rank,
       p.community_id AS community_id, p.degree_centrality AS degree_centrality,
       companies, connections
ORDER BY p.page_rank DESC
LIMIT $limit
"""

GET_SUBGRAPH = """
MATCH (center:Person {id: $person_id})
MATCH (center)-[co:CO_MEMBER]-(neighbor:Person)
WITH center, neighbor, co
OPTIONAL MATCH (neighbor)-[co2:CO_MEMBER]-(neighbor2:Person)
WHERE neighbor2.id <> center.id AND (neighbor2)-[:CO_MEMBER]-(center)
RETURN center, neighbor, co, neighbor2, co2
"""

GET_COMMUNITIES = """
MATCH (p:Person)
WHERE p.community_id IS NOT NULL
WITH p.community_id AS community_id, collect({
  id: p.id, nome: p.nome, page_rank: p.page_rank
}) AS members
RETURN community_id, size(members) AS member_count,
       members[..10] AS top_members
ORDER BY member_count DESC
"""

# Member queries
GET_MEMBERS = """
MATCH (p:Person)
WHERE $search IS NULL OR p.nome_normalizado CONTAINS toUpper($search)
WITH p ORDER BY p.page_rank DESC
SKIP $skip LIMIT $limit
OPTIONAL MATCH (p)-[r:MEMBER_OF]->(c:Company)
WITH p, collect(DISTINCT {cd_cvm: c.cd_cvm, nome: c.nome, cargo: r.cargo}) AS companies
RETURN p {.id, .nome, .nome_normalizado, .formacao, .page_rank, .betweenness,
          .degree_centrality, .eigenvector, .closeness, .clustering_coeff,
          .community_id, .k_core} AS member,
       companies
"""

COUNT_MEMBERS = """
MATCH (p:Person)
WHERE $search IS NULL OR p.nome_normalizado CONTAINS toUpper($search)
RETURN count(p) AS total
"""

GET_MEMBER_BY_ID = """
MATCH (p:Person {id: $id})
OPTIONAL MATCH (p)-[r:MEMBER_OF]->(c:Company)
OPTIONAL MATCH (p)-[co:CO_MEMBER]-(neighbor:Person)
WITH p,
     collect(DISTINCT {cd_cvm: c.cd_cvm, nome: c.nome, cargo: r.cargo,
             ano_referencia: r.ano_referencia, data_eleicao: r.data_eleicao}) AS companies,
     collect(DISTINCT {id: neighbor.id, nome: neighbor.nome,
             page_rank: neighbor.page_rank}) AS connections
RETURN p {.id, .nome, .nome_normalizado, .formacao, .data_nascimento,
          .page_rank, .betweenness, .degree_centrality, .eigenvector,
          .closeness, .clustering_coeff, .community_id, .k_core} AS member,
       companies, connections
"""

GET_TOP_MEMBERS = """
MATCH (p:Person)
WHERE p[$metric] IS NOT NULL
RETURN p {.id, .nome, .page_rank, .betweenness, .degree_centrality,
          .eigenvector, .closeness, .community_id} AS member
ORDER BY p[$metric] DESC
LIMIT $limit
"""

# Company queries
GET_COMPANY_BOARD = """
MATCH (c:Company {cd_cvm: $cd_cvm})
OPTIONAL MATCH (p:Person)-[r:MEMBER_OF]->(c)
WITH c, collect({
  id: p.id, nome: p.nome, cargo: r.cargo,
  ano_referencia: r.ano_referencia, page_rank: p.page_rank
}) AS board_members
RETURN c {.cd_cvm, .cnpj, .nome, .setor, .segmento_listagem, .situacao} AS company,
       board_members
"""

GET_COMPANY_INTERLOCKING = """
MATCH (c:Company {cd_cvm: $cd_cvm})<-[:MEMBER_OF]-(p:Person)-[:MEMBER_OF]->(other:Company)
WHERE other.cd_cvm <> c.cd_cvm
WITH other, collect(DISTINCT p.nome) AS shared_members, count(DISTINCT p) AS shared_count
RETURN other {.cd_cvm, .nome, .setor} AS company,
       shared_members, shared_count
ORDER BY shared_count DESC
"""

# Metrics queries
GET_METRICS_OVERVIEW = """
MATCH (p:Person) WITH count(p) AS total_members
MATCH (c:Company) WITH total_members, count(c) AS total_companies
MATCH ()-[r:CO_MEMBER]-() WITH total_members, total_companies, count(r)/2 AS total_connections
MATCH (p:Person) WHERE p.community_id IS NOT NULL
WITH total_members, total_companies, total_connections,
     count(DISTINCT p.community_id) AS num_communities
OPTIONAL MATCH (p2:Person) WITH total_members, total_companies, total_connections,
     num_communities, avg(p2.degree_centrality) AS avg_degree
OPTIONAL MATCH (meta:NetworkMeta)
RETURN total_members, total_companies, total_connections, num_communities, avg_degree,
       meta.modularity AS modularity
"""

GET_CONCENTRATION_METRICS = """
MATCH (p:Person)
WHERE p.degree_centrality IS NOT NULL
WITH collect(p.degree_centrality) AS centralities
RETURN centralities
"""

# CO_MEMBER projection
PROJECT_CO_MEMBERS = """
MATCH (p1:Person)-[:MEMBER_OF]->(c:Company)<-[:MEMBER_OF]-(p2:Person)
WHERE p1.id < p2.id
  AND ($year IS NULL OR EXISTS {
    MATCH (p1)-[r1:MEMBER_OF]->(c) WHERE r1.ano_referencia = $year
  })
WITH p1, p2, count(DISTINCT c) AS weight, collect(DISTINCT c.cd_cvm) AS companies
MERGE (p1)-[co:CO_MEMBER]-(p2)
SET co.weight = weight
RETURN count(*) AS edges_created
"""

# Save metrics back to Neo4j
SAVE_PERSON_METRICS = """
UNWIND $batch AS row
MATCH (p:Person {id: row.id})
SET p.page_rank = row.page_rank,
    p.betweenness = row.betweenness,
    p.degree_centrality = row.degree_centrality,
    p.eigenvector = row.eigenvector,
    p.closeness = row.closeness,
    p.clustering_coeff = row.clustering_coeff,
    p.community_id = row.community_id,
    p.k_core = row.k_core
"""

SAVE_NETWORK_META = """
MERGE (meta:NetworkMeta)
SET meta.modularity = $modularity,
    meta.updated_at = datetime()
"""

# Temporal queries
GET_TEMPORAL_METRICS = """
MATCH (p:Person)-[r:MEMBER_OF]->(c:Company)
WHERE r.ano_referencia IS NOT NULL AND r.ano_referencia > 0
WITH r.ano_referencia AS year,
     count(DISTINCT p) AS members,
     count(DISTINCT c) AS companies,
     count(r) AS memberships
RETURN year, members, companies, memberships
ORDER BY year
"""
