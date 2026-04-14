from langgraph.graph import StateGraph, START, END
from graph.state import PipelineState
from graph.nodes import (
    intake_node, filter_node, retrieve_node,
    rank_node, explain_node, widen_budget_node,
)
from graph.memory import (
    checkpointer, merge_refinement, get_config, new_thread_id,
    save_session, get_session,
)


# ── Routing ───────────────────────────────────────────────────────────────────

def route_after_filter(state: PipelineState) -> str:
    if len(state["passing"]) > 0:
        return "retrieve"
    if not state["budget_widened"]:
        return "widen_budget"
    return "end"


# ── Build graph ───────────────────────────────────────────────────────────────

def build_graph():
    builder = StateGraph(PipelineState)

    builder.add_node("intake", intake_node)
    builder.add_node("filter", filter_node)
    builder.add_node("widen_budget", widen_budget_node)
    builder.add_node("retrieve", retrieve_node)
    builder.add_node("rank", rank_node)
    builder.add_node("explain", explain_node)

    builder.add_edge(START, "intake")
    builder.add_edge("intake", "filter")
    builder.add_conditional_edges(
        "filter",
        route_after_filter,
        {"retrieve": "retrieve", "widen_budget": "widen_budget", "end": END},
    )
    builder.add_edge("widen_budget", "filter")
    builder.add_edge("retrieve", "rank")
    builder.add_edge("rank", "explain")
    builder.add_edge("explain", END)

    return builder.compile(checkpointer=checkpointer)


graph = build_graph()


# ── Public interface ──────────────────────────────────────────────────────────

def run_graph(brief: str, thread_id: str = None) -> tuple[PipelineState, str]:
    """
    Run full pipeline for a brief.
    Returns (final_state, thread_id) — thread_id can be passed to refine_brief().
    """
    if thread_id is None:
        thread_id = new_thread_id()

    initial_state: PipelineState = {
        "raw_brief": brief,
        "profile": {},
        "passing": [],
        "candidates": [],
        "top3": [],
        "explanation": "",
        "budget_widened": False,
        "error": "",
    }

    state = graph.invoke(initial_state, config=get_config(thread_id))
    save_session(thread_id, brief, state["profile"])
    return state, thread_id


def refine_brief(thread_id: str, refinement: str) -> PipelineState:
    """
    Refine results for an existing session.
    Retrieves session context from our store, merges refinement into profile,
    then runs a fresh LangGraph thread (avoids checkpoint conflicts on completed runs).
    intake_node detects pre-set profile and skips the LLM call.
    """
    session = get_session(thread_id)
    current_profile = session["profile"]
    raw_brief = session["raw_brief"]

    print(f"  [refine] '{refinement}'")
    print(f"  [refine] vibe before: {current_profile['vibe_signals']}")

    updated_profile = merge_refinement(current_profile, refinement)
    print(f"  [refine] vibe after:  {updated_profile['vibe_signals']}")

    # Fresh LangGraph thread per refinement — avoids MemorySaver checkpoint conflicts
    fresh_tid = new_thread_id()
    refined_state: PipelineState = {
        "raw_brief": raw_brief,
        "profile": updated_profile,   # pre-set: intake_node skips LLM call
        "passing": [],
        "candidates": [],
        "top3": [],
        "explanation": "",
        "budget_widened": False,
        "error": "",
    }

    result = graph.invoke(refined_state, config=get_config(fresh_tid))
    # Update session store with latest profile for next refinement
    save_session(thread_id, raw_brief, result["profile"])
    return result
