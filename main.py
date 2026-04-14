import argparse
import json
import os

BRIEFS = {
    1: "Birthday dinner for 25 people. Hidden gem — not typical restaurant. Private room or speakeasy-style. Great food, moody atmosphere. ~$2,000 budget.",
    2: "Corporate team offsite for 40 people. Full-day format, AV needed, lunch included. Professional but not sterile. Seaport or Back Bay preferred.",
    3: "Bachelorette party for 20. Upscale but fun — rooftop or private bar section. Bottle service energy without club feeling. Somewhere worth posting.",
    4: "Graduation dinner for 25, family from out of town. Special occasion. Nice food, cozy, not loud. I want parents to feel I planned something thoughtful.",
    5: "Tech startup networking event, 60 people, cocktail-style standing room. Feels creative and modern — not hotel ballroom. Budget flexible, want good value.",
}


# ── Graph mode (Phase 2 default) ──────────────────────────────────────────────

def run_graph_mode(brief_ids: list[int]) -> dict:
    from graph.pipeline_graph import run_graph

    results = {}
    for bid in brief_ids:
        brief = BRIEFS[bid]
        print(f"\n{'='*60}")
        print(f"BRIEF {bid:02d} [graph]: {brief[:75]}...")
        print("="*60)

        state, thread_id = run_graph(brief)

        print(f"  Headcount: {state['profile']['headcount']} | "
              f"Budget/pp: ${state['profile']['budget_per_person']} | "
              f"Vibe: {state['profile']['vibe_signals']}")
        print(f"  Hard filter: 25 -> {len(state['passing'])} passing")
        print(f"  Candidates: {[v['name'] for v in state['candidates']]}")
        print(f"  Budget widened: {state['budget_widened']}")
        print(f"  Top-3:")
        for v in state["top3"]:
            print(f"    [{v['score']}] {v['venue_name']} -- {v['rationale'][:75]}...")

        results[f"brief_{bid:02d}"] = {
            "mode": "graph",
            "thread_id": thread_id,
            "brief_id": bid,
            "raw_brief": brief,
            "profile": state["profile"],
            "passing_count": len(state["passing"]),
            "budget_widened": state["budget_widened"],
            "candidates": [
                {"id": v["id"], "name": v["name"], "similarity_score": v["similarity_score"]}
                for v in state["candidates"]
            ],
            "top3": state["top3"],
            "explanation": state["explanation"],
        }

    return results


# ── Chain mode (Phase 1 pipeline) ─────────────────────────────────────────────

def run_chain_mode(brief_ids: list[int]) -> dict:
    from pipeline import load_venues, normalize_brief
    from retriever import hard_filter
    from vectorstore import load_or_build_vectorstore, semantic_search
    from ranker import llm_rank, llm_explain

    structs, texts = load_venues("data/venues.json")
    collection = load_or_build_vectorstore(structs, texts, "data/chroma_db")

    results = {}
    for bid in brief_ids:
        brief = BRIEFS[bid]
        print(f"\n{'='*60}")
        print(f"BRIEF {bid:02d} [chain]: {brief[:75]}...")
        print("="*60)

        profile = normalize_brief(brief)
        passing = hard_filter(structs, profile)
        passing_ids = [v["id"] for v in passing]
        candidates = semantic_search(collection, profile["vibe_signals"], passing_ids, k=5)
        top3 = llm_rank(candidates, profile)
        explanation = llm_explain(top3, brief, structs)

        print(f"  Headcount: {profile['headcount']} | Budget/pp: ${profile['budget_per_person']}")
        print(f"  Hard filter: 25 -> {len(passing)} passing")
        print(f"  Top-3: {[v['venue_name'] for v in top3]}")

        results[f"brief_{bid:02d}"] = {
            "mode": "chain",
            "brief_id": bid,
            "raw_brief": brief,
            "profile": profile,
            "passing_count": len(passing),
            "candidates": [
                {"id": v["id"], "name": v["name"], "similarity_score": v["similarity_score"]}
                for v in candidates
            ],
            "top3": top3,
            "explanation": explanation,
        }

    return results


# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="VenuMatch pipeline")
    parser.add_argument("--brief", type=int, choices=[1, 2, 3, 4, 5],
                        help="Run a single brief (1-5). Default: all.")
    parser.add_argument("--mode", choices=["graph", "chain"], default="graph",
                        help="graph = LangGraph (default) | chain = Phase 1 LangChain")
    args = parser.parse_args()

    brief_ids = [args.brief] if args.brief else [1, 2, 3, 4, 5]
    output_path = f"results/output_phase2_{args.mode}.json"

    print(f"Mode: {args.mode.upper()} | Briefs: {brief_ids}")

    if args.mode == "graph":
        results = run_graph_mode(brief_ids)
    else:
        results = run_chain_mode(brief_ids)

    os.makedirs("results", exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {output_path}")


if __name__ == "__main__":
    main()
