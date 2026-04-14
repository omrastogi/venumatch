"""
Graph nodes for the LangGraph pipeline.
Each node receives PipelineState, returns a partial state dict with updated fields.
Resources (structs, collection) are initialized once and shared across all nodes.
"""
from pipeline import load_venues, normalize_brief
from retriever import hard_filter
from vectorstore import load_or_build_vectorstore, semantic_search
from ranker import llm_rank, llm_explain
from graph.state import PipelineState

# ── Shared resources ─────────────────────────────────────────────────────────
# Loaded once on import, reused across all node calls

_structs, _texts = load_venues("data/venues.json")
_collection = load_or_build_vectorstore(_structs, _texts, "data/chroma_db")


def get_structs():
    return _structs


# ── Nodes ─────────────────────────────────────────────────────────────────────

def intake_node(state: PipelineState) -> dict:
    """Extract structured profile from raw brief via LangChain intake chain.
    Skips LLM call if profile already populated (refinement mode).
    """
    if state.get("profile") and state["profile"].get("headcount"):
        print("  [intake] profile pre-set, skipping LLM call (refinement mode)")
        return {}
    profile = normalize_brief(state["raw_brief"])
    return {"profile": profile}


def filter_node(state: PipelineState) -> dict:
    """Hard filter venues on capacity and budget. Pure Python, no LLM."""
    passing = hard_filter(_structs, state["profile"])
    return {"passing": passing}


def retrieve_node(state: PipelineState) -> dict:
    """Semantic search on passing venues only via ChromaDB."""
    passing_ids = [v["id"] for v in state["passing"]]
    candidates = semantic_search(
        _collection,
        state["profile"]["vibe_signals"],
        passing_ids,
        k=5,
    )
    return {"candidates": candidates}


def rank_node(state: PipelineState) -> dict:
    """LLM re-ranks candidates and returns top 3 with scores and rationale."""
    top3 = llm_rank(state["candidates"], state["profile"])
    return {"top3": top3}


def explain_node(state: PipelineState) -> dict:
    """LLM generates client-facing recommendation for top 3 venues."""
    explanation = llm_explain(state["top3"], state["raw_brief"], _structs)
    return {"explanation": explanation}


def widen_budget_node(state: PipelineState) -> dict:
    """
    Increase budget_per_person by 20% and set budget_widened flag.
    Fires when hard filter returns zero passing venues.
    Flag prevents infinite retry loop.
    """
    profile = dict(state["profile"])
    original = profile["budget_per_person"]
    profile["budget_per_person"] = round(original * 1.2)
    print(f"  [widen_budget] ${original} -> ${profile['budget_per_person']}/pp")
    return {"profile": profile, "budget_widened": True}
