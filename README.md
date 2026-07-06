---
title: Bharat Tech Atlas
emoji: 🗺️
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 7860
suggested_hardware: cpu-basic
tags:
- ml-intern
---

# Bharat Tech Atlas v3.3

Mapping platform for India's startup ecosystem — curated dataset of startups, SMEs, college E-Cells, incubators, and accelerators. Now with **ML-powered insights**, **ETL data pipelines**, **MLOps monitoring**, and **security hardening**.

> **Data disclaimer**: This is a curated subset. India has 223,000+ DPIIT-registered startups (as of April 2026). Stats shown here reflect only what's in our database. Sources: DPIIT, Tracxn, Crunchbase, LinkedIn.

## What's New in v3.3

- **Security hardening**: Centralized `security.py` with XSS detection, prompt injection scanning (27 patterns), URL validation (SSRF prevention), audit logging, rate limiting, CSP generation
- **Input validation**: Stricter bounds on coordinates, funding amounts, years, startup names, query lengths
- **Frontend security**: Removed `dangerouslySetInnerHTML` from social icons, added `SafeSocialIcon` React component, URL validation on all social links
- **Chat safety**: Prompt injection detection rejects DAN/jailbreak attempts, output sanitization strips scripts
- **Audit logging**: Every request gets a `request_id`, security events logged with severity levels
- **CORS tightened**: Configurable origins, limited methods (`GET/POST/HEAD/OPTIONS`)
- **Security headers**: `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `X-Request-ID`, HSTS + CSP in production
- **Rate limits**: Chat/Agent = 30 req/min per IP, General API = 120/min
- **Query timeouts**: 10s PRAGMA busy_timeout on all entity queries
- **Tests**: 15 security tests added (injection, XSS, CORS, rate limits, coordinate validation)

## What's New in v3.2

- **Chat AI fix**: 🤖 button now functional — keyword-based responses work instantly, LLM mode auto-loads when transformers available
- **Search Agent**: Web search for startup analysis (gracefully degrades when duckduckgo-search not installed)
- **ML keyword fallback**: All ML endpoints work without GPU/transformers — sector classification via keyword rules
- **Bug fixes**: Fixed double-execution middleware, DB connection pool, missing router mounts, dead enrichment code
- **Schema migrations**: Auto-migrate DB schema on startup, seed guard for faster restarts

## What's New in v3.0

- **ML Inference API**: NLP sector classification + startup growth prediction
- **ETL Pipeline**: Automated Extract → Transform → Load from DPIIT, Tracxn, Crunchbase
- **MLOps Monitoring**: Data drift detection, model health tracking, CI/CD pipelines
- **Model Serving**: ONNX-optimized inference, caching, TorchServe/Triton-ready
- **125 Unicorns**: Full Indian unicorn dataset with funding & investors

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React + MapLibre)                    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐             │
│  │  Map UI  │ │ Sidebar  │ │ Analytics│ │  Search    │             │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └─────┬──────┘             │
│       │             │            │              │                     │
│       └─────────────┴────────────┴──────────────┘                    │
│                         Async API Calls (Fetch)                       │
└──────────────────────────────────┬──────────────────────────────────┘
                                   │
┌──────────────────────────────────▼──────────────────────────────────┐
│                      BACKEND (FastAPI + Uvicorn)                      │
│                                                                       │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐      │
│  │  /api/entities  │  │    /api/ml      │  │   /api/mlops    │      │
│  │  GeoJSON, CRUD  │  │  Classification │  │  Drift, Monitor │      │
│  │  Clusters, Fmt  │  │  Growth Predict │  │  Model Registry │      │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘      │
│           │                     │                     │               │
│  ┌────────▼─────────────────────▼─────────────────────▼────────┐     │
│  │              DATABASE LAYER (SQLite + R-Tree)                 │     │
│  │   Spatial indexing · WAL mode · Optimized queries             │     │
│  └──────────────────────────────────────────────────────────────┘     │
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐     │
│  │                    ETL PIPELINE                                │     │
│  │   DPIIT API → ┐                                              │     │
│  │   Tracxn API → ├→ Transform (geocode, normalize) → Load DB   │     │
│  │   Crunchbase → ┘                                              │     │
│  └──────────────────────────────────────────────────────────────┘     │
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐     │
│  │                    ML MODEL SERVER                             │     │
│  │   Sector Classifier (BART/ONNX) + Growth Predictor (GBT)     │     │
│  │   LRU Cache · Batch Inference · Health Monitoring             │     │
│  └──────────────────────────────────────────────────────────────┘     │
└───────────────────────────────────────────────────────────────────────┘
```

