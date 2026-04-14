def hard_filter(structs: list[dict], profile: dict) -> list[dict]:
    """
    Stage 1 retrieval: eliminate venues that fail hard constraints.
    Filters on capacity, budget, and optionally neighborhood.
    Returns subset of structs with original_idx intact.
    """
    passing = []

    for venue in structs:
        # Capacity: venue must fit the group
        if venue["capacity"] < profile["headcount"]:
            continue

        # Budget: venue must be within per-person budget
        if venue["avg_cost_pp"] > profile["budget_per_person"]:
            continue

        # Neighborhood: soft preference — only filter if explicitly stated
        if profile["neighborhood_pref"]:
            if venue["neighborhood"] not in profile["neighborhood_pref"]:
                continue

        passing.append(venue)

    return passing
