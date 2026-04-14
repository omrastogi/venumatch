import requests
import pandas as pd
import streamlit as st

API_BASE = "http://localhost:8000"

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="VenuMatch",
    page_icon="🎯",
    layout="wide",
)

# ── Session state init ────────────────────────────────────────────────────────

if "thread_id" not in st.session_state:
    st.session_state.thread_id = None
if "result" not in st.session_state:
    st.session_state.result = None
if "history" not in st.session_state:
    st.session_state.history = []  # list of (action, top3 names)

# ── Header ────────────────────────────────────────────────────────────────────

st.title("VenuMatch")
st.caption("Describe the event. Get the right venue.")
st.divider()

# ── Sidebar — pipeline internals ──────────────────────────────────────────────

with st.sidebar:
    st.header("Pipeline Details")

    if st.session_state.result:
        r = st.session_state.result
        profile = r["profile"]

        st.subheader("Extracted Profile")
        st.markdown(f"**Occasion:** {profile.get('occasion', '—')}")
        st.markdown(f"**Headcount:** {profile.get('headcount', '—')}")
        st.markdown(f"**Budget/pp:** ${profile.get('budget_per_person', '—')}")
        st.markdown(f"**Neighborhood:** {', '.join(profile.get('neighborhood_pref', [])) or 'Any'}")
        st.markdown(f"**Vibe:** _{profile.get('vibe_signals', '—')}_")
        if profile.get("hard_constraints"):
            st.markdown(f"**Constraints:** {', '.join(profile['hard_constraints'])}")

        st.divider()

        st.subheader("Hard Filter")
        passing = r["passing_count"]
        st.metric("Venues passing filter", passing, delta=f"{25 - passing} eliminated")
        if r["budget_widened"]:
            st.warning("Budget was widened by 20% to find results.")

        st.divider()

        st.subheader("Semantic Candidates")
        if r.get("candidates"):
            df = pd.DataFrame(r["candidates"])[["name", "similarity_score"]]
            df = df.rename(columns={"name": "Venue", "similarity_score": "Score"})
            df = df.sort_values("Score", ascending=True)
            st.bar_chart(df.set_index("Venue")["Score"], height=200)

        st.divider()

        st.subheader("Session")
        st.code(st.session_state.thread_id[:16] + "..." if st.session_state.thread_id else "—")

        if st.session_state.history:
            st.subheader("Refinement History")
            for i, (action, names) in enumerate(st.session_state.history):
                st.markdown(f"**{i+1}.** _{action}_")
                st.caption(" → ".join(names))
    else:
        st.info("Run a search to see pipeline details here.")

# ── Main layout ───────────────────────────────────────────────────────────────

col_input, col_results = st.columns([1, 1], gap="large")

with col_input:
    st.subheader("Describe your event")

    brief = st.text_area(
        label="Client brief",
        placeholder=(
            "e.g. Birthday dinner for 25 people. Hidden gem — not typical restaurant. "
            "Private room or speakeasy-style. Great food, moody atmosphere. ~$2,000 budget."
        ),
        height=160,
        label_visibility="collapsed",
    )

    find_clicked = st.button("Find Venues", type="primary", use_container_width=True)

    # Example briefs
    with st.expander("Load an example brief"):
        examples = {
            "Birthday (speakeasy)": "Birthday dinner for 25 people. Hidden gem — not typical restaurant. Private room or speakeasy-style. Great food, moody atmosphere. ~$2,000 budget.",
            "Corporate offsite": "Corporate team offsite for 40 people. Full-day format, AV needed, lunch included. Professional but not sterile. Seaport or Back Bay preferred.",
            "Bachelorette party": "Bachelorette party for 20. Upscale but fun — rooftop or private bar section. Bottle service energy without club feeling. Somewhere worth posting.",
            "Graduation dinner": "Graduation dinner for 25, family from out of town. Special occasion. Nice food, cozy, not loud. I want parents to feel I planned something thoughtful.",
            "Startup networking": "Tech startup networking event, 60 people, cocktail-style standing room. Feels creative and modern — not hotel ballroom. Budget flexible, want good value.",
        }
        for label, text in examples.items():
            if st.button(label, use_container_width=True):
                st.session_state["_load_brief"] = text
                st.rerun()

    # Load example brief if button was clicked
    if "_load_brief" in st.session_state:
        brief = st.session_state.pop("_load_brief")

    # Refinement box — only shown after first result
    if st.session_state.result:
        st.divider()
        st.subheader("Refine your search")
        refinement = st.text_input(
            "What would you like to change?",
            placeholder="e.g. I prefer South End, or make it more casual",
        )
        refine_clicked = st.button("Refine", use_container_width=True)

        if refine_clicked and refinement.strip():
            with st.spinner("Refining..."):
                resp = requests.post(f"{API_BASE}/refine", json={
                    "thread_id": st.session_state.thread_id,
                    "refinement": refinement,
                })
            if resp.status_code == 200:
                st.session_state.result = resp.json()
                st.session_state.history.append(
                    (refinement, [v["venue_name"] for v in st.session_state.result["top3"]])
                )
                st.rerun()
            elif resp.status_code == 422:
                st.error("No venues found after refinement. Try relaxing your constraints.")
            else:
                st.error(f"Error: {resp.json().get('detail', 'Unknown error')}")

# ── Search trigger ────────────────────────────────────────────────────────────

if find_clicked:
    if not brief.strip():
        st.error("Please describe your event before searching.")
    else:
        with st.spinner("Finding venues..."):
            resp = requests.post(f"{API_BASE}/match", json={"brief": brief})

        if resp.status_code == 200:
            st.session_state.result = resp.json()
            st.session_state.thread_id = resp.json()["thread_id"]
            st.session_state.history = [("Initial search", [v["venue_name"] for v in resp.json()["top3"]])]
            st.rerun()
        elif resp.status_code == 422:
            st.error("No venues found for your brief. Try relaxing budget or removing neighborhood preference.")
        else:
            st.error(f"API error: {resp.text[:200]}")

# ── Results ───────────────────────────────────────────────────────────────────

with col_results:
    if st.session_state.result:
        r = st.session_state.result
        st.subheader("Top Venues")

        # Venue cards
        for i, venue in enumerate(r["top3"]):
            medal = ["🥇", "🥈", "🥉"][i] if i < 3 else f"{i+1}."
            with st.container(border=True):
                col_name, col_score = st.columns([3, 1])
                with col_name:
                    st.markdown(f"### {medal} {venue['venue_name']}")
                with col_score:
                    st.metric("Match", f"{venue['score']}/10")
                st.markdown(venue["rationale"])

        st.divider()

        # Full explanation
        with st.expander("Full recommendation", expanded=True):
            st.markdown(r["explanation"])
    else:
        st.info("Your venue matches will appear here.")
