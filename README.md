# VenuMatch

AI-native venue matching pipeline — **filter first, embed second.**

Describe an event in plain English. VenuMatch extracts a structured profile, hard-filters 25 Boston venues against real constraints, runs semantic search on only the passing venues, and returns the top 3 matches with scores, rationale, and a client-ready recommendation.

---

## How it works

```
Client Brief (plain text)
        │
        ▼
  [Intake LLM]  ──  extracts: headcount, budget/pp, neighborhood,
        │             vibe_signals, occasion, hard_constraints
        │
        ├──▶  Hard Filter (Python)
        │         drop venues that fail capacity or budget
        │         if 0 pass → widen budget 20%, retry once
        │
        ├──▶  Semantic Search (ChromaDB)
        │         embed vibe_signals only
        │         query scoped to passing venue IDs
        │
        ▼
  [LLM Ranker]  ──  scores each candidate 0-10, writes rationale
        │
        ▼
  [LLM Explainer]  ──  one client-ready recommendation paragraph per venue
```

**Why vibe-only embedding?**
Budget and headcount numbers dominate token weight in raw briefs. Extracting "moody, intimate, hidden, speakeasy" and embedding that string gives the vector search a clean signal with no numeric noise.

**Why hard filter before any LLM call?**
Capacity and budget are binary — no partial credit. Filtering first in Python means no invalid venue ever consumes tokens or reaches the ranker.

**Why ChromaDB `where=` filter instead of post-filter?**
The query is scoped to passing IDs at the ANN index level. `k` results are drawn from passing venues only — not from the full corpus. At scale this prevents top-k from being filled by eliminated venues.

---

## Tech stack

| Layer | What |
|-------|------|
| LangChain | Intake, ranker, explainer chains (`ChatOpenAI`, `JsonOutputParser`, `StrOutputParser`) |
| ChromaDB | Persistent vectorstore, cosine space, filter-aware `where=` query |
| LangGraph | `StateGraph` orchestration, budget-widen conditional edge, `MemorySaver` |
| FastAPI | REST API — `/match`, `/refine`, `/venues`, `/health` |
| Streamlit | UI — venue cards, sidebar pipeline details, refinement loop |

---

## Setup

**Prerequisites:** conda, Python 3.10+, OpenAI API key

```bash
# 1. Clone
git clone https://github.com/omrastogi/venumatch.git
cd venumatch

# 2. Create environment
conda create -n struct_rag python=3.10
conda activate struct_rag

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set API key
echo "OPENAI_API_KEY=sk-..." > .env
```

---

## Running VenuMatch

### Option A — Full stack (API + UI)

```bash
bash start.sh
```

Opens both servers. Visit:

| | URL |
|-|-----|
| Streamlit UI | http://localhost:8501 |
| API | http://localhost:8000 |
| Interactive docs | http://localhost:8000/docs |

### Option B — API only

```bash
conda run -n struct_rag uvicorn api:app --port 8000 --reload
```

### Option C — CLI (no UI, no API)

```bash
# All 5 sample briefs via LangGraph
python main.py --mode graph

# Single brief
python main.py --mode graph --brief 1

# Phase 1 LangChain mode (no graph)
python main.py --mode chain
```

Output saved to `results/output_phase2_{mode}.json`.

---

## API reference

Base URL: `http://localhost:8000`

All request/response bodies are JSON. All errors return `{ "detail": "..." }`.

---

### `GET /health`

Check server status and venue count.

**Response**

```json
{
  "status": "ok",
  "venues_loaded": 25
}
```

---

### `GET /venues`

List all venues. Optionally filter by neighborhood.

**Query parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `neighborhood` | string | No | Filter to one neighborhood (e.g. `Seaport`, `Back Bay`) |

**Example**

```bash
curl http://localhost:8000/venues
curl "http://localhost:8000/venues?neighborhood=Seaport"
```

**Response** — array of venue objects

```json
[
  {
    "id": 1,
    "name": "Backbar",
    "neighborhood": "Downtown",
    "capacity": 40,
    "avg_cost_pp": 75,
    "specialty": "Craft cocktails, speakeasy atmosphere"
  }
]
```

---

### `POST /match`

Run the full pipeline for a client brief. Returns top 3 venue matches.

**Request body**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `brief` | string | Yes | Plain-text event description. Cannot be empty. |

**Example**

```bash
curl -X POST http://localhost:8000/match \
  -H "Content-Type: application/json" \
  -d '{"brief": "Birthday dinner for 25. Hidden gem, speakeasy vibe. Moody atmosphere. ~$2,000 total."}'
```

**Response**

