# NeedYield

> Authentication phase: Supabase Auth supports Neighbor and Gardener signup/login when configured, with reliable browser-local demo accounts when it is not.

**Matching New York's yield with New York's need.**

NeedYield is an AI-powered produce redistribution concept connecting NYC gardeners, community food resources, and neighbors before fresh food goes to waste.

## Current demo

The current build includes a polished Neighbor experience, guided gardener workflow, optional Supabase accounts/persistence, a FastAPI backend, image analysis with Gemini-or-mock fallback, deterministic distribution matching, backend reservations, Rescue Mode, a Leaflet/OpenStreetMap map, and a grounded RAG food-resource assistant.

All locations and inventory in this phase are clearly identified as demo data. No organization shown is presented as a participating partner.

## Running locally

### Backend

Python 3.10+ is recommended.

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API runs at `http://127.0.0.1:8000`. Health check: `GET /api/health`.

## Deployment

The repository includes a Render Blueprint that deploys the FastAPI backend and React frontend as separate connected services. Create a new Render Blueprint from this repository and provide the requested Gemini, NYC Open Data, and Supabase environment values in the Render dashboard. The frontend API URL is populated from the backend service automatically. After deployment, set the deployed frontend URL as the Supabase Auth Site URL and add it to the allowed redirect URLs.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

For a production build:

```bash
cd frontend
npm run build
```

## Architecture

- React + TypeScript + Vite
- Plain responsive CSS
- Leaflet + OpenStreetMap map tiles
- Python + FastAPI + Pydantic
- Gemini multimodal analysis behind a server-side service, with a labeled mock fallback
- Deterministic, explainable matching separated from route handlers
- In-memory demo inventory, donations, and reservations behind service interfaces
- Backend-first frontend API client with local Phase 1 fallback when the API is unavailable
- Optional Supabase persistence behind a centralized server-side adapter
- LangChain `Document` ingestion, embeddings, persistent Chroma vector retrieval, structured verification, and grounded Gemini generation

## NYC Open Data

NeedYield queries the NYC Open Data dataset **Neighborhood Financial Health Digital Mapping and Data Tool** (`r3dx-pew9`), provided by the NYC Department of Consumer and Worker Protection.

Fields used:

- `borough`
- `neighborhoods`
- `nyc_poverty_rate`

The poverty rate is normalized to a 0–1 community-need factor and contributes 30% of the deterministic destination score. Results are cached for one hour. If the API is unavailable, labeled seeded fallback scores keep the demo working. These public-data signals provide neighborhood context only; they do not turn a public resource into a verified NeedYield partner.

## Matching

Only participating, verified demo partners that accept Saturday produce, accept the produce category, fall within the selected radius, and report a need are eligible. The preferred organization is allocated up to its explicit requested quantity first. Remaining surplus is scored using configurable community need, produce need, proximity, inventory shortage, and hours weights, then allocated within each location's capacity. Reasons are generated from those factors, not an LLM.

## Maps and directions

Find Food keeps the existing searchable location cards and adds a Leaflet map with OpenStreetMap tiles. Markers show current inventory, hours, neighborhood, optional Haversine distance, a reservation shortcut, and a Google Maps directions link. Browser location is optional; denial leaves neighborhood and borough discovery fully functional.

## Environment variables

Copy `backend/.env.example` to `backend/.env`:

```text
GEMINI_API_KEY=
NYC_OPEN_DATA_APP_TOKEN=
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
```

Without `GEMINI_API_KEY`, image analysis returns a clearly identified demo fallback result. No secret is sent to the browser.

## Supabase persistence

Supabase is optional. Without credentials, the API reports `"storage": "memory"` from `/api/health` and preserves the reliable in-memory demo. With `SUPABASE_URL` and the backend-only `SUPABASE_SERVICE_ROLE_KEY`, the centralized persistence adapter loads and saves locations, organization needs, inventory, reservations, donations, donation items, and allocations.

Run the three numbered migrations in `backend/supabase/migrations/` in order before adding credentials. They enable Row Level Security, automatic Neighbor/Gardener profiles, and transactionally safe user-owned reservations. See [backend/supabase/README.md](backend/supabase/README.md) for setup.

## RAG assistant

The assistant is a hybrid pipeline, not a general chatbot. Resource records become LangChain Documents with source metadata, are embedded once, and are stored in persistent Chroma. At query time, vector similarity retrieves the Top-K candidate records. NeedYield then verifies current structured inventory, hours, Saturday availability, and Haversine distance before any answer is generated. Gemini receives only retrieved context plus verified options. If Gemini is unavailable, a labeled deterministic grounded answer is returned; if Chroma fails, structured resource filtering remains available.

Rebuild the vector index whenever resource descriptions change:

```bash
cd backend
.venv/bin/python scripts/ingest_resources.py
```

Generated Chroma files in `backend/chroma_db/` are ignored by Git. The API endpoint is `POST /api/rag/query`.

## Testing

```bash
cd backend
.venv/bin/pytest -q
```

Tests cover Haversine distance, partner eligibility, matching order, preferred/surplus allocation, inventory decrement, Rescue Mode restoration, vector ingestion, retrieval, and structured inventory verification.

## Evaluation

The evaluation framework is under `evaluation/`. `vision_eval.py` calculates produce-label accuracy and quantity MAE from human-labeled cases. The repository intentionally contains no vision scores because no labeled harvest-image dataset has been collected yet.

`rag_eval.py` evaluates actual Chroma retrieval against labeled expected resource IDs and reports Hit Rate@1, Hit Rate@3, and Recall@3. The included five-question set is a small pipeline check over six demo records, not a claim of production-scale retrieval quality. See [evaluation/README.md](evaluation/README.md) for commands and interpretation.

Predictive ML remains intentionally deferred because the project does not yet have real historical outcomes.
