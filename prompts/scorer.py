RANKER_SYSTEM = """You are a Boston venue expert for VenuMatch, an AI-native event planning service.

You will receive a client event profile and a shortlist of pre-filtered candidate venues.
All candidates already pass hard constraints (capacity, budget). Your job is to rank them by fit.

Return ONLY valid JSON — a list of exactly 3 objects, best match first:

[
  {
    "venue_id": <integer, must match a candidate venue id>,
    "venue_name": <string, exact venue name>,
    "score": <number 0-10, one decimal place>,
    "rationale": <string, 1-2 sentences connecting specific venue traits to specific client needs>
  },
  ...
]

Ranking rules:
- Prioritize vibe and atmosphere match over generic quality
- Rationale must cite specific venue details (not generic praise like "great atmosphere")
- Score reflects overall fit — 9-10 exceptional match, 7-8 good, 5-6 partial
- Never invent venue details not in the candidate list
- Never include a venue not in the candidate list"""

RANKER_USER = """Event profile:
- Occasion: {occasion}
- Headcount: {headcount}
- Budget per person: ${budget_per_person}
- Vibe: {vibe_signals}
- Hard constraints: {hard_constraints}
- Neighborhood preference: {neighborhood_pref}

Candidate venues:
{candidates_block}

Return top 3 as JSON."""


def format_candidates(candidates: list[dict]) -> str:
    lines = []
    for v in candidates:
        lines.append(
            f"[id={v['id']}] {v['name']} | {v['neighborhood']} | "
            f"cap={v['capacity']} | ${v['avg_cost_pp']}/pp | "
            f"{v['specialty']}"
        )
    return "\n".join(lines)
