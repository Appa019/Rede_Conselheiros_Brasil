# Rede de Conselheiros CVM

Plataforma de análise de redes sociais (SNA) dos conselheiros de empresas abertas brasileiras, usando dados públicos da CVM. Combina análise de grafos, métricas de concentração de poder, predição de links e dashboard interativo.

## Arquitetura

| Camada | Stack | Diretório |
|--------|-------|-----------|
| Backend | Python 3.12 / FastAPI | `backend/` |
| Frontend | Next.js 16 / TypeScript / Tailwind v4 | `frontend/` |
| Graph DB | Neo4j 5 (local: docker-compose, prod: AuraDB free tier) | - |
| Vector Store | Pinecone (embeddings para similarity search) | - |
| Visualização | Sigma.js + graphology (WebGL) | - |
| ML | Node2Vec + scikit-learn (Random Forest) | - |
| Graph Metrics | NetworKit (C++ parallel) + NetworkX | - |

## Comandos Essenciais

### Setup inicial
```bash
# Neo4j local
docker compose up -d

# Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload  # http://localhost:8000

# Frontend
cd frontend
pnpm install
pnpm dev  # http://localhost:3000
```

### Pipeline de dados
```bash
cd backend

# 1. ETL: download CVM → parse → clean → load Neo4j
python scripts/run_etl.py --years 2024 --verbose
python scripts/run_etl.py --years 2021 2022 2023 2024 2025 --verbose  # todos

# 2. Métricas: NetworKit (C++ parallel) → salva no Neo4j
python scripts/compute_metrics.py --verbose

# 3. ML: Node2Vec embeddings + link prediction
python scripts/train_model.py --skip-pinecone --verbose
```

### Pipeline via frontend (admin)
O dashboard tem botões "Atualizar Dados" e "Treinar Modelo" que chamam os endpoints admin.
- Atualizar Dados: `POST /admin/etl` → auto-trigger `POST /admin/compute-metrics` ao completar
- Treinar Modelo: `POST /admin/train` (skip_pinecone=True)
- Ambos com progress bar em tempo real (polling 2s) e exibição de resultados
- Job IDs persistidos em `localStorage` (`admin_active_jobs`) — sobrevive a navegação entre páginas
- `useAdminWorkflow()` hook central gerencia todo o fluxo (trigger, polling, auto-metrics, cache invalidation)

### Verificação
```bash
# Frontend
cd frontend && pnpm build  # verifica build completo
npx tsc --noEmit            # type check sem build

# Backend
cd backend && ruff check .  # lint Python
python -m pytest tests/test_api_smoke.py -v         # API endpoints (requer Neo4j com dados)
python -m pytest tests/test_etl_smoke.py -v -m smoke # ETL (requer rede)
python -m pytest tests/test_metrics_smoke.py -v      # métricas (requer Neo4j com dados)
python -m pytest tests/test_ml_smoke.py -v           # ML (requer Neo4j com dados)
python -m pytest -v                                  # suite completa
python -m pytest -m "not slow" -v                    # apenas smoke (sem full pipeline)
```

## Estrutura do Projeto

```
backend/
├── app/
│   ├── main.py              # FastAPI app, CORS, health check
│   ├── config.py             # pydantic-settings (lê .env)
│   ├── dependencies.py       # lifespan Neo4j + get_neo4j dependency
│   ├── etl/
│   │   ├── downloader.py     # httpx async download ZIPs CVM
│   │   ├── extractor.py      # unzip + parse CSVs (sep=";", encoding fallback)
│   │   ├── cleaner.py        # unidecode normalize, dedup, cargo mapping
│   │   ├── loader.py         # batch MERGE Cypher no Neo4j
│   │   └── orchestrator.py   # pipeline completo
│   ├── graph/
│   │   ├── neo4j_client.py   # async driver wrapper
│   │   ├── queries.py        # Cypher query templates
│   │   └── metrics.py        # NetworKit (C++ parallel): centrality, Louvain, Gini, HHI, advanced (assortativity, resilience, etc.)
│   ├── ml/
│   │   ├── embeddings.py     # Node2Vec (128d)
│   │   ├── pinecone_client.py
│   │   ├── link_prediction.py # Random Forest
│   │   └── train.py          # pipeline ML completo
│   ├── routers/               # graph, members, companies, metrics, temporal, predictions, admin
│   └── schemas/common.py     # 30+ Pydantic models (incl. AdvancedMetrics, DegreeDistribution, JobStatus, etc.)
├── scripts/                   # run_etl.py, compute_metrics.py, train_model.py
├── tests/
│   ├── conftest.py            # fixtures: neo4j_client, api_client, networkx_graph (session-scoped)
│   ├── test_api_smoke.py      # 12 testes de endpoints HTTP (schema validation via Pydantic)
│   ├── test_etl_smoke.py      # 7 testes de ETL (download, parse, clean — tolerante a CVM offline)
│   ├── test_metrics_smoke.py  # 6 testes de métricas (centrality, communities, advanced)
│   └── test_ml_smoke.py       # 3 testes de ML (embeddings, link prediction, full pipeline)
├── pytest.ini                 # asyncio_mode=auto, session loop scope
└── requirements.txt

frontend/
├── src/
│   ├── app/                   # Next.js App Router (8 páginas)
│   ├── components/
│   │   ├── graph/             # NetworkGraph (Sigma.js), Controls, Tooltip
│   │   ├── dashboard/         # MetricCard, TopConnected, ConcentrationIndex, AdminActions
│   │   ├── charts/            # TimelineChart, BarChart (SVG puro)
│   │   ├── filters/           # GraphFilters (ano, setor, conexões)
│   │   ├── icons/             # CvmLogo (SVG inline, verde institucional)
│   │   └── layout/            # Sidebar (com CvmLogo), Header
│   ├── hooks/                 # useGraph, useMembers, useMetrics, useCompanies, useTemporal, useAdmin
│   ├── lib/                   # api.ts (apiFetch + apiPost wrappers), query-client.tsx
│   └── types/index.ts
└── package.json
```

