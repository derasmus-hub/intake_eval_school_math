import json
import yaml
from pathlib import Path
from openai import AsyncOpenAI
from app.config import settings
from app.models.lesson import (
    LessonContent,
    Rozgrzewka,
    WyjasnienieTematu,
    PrzykladyRozwiazane,
    ZadaniaDoPraktyki,
    Podsumowanie,
)

PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"


def load_prompt(name: str) -> dict:
    with open(PROMPTS_DIR / name, "r") as f:
        return yaml.safe_load(f)


async def generate_lesson(
    student_id: int,
    profile: dict,
    progress_history: list[dict],
    session_number: int,
    current_level: str,
    previous_topics: list[str] | None = None,
    recall_weak_areas: list[str] | None = None,
) -> LessonContent:
    lesson_prompt = load_prompt("lesson_generator.yaml")

    system_prompt = lesson_prompt["system_prompt"]
    user_template = lesson_prompt["user_template"]

    progress_text = "No previous lessons." if not progress_history else json.dumps(progress_history, indent=2)
    topics_text = "None (first lesson)." if not previous_topics else ", ".join(previous_topics)

    recall_text = "None." if not recall_weak_areas else ", ".join(recall_weak_areas)

    user_message = user_template.format(
        session_number=session_number,
        current_level=current_level,
        profile_summary=profile.get("profile_summary", "No profile summary available"),
        priorities=", ".join(profile.get("priorities", [])),
        gaps=json.dumps(profile.get("gaps", []), indent=2),
        progress_history=progress_text,
        previous_topics=topics_text,
        recall_weak_areas=recall_text,
    )

    client = AsyncOpenAI(api_key=settings.api_key)

    response = await client.chat.completions.create(
        model=settings.model_name,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=0.7,
        response_format={"type": "json_object"},
    )

    result_text = response.choices[0].message.content
    result = json.loads(result_text)

    # Build 5-phase sub-models from AI response (if present)
    rozgrzewka = None
    if result.get("rozgrzewka"):
        rozgrzewka = Rozgrzewka(**result["rozgrzewka"])

    wyjasnienie_tematu = None
    if result.get("wyjasnienie_tematu"):
        wyjasnienie_tematu = WyjasnienieTematu(**result["wyjasnienie_tematu"])

    przyklady_rozwiazane = None
    if result.get("przyklady_rozwiazane"):
        przyklady_rozwiazane = PrzykladyRozwiazane(**result["przyklady_rozwiazane"])

    zadania_do_praktyki = None
    if result.get("zadania_do_praktyki"):
        zadania_do_praktyki = ZadaniaDoPraktyki(**result["zadania_do_praktyki"])

    podsumowanie = None
    if result.get("podsumowanie"):
        podsumowanie = Podsumowanie(**result["podsumowanie"])

    return LessonContent(
        objective=result.get("objective", ""),
        explanation=result.get("explanation", ""),
        exercises=result.get("exercises", []),
        practice_problems=result.get("practice_problems", []),
        key_formulas=result.get("key_formulas", []),
        difficulty=result.get("difficulty", current_level),
        math_domain=result.get("math_domain", ""),
        rozgrzewka=rozgrzewka,
        wyjasnienie_tematu=wyjasnienie_tematu,
        przyklady_rozwiazane=przyklady_rozwiazane,
        zadania_do_praktyki=zadania_do_praktyki,
        podsumowanie=podsumowanie,
    )