---

## 1. Data Pipelines & API Architecture

### ETL Pipeline (`backend/etl/`)

| Stage | Module | Description |
|-------|--------|-------------|
| **Extract** | `extract.py` | Async API callers for DPIIT, Tracxn, Crunchbase with rate limiting |
| **Transform** | `transform.py` | Geocoding, sector normalization, deduplication, slug generation |
| **Load** | `load.py` | Batch upserts to SQLite, R-Tree spatial index maintenance |
| **Orchestrator** | `pipeline.py` | Full/incremental runs, scheduling, error recovery |

### API Endpoints — ETL Management

- `GET /api/etl/status` — Pipeline status + DB stats
- `POST /api/etl/run` — Trigger full ETL pipeline
- `POST /api/etl/run/incremental?since_hours=24` — Incremental update
- `GET /api/etl/history` — Pipeline run history
- `GET /api/etl/sources` — Configured data sources info

### Data Flow

```
DPIIT Portal ──┐
Tracxn API ────┼──→ ETLExtractor (async, rate-limited)
Crunchbase ────┘         │
                         ▼
                  ETLTransformer
                  - Clean names (remove Pvt/Ltd/Inc)
                  - Normalize sectors → standard taxonomy
                  - Geocode addresses → lat/lng
                  - Deduplicate across sources
                         │
                         ▼
                    ETLLoader
                  - Batch INSERT/UPDATE
                  - R-Tree spatial index
                  - Stale record deactivation
```

---

## 2. Backend Frameworks & ML APIs

### FastAPI Backend (Production-Grade)

- **Async request handling** — concurrent ML inference without blocking
- **Rate limiting** — 60 req/min general, 10 req/min for ML endpoints
- **Input sanitization** — SQL injection prevention, query length limits
- **Auto-generated docs** — Swagger UI at `/docs`

### ML API Endpoints (`/api/ml/`)

- `GET /api/ml/classify/sector?description=...&top_k=3` — NLP sector classification
- `POST /api/ml/classify/sector/batch` — Batch classification (up to 50)
- `GET /api/ml/predict/growth/{slug}` — Growth prediction for an entity
- `GET /api/ml/predict/growth?sector=fintech&state=Karnataka` — Ranked predictions
- `GET /api/ml/health` — Model server health
- `GET /api/ml/sectors/taxonomy` — Full sector taxonomy

---

## 3. Pre-Existing Models & Serving

### Sector Classifier (`backend/ml/classifier.py`)

| Mode | Model | Latency | Accuracy |
|------|-------|---------|----------|
| Zero-shot | `facebook/bart-large-mnli` | ~200ms | ~85% |
| ONNX | Exported BART | ~50ms | ~85% |
| Keyword fallback | Rule-based | ~1ms | ~70% |

### Growth Predictor (`backend/ml/predictor.py`)

Features used:
- **Funding signal** — log-normalized funding amount
- **Team signal** — log-normalized employee count
- **Sector momentum** — market trend score (AI=0.95, EdTech=0.65)
- **Ecosystem score** — city startup density (Bengaluru=0.95)
- **Age signal** — sweet spot 2-7 years
- **Recognition signals** — DPIIT, NSA, unicorn status
- **Investor quality** — presence of top-tier VCs

### Model Serving (`backend/ml/serving.py`)

Production-ready serving with:
- **LRU Response Cache** — avoid redundant inference
- **Batch processing** — group requests for GPU efficiency
- **TorchServe adapter** — for PyTorch model deployment at scale
- **NVIDIA Triton adapter** — multi-model, dynamic batching
- **ONNX Runtime** — 3-5x speedup on CPU

---

## 4. MLOps & Agile Integration

