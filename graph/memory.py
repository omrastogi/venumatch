"""
Session memory for multi-turn refinement.
Uses LangGraph MemorySaver to persist state across calls per thread_id.
"""
import os
import uuid
from dotenv import load_dotenv
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI
from langchain_core.prompts import HumanMessagePromptTemplate
from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()

# Shared checkpointer — persists state in memory across calls
checkpointer = MemorySaver()

# Session store — tracks brief + profile per user session (thread_id → session dict)
# LangGraph checkpointer handles node-level state; this handles cross-run context
_sessions: dict[str, dict] = {}

# ── Refinement LLM chain ──────────────────────────────────────────────────────

_REFINE_SYSTEM = """You are updating an event profile based on a client refinement instruction.
Given the current profile and the client's new instruction, return ONLY valid JSON with
these keys updated as needed:

{
  "vibe_signals": "<updated vibe string, no numbers>",
  "neighborhood_pref": ["<list of neighborhoods if mentioned, else keep existing>"],
  "hard_constraints": ["<updated list>"],
  "budget_per_person": <number, only change if explicitly mentioned>,
  "headcount": <number, only change if explicitly mentioned>
}

Rules:
- Only change fields the refinement explicitly addresses
- Keep all other field values exactly as in the current profile
- vibe_signals must remain purely descriptive (no numbers)"""

_REFINE_USER = """Current profile:
{current_profile}

Client refinement: "{refinement}"

Return updated profile fields as JSON."""

_refine_chain = (
    ChatPromptTemplate.from_messages([
        SystemMessage(content=_REFINE_SYSTEM),
        HumanMessagePromptTemplate.from_template(_REFINE_USER),
    ])
    | ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=os.getenv("OPENAI_API_KEY"))
    | JsonOutputParser()
)


def merge_refinement(current_profile: dict, refinement: str) -> dict:
    """
    Use LLM to merge a refinement instruction into existing profile.
    Returns updated profile dict.
    """
    import json
    updates = _refine_chain.invoke({
        "current_profile": json.dumps(current_profile, indent=2),
        "refinement": refinement,
    })
    return {**current_profile, **updates}


# ── Session helpers ───────────────────────────────────────────────────────────

def new_thread_id() -> str:
    """Generate a unique session ID."""
    return str(uuid.uuid4())


def get_config(thread_id: str) -> dict:
    """Build LangGraph config dict for a given thread."""
    return {"configurable": {"thread_id": thread_id}}


def save_session(thread_id: str, raw_brief: str, profile: dict):
    """Persist session context after a graph run."""
    _sessions[thread_id] = {"raw_brief": raw_brief, "profile": profile}


def get_session(thread_id: str) -> dict:
    """Retrieve session context for refinement."""
    if thread_id not in _sessions:
        raise KeyError(f"No session found for thread_id={thread_id}")
    return _sessions[thread_id]


def get_session_state(graph, thread_id: str) -> dict:
    """Retrieve the latest LangGraph checkpoint state for a session."""
    config = get_config(thread_id)
    snapshot = graph.get_state(config)
    return snapshot.values if snapshot else {}