## API Endpoints

### Core
- `GET /api/health` — status + conectividade Neo4j
- `GET /api/graph/network?year=&sector=&min_connections=&limit=` — grafo filtrado
- `GET /api/graph/subgraph/{person_id}` — ego network
- `GET /api/graph/communities` — comunidades Louvain
- `GET /api/members?search=&page=&page_size=` — lista paginada
- `GET /api/members/top?metric=page_rank&limit=10` — ranking
- `GET /api/members/{id}` — perfil completo
- `GET /api/companies/{cd_cvm}/board` — composição do board
- `GET /api/companies/{cd_cvm}/network` — interlocking directorates

### Analytics
- `GET /api/metrics/overview` — total nodes/edges/density/communities
- `GET /api/metrics/concentration` — Gini, HHI, interlocking index
- `GET /api/metrics/advanced` — assortativity, transitivity, small-world sigma, diameter, rich-club
- `GET /api/metrics/distribution` — degree distribution stats + power-law fit (alpha, xmin, p-value)
- `GET /api/metrics/sector-interlocking` — cross-sector interlocking matrix (shared board members)
- `GET /api/metrics/centrality-correlation` — Spearman rho entre centralidades (degree, betweenness, closeness, eigenvector, pagerank)
- `GET /api/metrics/resilience` — targeted node removal analysis (1%, 2%, 5%, 10%)
- `GET /api/temporal/evolution` — métricas por ano
- `GET /api/predictions/links` — conexões previstas
- `GET /api/predictions/similar/{id}` — membros similares (Pinecone)

### Admin (background tasks)
- `POST /api/admin/etl` — lança ETL pipeline (download CVM → parse → clean → load Neo4j)
- `POST /api/admin/compute-metrics` — lança computação de métricas (NetworKit C++ parallel → Neo4j)
- `POST /api/admin/train` — lança pipeline ML (Node2Vec + link prediction, skip_pinecone=True)
- `GET /api/admin/jobs/{job_id}` — poll status de um job (progress, message, result)
- `GET /api/admin/jobs` — lista últimos 20 jobs

> Jobs usam `asyncio.create_task` com store in-memory (dict). Apenas 1 job por tipo pode rodar simultaneamente (409 Conflict). O frontend faz polling a cada 2s via `useJobStatus` e auto-trigger de compute-metrics após ETL. Job IDs são persistidos em localStorage para sobreviver a navegação.

## Modelo de Dados Neo4j

### Nodes
- **Person** — `id` (sha256 12 hex), `nome`, `nome_normalizado`, `data_nascimento`, `formacao`, métricas pré-computadas
- **Company** — `cd_cvm`, `cnpj`, `nome`, `setor`, `segmento_listagem`, `situacao`
- **Sector** — `nome`

### Relationships
- `(Person)-[:MEMBER_OF {cargo, tipo_orgao, data_eleicao, mandato_fim, ano_referencia}]->(Company)`
- `(Person)-[:CO_MEMBER {weight}]->(Person)` — projeção bipartida
- `(Person)-[:SHAREHOLDER_OF {percentual_ordinarias, percentual_total}]->(Company)`
- `(Company)-[:BELONGS_TO]->(Sector)`

## Convenções de Código