### MLOps Module (`backend/mlops/`)

| Component | Description |
|-----------|-------------|
| **Data Drift Detection** | PSI (categorical) + KS-test (numerical) |
| **Model Monitor** | Latency, errors, confidence tracking, auto-alerts |
| **Model Registry** | Version control, A/B comparison, promotion |
| **CI/CD Pipeline** | GitHub Actions workflow (test → validate → train → deploy) |

### MLOps API Endpoints (`/api/mlops/`)

- `GET /api/mlops/drift/check` — Run drift detection on current data
- `GET /api/mlops/drift/history` — Historical drift reports
- `GET /api/mlops/monitor/metrics` — Real-time model metrics
- `GET /api/mlops/monitor/alerts` — Recent alerts (latency, degradation)
- `GET /api/mlops/registry/models` — All model versions
- `GET /api/mlops/registry/compare?model=...&v1=...&v2=...` — Version diff
- `GET /api/mlops/cicd/workflow` — GitHub Actions YAML
- `POST /api/mlops/cicd/trigger-retrain` — Manual retraining trigger

### Agile Sprint Structure

| Sprint | Deliverable | Status |
|--------|-------------|--------|
| Sprint 1 | Basic map UI + FastAPI backend + static data | ✅ Done |
| Sprint 2 | ETL pipeline (DPIIT/Tracxn/Crunchbase) + real data | ✅ Done |
| Sprint 3 | ML models (sector classifier + growth predictor) | ✅ Done |
| Sprint 4 | MLOps (drift detection, monitoring, CI/CD) | ✅ Done |
| Sprint 5 | Security hardening, XSS prevention, audit logging, rate limiting | ✅ Done |
| Sprint 6 | Scale: ONNX optimization, GPU serving, load testing | 🔜 Next |

### CI/CD Pipeline

```yaml
# Triggered on: push to backend/ml/**, scheduled weekly
test → data-validation → train → validate-performance → deploy
```

- **DVC** for data version control
- **GitHub Actions** for automated pipeline
- **HuggingFace Hub** for model storage
- **Prometheus/Grafana** compatible metrics

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + Vite + MapLibre GL JS + Tailwind CSS |
| Backend | FastAPI + slowapi rate limiting |
| Database | SQLite with R-Tree spatial index |
| ML Inference | HuggingFace Transformers + ONNX Runtime |
| ETL | Async Python (aiohttp) + custom pipeline |
| MLOps | Data drift (PSI/KS) + Model registry + CI/CD |
| Map Tiles | CARTO Dark Matter |
| Deployment | Docker on Hugging Face Spaces |

---

## Map Features

### Map Modes
- **Clusters** (default): Server-side numbered bubble clusters at low zoom
- **Points**: All entities as colored dots
- **Heatmap**: Funding-weighted density visualization

### Filtering
- Entity types, sectors, DPIIT categories, business models, stage, location
- Special filters: unicorns, women-led, rural impact, campus startups, NSA winners
- State filter with fly-to

---

## Data

Curated dataset across India:
- **125 Unicorns**: Flipkart, PhonePe, Zerodha, Zomato, Swiggy, CRED, Zepto, Neysa + more
- **Women-led startups**: Nykaa, Mamaearth, Sugar Cosmetics, OPEN Financial + more
- **Rural impact**: DeHaat, CropIn, Stellapps, Aye Finance + more
- **Campus startups**: Pixxel, TartanSense, Zepto + more
- **NSA winners**: Tagged with award categories
- **DPIIT recognized**: Government-recognized startups

---

## Quick Start (Local Development)

```bash
# Backend
pip install -r requirements.txt
uvicorn backend.main:app --reload --port 7860

# Frontend (separate terminal)
cd frontend && npm install && npm run dev

# Run ETL pipeline
python -c "import asyncio; from backend.etl import ETLPipeline; asyncio.run(ETLPipeline({}).run())"

# Test ML classification
curl "http://localhost:7860/api/ml/classify/sector?description=AI-powered%20fraud%20detection%20for%20banks"

# Check data drift
curl "http://localhost:7860/api/mlops/drift/check"

# Run tests
pytest tests/test_api.py -v
```
