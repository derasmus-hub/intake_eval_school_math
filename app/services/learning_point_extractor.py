import json
import yaml
from pathlib import Path
from openai import AsyncOpenAI
from app.config import settings

PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"


def load_prompt(name: str) -> dict:
    with open(PROMPTS_DIR / name, "r") as f:
        return yaml.safe_load(f)


async def extract_learning_points(lesson_content: dict, student_level: str) -> list[dict]:
    prompt = load_prompt("extract_learning_points.yaml")

    system_prompt = prompt["system_prompt"]
    user_template = prompt["user_template"]

    # Build presentation text
    presentation_text = ""
    if lesson_content.get("wyjasnienie_tematu"):
        p = lesson_content["wyjasnienie_tematu"]
        if isinstance(p, dict):
            presentation_text = f"Topic: {p.get('topic', '')}\n"
            presentation_text += f"Explanation: {p.get('explanation', '')}\n"
            definitions = p.get("definitions", [])
            if definitions:
                presentation_text += "Definitions: " + "; ".join(definitions) + "\n"
            examples = p.get("examples", [])
            if examples:
                presentation_text += "Examples: " + "; ".join(examples)

    # Build exercises text
    exercises_text = ""
    exercises = lesson_content.get("exercises", [])
    if not exercises and lesson_content.get("przyklady_rozwiazane"):
        cp = lesson_content["przyklady_rozwiazane"]
        if isinstance(cp, dict):
            exercises = cp.get("exercises", [])
    if exercises:
        exercises_text = "Exercises:\n"
        for i, ex in enumerate(exercises, 1):
            if isinstance(ex, dict):
                exercises_text += f"  {i}. [{ex.get('type', '')}] {ex.get('instruction', '')} — {ex.get('content', '')} (Answer: {ex.get('answer', '')})\n"

    # Build practice text
    practice_text = ""
    problems = lesson_content.get("practice_problems", [])
    if problems:
        practice_text = "Practice Problems: " + "; ".join(problems)
    if lesson_content.get("zadania_do_praktyki"):
        fp = lesson_content["zadania_do_praktyki"]
        if isinstance(fp, dict):
            practice_text += f"\nIndependent Practice: {fp.get('description', '')}"

    # Build key formulas text
    formulas = lesson_content.get("key_formulas", [])
    if formulas:
        practice_text += "\nKey Formulas: " + "; ".join(formulas)

    user_message = user_template.format(
        student_level=student_level,
        objective=lesson_content.get("objective", ""),
        presentation_text=presentation_text or "No presentation data.",
        exercises_text=exercises_text or "No exercises data.",
        practice_text=practice_text or "No practice data.",
    )

    client = AsyncOpenAI(api_key=settings.api_key)

    response = await client.chat.completions.create(
        model=settings.model_name,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=0.3,
        response_format={"type": "json_object"},
    )

    result = json.loads(response.choices[0].message.content)
    return result.get("learning_points", [])