### Python (backend)
- async/await em todo I/O (Neo4j, httpx)
- Type hints obrigatórios
- Logging via `logging` (nunca print)
- Lint: `ruff check .`
- Batch size padrão: 500 registros
- Cache in-memory do grafo NetworkX em `metrics.py` com TTL 5min (`get_cached_graph()` / `invalidate_graph_cache()`)
- **NetworKit** para centralidades pesadas (betweenness, closeness, eigenvector, pagerank) — C++ paralelo, ~53x mais rápido que NetworkX puro
- NetworkX mantido para: advanced metrics (assortativity, small-world), resilience, Louvain (via python-louvain), e como formato de grafo principal
- Conversão NX→NK via `_nx_to_nk()` helper em `metrics.py` (mapeia string IDs ↔ int IDs)
- scipy usado para stats (skew, spearmanr, kstest) nas métricas avançadas
- ML progress callbacks granulares: `on_progress(pct, msg)` em embeddings.py e link_prediction.py
- **Node2Vec otimizado**: 80 walks × 20 length (era 200×30), 8 workers — qualidade similar, ~3.7x menos walks
- **Link prediction features em batch**: `_batch_link_features()` chama cada predictor NetworkX (jaccard, adamic_adar, pref_attachment, resource_alloc) uma vez com todos os pares, ~5-10x mais rápido que loop individual
- `compute_link_features()` removido — substituído por `_batch_link_features()` vetorizado

### TypeScript (frontend)
- Named exports para componentes e hooks
- Default export apenas para pages (exigência App Router)
- React Query para data fetching (staleTime: 60s)
- Tailwind v4 com `@theme` para custom tokens em `globals.css`
- Fontes: Space Grotesk (headings, `--font-heading`), Inter (body, `--font-body`), JetBrains Mono (mono, `--font-mono`)
- Ícones: lucide-react
- Sem gradientes — design flat, minimal, profissional
- **Light mode** — fundo branco, sem dark mode
- **Cores CVM**: accent `#1B5E4B` (verde institucional), warm `#F2A900` (dourado institucional)
- **Zero bordas arredondadas** — nenhum `rounded-lg`, `rounded-md`, `rounded-xl` (exceção: `rounded-full` em progress bars finas e status dots)
- Sem Framer Motion — transições via CSS `transition-colors` apenas
- Hover states: `hover:bg-[var(--color-surface-alt)]` (nunca `hover:bg-white/[0.04]`)
- Cards: `bg-[var(--color-surface)] border border-[var(--color-border)]` — sem rounded
- Inputs: `bg-white border border-[var(--color-border)]` — sem rounded
- Buttons primários: `bg-[var(--color-accent)] text-white` — sem rounded
- State que precisa sobreviver a navegação: persistir em `localStorage` e restaurar no mount (ex: `useAdminWorkflow`)
- Flags de controle em effects: usar `useRef` para evitar deps instáveis e re-execuções
- API `/graph/network` retorna `{ nodes, total }` sem `edges` — frontend faz fallback `edges ?? []`

### Dados CVM
- CSV separator: `;` (ponto e vírgula)
- Encoding fallback: latin-1 → cp1252 → utf-8-sig
- Person ID: `hashlib.sha256(nome_normalizado + data_nascimento)[:12]`
- Nome normalizado: `unidecode(nome).upper().strip()` + collapse whitespace
- Cargos padronizados via `CARGO_MAP` em `cleaner.py`
- Dados variam entre anos — schema detection para colunas

### Git
- Commits atômicos, formato Conventional Commits (feat:, fix:, chore:, refactor:)
- Commits em inglês
- Nunca hardcodar secrets — usar `.env` + `.env.example`
- Verificar build (`pnpm build` / `ruff check`) antes de commitar

## Variáveis de Ambiente

```env
# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=conselheiros2024

# Pinecone (opcional — ML features)
PINECONE_API_KEY=
PINECONE_INDEX_NAME=conselheiros-embeddings

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000/api

# Backend
CORS_ORIGINS=["http://localhost:3000"]
```

## Deploy

| Serviço | Plataforma | Config |
|---------|-----------|--------|
| Frontend | Vercel | `output: "standalone"` em next.config.ts |
| Backend | Railway ou Render | Dockerfile / Procfile |
| Neo4j | AuraDB free tier | ~25-40k nodes (cabe) |
| Pinecone | Free tier | Index: `conselheiros-embeddings` |
| CI/CD | GitHub Actions | `.github/workflows/etl-cron.yml` (mensal) |

## Limites e Cuidados

- AuraDB free: 50k nodes — estimativa do projeto: ~9k pessoas + 600 empresas + edges ≈ 25-40k
- Sigma.js: limitar a top 500 nodes por PageRank para performance
- Dedup sem CPF: usa nome normalizado + data_nascimento (pode gerar falsos em homônimos raros)
- Node2Vec: requer grafo conectado; nós isolados ficam sem embedding
