from typing import TypedDict


class PipelineState(TypedDict):
    # Input
    raw_brief: str

    # Stage 1 — intake normalization
    profile: dict

    # Stage 2 — hard filter
    passing: list[dict]

    # Stage 3 — semantic search
    candidates: list[dict]

    # Stage 4 — LLM rank
    top3: list[dict]

    # Stage 5 — LLM explain
    explanation: str

    # Control flow
    budget_widened: bool   # prevents infinite retry loop
    error: str             # set if pipeline cannot recover
