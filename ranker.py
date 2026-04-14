import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from prompts.scorer import RANKER_SYSTEM, RANKER_USER, format_candidates
from prompts.explainer import EXPLAINER_SYSTEM, EXPLAINER_USER, format_top3_for_explainer

load_dotenv()

_llm_precise = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    api_key=os.getenv("OPENAI_API_KEY"),
)
_llm_warm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.4,
    api_key=os.getenv("OPENAI_API_KEY"),
)

# SystemMessage prevents JSON schema braces being parsed as template variables
_rank_chain = (
    ChatPromptTemplate.from_messages([
        SystemMessage(content=RANKER_SYSTEM),
        HumanMessagePromptTemplate.from_template(RANKER_USER),
    ])
    | _llm_precise
    | JsonOutputParser()
)

_explain_chain = (
    ChatPromptTemplate.from_messages([
        SystemMessage(content=EXPLAINER_SYSTEM),
        HumanMessagePromptTemplate.from_template(EXPLAINER_USER),
    ])
    | _llm_warm
    | StrOutputParser()
)


def llm_rank(candidates: list[dict], profile: dict) -> list[dict]:
    """
    LangChain chain re-ranks semantic candidates, returns top 3 with scores and rationale.
    """
    raw = _rank_chain.invoke({
        "occasion": profile["occasion"],
        "headcount": profile["headcount"],
        "budget_per_person": profile["budget_per_person"],
        "vibe_signals": profile["vibe_signals"],
        "hard_constraints": ", ".join(profile["hard_constraints"]) or "none",
        "neighborhood_pref": ", ".join(profile["neighborhood_pref"]) or "none",
        "candidates_block": format_candidates(candidates),
    })

    # Handle both {"results": [...]} and bare [...] responses
    if isinstance(raw, list):
        return raw[:3]
    for key in raw:
        if isinstance(raw[key], list):
            return raw[key][:3]
    return raw


def llm_explain(top3: list[dict], raw_brief: str, structs: list[dict]) -> str:
    """
    LangChain chain generates client-facing recommendation for top 3 venues.
    """
    return _explain_chain.invoke({
        "raw_brief": raw_brief,
        "venues_block": format_top3_for_explainer(top3, structs),
    })
