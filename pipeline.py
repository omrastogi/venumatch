import json
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from prompts.intake import INTAKE_SYSTEM, INTAKE_USER

load_dotenv()

# SystemMessage keeps INTAKE_SYSTEM as a static string —
# prevents LangChain from parsing JSON schema braces as template variables
_intake_chain = (
    ChatPromptTemplate.from_messages([
        SystemMessage(content=INTAKE_SYSTEM),
        HumanMessagePromptTemplate.from_template(INTAKE_USER),
    ])
    | ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=os.getenv("OPENAI_API_KEY"))
    | JsonOutputParser()
)


def normalize_brief(brief: str) -> dict:
    """
    Run intake normalization LangChain chain on raw client brief.
    Returns structured profile dict with headcount, budget_per_person,
    neighborhood_pref, vibe_signals, hard_constraints, occasion.
    """
    return _intake_chain.invoke({"brief": brief})


def load_venues(path: str) -> tuple[list[dict], list[str]]:
    """
    Load venues from JSON and split into two representations:
    - structs: structured fields for hard filtering (no description)
    - texts:   semantic strings for embedding (specialty + description only)

    Returns (structs, texts) as parallel lists — same index = same venue.
    """
    with open(path, "r") as f:
        data = json.load(f)

    structs = []
    texts = []

    for i, venue in enumerate(data["venues"]):
        structs.append({
            "original_idx": i,
            "id": venue["id"],
            "name": venue["name"],
            "neighborhood": venue["neighborhood"],
            "capacity": venue["capacity"],
            "avg_cost_pp": venue["avg_cost_pp"],
            "specialty": venue["specialty"],
        })

        texts.append(f"{venue['specialty']}. {venue['description']}")

    return structs, texts


if __name__ == "__main__":
    structs, texts = load_venues("data/venues.json")

    print(f"Loaded {len(structs)} venues\n")

    for i in [0, 1]:
        print(f"--- Venue {i} struct ---")
        print(structs[i])
        print(f"--- Venue {i} text ---")
        print(texts[i])
        print()
