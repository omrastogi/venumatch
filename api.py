from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator

from pipeline import load_venues
from graph.pipeline_graph import run_graph, refine_brief


# ── Startup: load venues once ─────────────────────────────────────────────────

_structs: list[dict] = []

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _structs
    structs, texts = load_venues("data/venues.json")
    _structs = structs
    # Warm up vectorstore on startup
    from vectorstore import load_or_build_vectorstore
    load_or_build_vectorstore(structs, texts, "data/chroma_db")
    print(f"[startup] {len(_structs)} venues loaded, vectorstore ready")
    yield


app = FastAPI(
    title="VenuMatch",
    description="AI-native venue matching — filter first, embed second.",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Pydantic models ───────────────────────────────────────────────────────────

class MatchRequest(BaseModel):
    brief: str
    thread_id: Optional[str] = None

    @field_validator("brief")
    @classmethod
    def brief_not_empty(cls, v):
        if not v.strip():
            raise ValueError("brief cannot be empty")
        return v.strip()


class VenueResult(BaseModel):
    venue_id: int
    venue_name: str
    score: float
    rationale: str


class MatchResponse(BaseModel):
    thread_id: str
    profile: dict
    top3: list[VenueResult]
    explanation: str
    passing_count: int
    budget_widened: bool
    candidates: list[dict]


class RefineRequest(BaseModel):
    thread_id: str
    refinement: str

    @field_validator("refinement")
    @classmethod
    def refinement_not_empty(cls, v):
        if not v.strip():
            raise ValueError("refinement cannot be empty")
        return v.strip()


class VenueOut(BaseModel):
    id: int
    name: str
    neighborhood: str
    capacity: int
    avg_cost_pp: int
    specialty: str


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "venues_loaded": len(_structs)}


@app.get("/venues", response_model=list[VenueOut])
def list_venues(neighborhood: Optional[str] = Query(None)):
    """List all venues. Optional ?neighborhood= filter."""
    venues = _structs
    if neighborhood:
        venues = [v for v in venues if v["neighborhood"].lower() == neighborhood.lower()]
    return venues


@app.post("/match", response_model=MatchResponse)
def match(req: MatchRequest):
    """Run full pipeline for a brief. Returns top 3 venues + explanation."""
    try:
        state, thread_id = run_graph(req.brief, req.thread_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if not state.get("top3"):
        raise HTTPException(
            status_code=422,
            detail="No venues found matching constraints. Try relaxing budget or removing neighborhood filter."
        )

    return MatchResponse(
        thread_id=thread_id,
        profile=state["profile"],
        top3=[VenueResult(**v) for v in state["top3"]],
        explanation=state["explanation"],
        passing_count=len(state["passing"]),
        budget_widened=state["budget_widened"],
        candidates=[
            {"id": v["id"], "name": v["name"], "similarity_score": v["similarity_score"]}
            for v in state["candidates"]
        ],
    )


@app.post("/refine", response_model=MatchResponse)
def refine(req: RefineRequest):
    """Refine results for an existing session using thread_id."""
    try:
        state = refine_brief(req.thread_id, req.refinement)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Session {req.thread_id} not found. Run /match first.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if not state.get("top3"):
        raise HTTPException(
            status_code=422,
            detail="No venues found after refinement. Try relaxing constraints."
        )

    return MatchResponse(
        thread_id=req.thread_id,
        profile=state["profile"],
        top3=[VenueResult(**v) for v in state["top3"]],
        explanation=state["explanation"],
        passing_count=len(state["passing"]),
        budget_widened=state["budget_widened"],
        candidates=[
            {"id": v["id"], "name": v["name"], "similarity_score": v["similarity_score"]}
            for v in state["candidates"]
        ],
    )
