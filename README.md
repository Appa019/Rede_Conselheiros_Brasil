# Rede de Conselheiros CVM

Plataforma de análise de redes sociais (SNA) dos conselheiros de empresas abertas brasileiras, usando dados públicos da CVM. Combina análise de grafos, métricas de concentração de poder, predição de links e dashboard interativo.

## Arquitetura

| Camada | Stack |
|--------|-------|
| Backend | Python 3.12 / FastAPI |
| Frontend | Next.js 16 / TypeScript / Tailwind v4 |
| Graph DB | Neo4j 5 (local: Docker, prod: AuraDB) |
| Visualização | Sigma.js + graphology (WebGL) |
| ML | Node2Vec + scikit-learn (Random Forest) |
| Graph Metrics | NetworKit (C++ paralelo) + NetworkX |

## Pré-requisitos

- Python 3.12+
- Node.js 20+ e pnpm
- Docker e Docker Compose

## Setup

### 1. Neo4j local

```bash
# Copiar e configurar variáveis de ambiente
cp backend/.env.example backend/.env
# Editar backend/.env com senha e URI do Neo4j

# Subir Neo4j via Docker
docker compose up -d
```

### 2. Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
# API disponível em http://localhost:8000
```

### 3. Frontend

```bash
cd frontend
pnpm install
pnpm dev
# Interface disponível em http://localhost:3000
```

## Pipeline de Dados

```bash
cd backend && source venv/bin/activate

# 1. ETL: download CVM → parse → clean → carga Neo4j
python scripts/run_etl.py --years 2024 --verbose

# 2. Métricas: NetworKit (C++ paralelo) → salva no Neo4j
python scripts/compute_metrics.py --verbose

# 3. ML: Node2Vec embeddings + link prediction
python scripts/train_model.py --skip-pinecone --verbose
```

O dashboard admin também expõe esses pipelines com progress bar em tempo real.

## Verificação

```bash
# Backend
cd backend
ruff check .
python -m pytest tests/test_etl_smoke.py -v -m smoke   # smoke ETL (sem Neo4j)
python -m pytest -v                                     # suite completa

# Frontend
cd frontend
pnpm build        # verifica build completo
npx tsc --noEmit  # type check
```

## Variáveis de Ambiente

Copiar `backend/.env.example` para `backend/.env` e preencher:

| Variável | Descrição |
|----------|-----------|
| `NEO4J_URI` | URI de conexão Neo4j (ex: `bolt://localhost:7687`) |
| `NEO4J_USER` | Usuário Neo4j (padrão: `neo4j`) |
| `NEO4J_PASSWORD` | Senha Neo4j (obrigatório) |
| `CORS_ORIGINS` | Lista JSON de origens permitidas |
| `NEXT_PUBLIC_API_URL` | URL da API (frontend) |

Para `docker-compose.yml` local, definir `NEO4J_AUTH` no ambiente:

```bash
export NEO4J_AUTH=neo4j/suasenha
docker compose up -d
```

## Deploy

| Serviço | Plataforma |
|---------|-----------|
| Frontend | Vercel |
| Backend | Railway ou Render |
| Neo4j | AuraDB free tier |
| CI/CD | GitHub Actions (cron mensal) |

## Estrutura

```
backend/          # FastAPI + ETL + Graph + ML
frontend/         # Next.js + Sigma.js + TanStack Query
docker-compose.yml
.github/workflows/etl-cron.yml
```

## Dados

Fonte: [CVM — Formulário de Referência](https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/FRE/DADOS/)

Cobertura: empresas abertas brasileiras, anos 2021–2025.