```json
{
  "thread_id": "3f8a2c1d-...",
  "profile": {
    "occasion": "birthday",
    "headcount": 25,
    "budget_per_person": 80,
    "vibe_signals": "moody, intimate, hidden, speakeasy",
    "neighborhood_pref": [],
    "hard_constraints": []
  },
  "top3": [
    {
      "venue_id": 7,
      "venue_name": "Backbar",
      "score": 9.0,
      "rationale": "Speakeasy vibe and cozy atmosphere — hidden location and craft cocktails match the brief exactly."
    },
    {
      "venue_id": 12,
      "venue_name": "Haley.Henry",
      "score": 7.5,
      "rationale": "Low-key intimate natural wine bar — cozy vibe fits, though not a traditional speakeasy."
    },
    {
      "venue_id": 4,
      "venue_name": "Lolita Back Bay",
      "score": 6.5,
      "rationale": "Moody and creative, but cocktail lounge style may not fully capture the intimate exclusive feel."
    }
  ],
  "explanation": "**Backbar** is the standout choice here — tucked away in an alley off Downtown Crossing, it's exactly the kind of hidden gem that makes a birthday feel like a discovery...",
  "passing_count": 17,
  "budget_widened": false,
  "candidates": [
    { "id": 7, "name": "Backbar", "similarity_score": 0.82 },
    { "id": 12, "name": "Haley.Henry", "similarity_score": 0.76 }
  ]
}
```

**Response fields**

| Field | Description |
|-------|-------------|
| `thread_id` | Session ID. Pass to `/refine` to continue this search. |
| `profile` | Structured event profile extracted from the brief. |
| `top3` | Ranked venue matches. Each has `venue_id`, `venue_name`, `score` (0-10), `rationale`. |
| `explanation` | Client-facing recommendation text covering all 3 venues. |
| `passing_count` | Number of venues that passed the hard filter. |
| `budget_widened` | `true` if budget was relaxed 20% to find results. |
| `candidates` | All semantic search candidates with similarity scores (before LLM ranking). |

**Error responses**

| Status | When |
|--------|------|
| `422` | Brief is empty, or no venues pass constraints even after budget widening. |
| `500` | Pipeline error (LLM failure, etc.). |

---

### `POST /refine`

Refine results from an existing session. Updates the extracted profile with new preferences and re-runs the pipeline.

**Request body**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `thread_id` | string | Yes | Session ID from a prior `/match` or `/refine` call. |
| `refinement` | string | Yes | Plain-text refinement. E.g. `"I prefer South End"` or `"make it more casual"`. |

**Example**

```bash
curl -X POST http://localhost:8000/refine \
  -H "Content-Type: application/json" \
  -d '{
    "thread_id": "3f8a2c1d-...",
    "refinement": "Actually I prefer South End, and make it more casual"
  }'
```

**Response** — same shape as `/match` response, with updated `profile` and `top3`.

**Error responses**

| Status | When |
|--------|------|
| `404` | `thread_id` not found. Run `/match` first. |
| `422` | No venues pass constraints after refinement. |
| `500` | Pipeline error. |

---

## Multi-turn refinement flow

```
POST /match  →  { thread_id, top3, ... }
                       │
                       ▼
POST /refine  (thread_id + "prefer South End")  →  { updated top3, ... }
                       │
                       ▼
POST /refine  (thread_id + "more casual please")  →  { updated top3, ... }
```

The session persists the profile between calls. Each refinement patches only the fields mentioned — unspecified fields carry over from the previous run.

---

## File structure

```
venumatch/
├── api.py                        # FastAPI app — endpoints and Pydantic models
├── app.py                        # Streamlit UI
├── main.py                       # CLI entry point (--mode graph|chain --brief N)
├── start.sh                      # Launch API + UI together
├── requirements.txt
├── .env                          # API key — gitignored
│
├── pipeline.py                   # load_venues(), normalize_brief()
├── embedder.py                   # OpenAIEmbeddings wrapper
├── vectorstore.py                # ChromaDB build/load, semantic_search()
├── retriever.py                  # hard_filter()
├── ranker.py                     # llm_rank(), llm_explain()
│
├── graph/
│   ├── state.py                  # PipelineState TypedDict
│   ├── nodes.py                  # intake, filter, widen, retrieve, rank nodes
│   ├── pipeline_graph.py         # StateGraph, run_graph(), refine_brief()
│   └── memory.py                 # MemorySaver, _sessions, merge_refinement()
│
├── prompts/
│   ├── intake.py                 # Brief normalization prompts
│   ├── scorer.py                 # Ranker prompts
│   └── explainer.py              # Client-facing explanation prompts
│
└── data/
    ├── venues.json               # 25 Boston venues
    └── chroma_db/                # ChromaDB vectorstore (auto-built on first run)
```

---

## Models

| Step | Model | Temperature |
|------|-------|-------------|
| Intake — extract profile from brief | `gpt-4o-mini` | 0 |
| Refinement — merge new preferences | `gpt-4o-mini` | 0 |
| Ranker — score and rank candidates | `gpt-4o-mini` | 0 |
| Explainer — client recommendation | `gpt-4o-mini` | 0.4 |
| Embeddings | `text-embedding-3-small` | — |

---

## Cost estimate (5 briefs, full run)

| Step | Calls | Approx cost |
|------|-------|-------------|
| Venue embeddings (cached after first run) | 25 | ~$0.001 |
| Query embeddings | 5 | <$0.001 |
| Intake normalization | 5 | ~$0.01 |
| LLM ranking | 5 | ~$0.03 |
| LLM explanation | 5 | ~$0.03 |
| **Total** | | **< $0.10** |
