import json
import yaml
from pathlib import Path
from openai import AsyncOpenAI
from app.config import settings

PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"


def load_prompt(name: str) -> dict:
    with open(PROMPTS_DIR / name, "r") as f:
        return yaml.safe_load(f)


async def generate_learning_path(
    student_info: dict,
    assessment_data: dict | None,
    profile_data: dict | None,
) -> dict:
    """Generate a 12-week learning path from assessment + profile data.

    Args:
        student_info: dict with name, age, current_level, goals, problem_areas
        assessment_data: dict from assessments table (or None if no assessment)
        profile_data: dict from learner_profiles table (or None if no profile)

    Returns:
        dict with title, target_level, overview, weeks[], milestones[]
    """
    prompt_data = load_prompt("learning_path.yaml")
    misconceptions_data = load_prompt("polish_struggles.yaml")

    # Build assessment fields with fallbacks
    determined_level = student_info.get("current_level", "pending")
    confidence_score = "N/A"
    sub_skill_breakdown = "No assessment data available."
    weak_areas = "Not assessed."
    math_misconceptions = "No math misconceptions data available."

    if assessment_data:
        determined_level = assessment_data.get("determined_level") or determined_level
        confidence_score = assessment_data.get("confidence_score", "N/A")
        if assessment_data.get("sub_skill_breakdown"):
            sub_skill_breakdown = json.dumps(assessment_data["sub_skill_breakdown"], indent=2)
        if assessment_data.get("weak_areas"):
            weak_areas = ", ".join(assessment_data["weak_areas"])
        if assessment_data.get("ai_analysis") and isinstance(assessment_data["ai_analysis"], dict):
            misconceptions = assessment_data["ai_analysis"].get("math_misconceptions", [])
            if misconceptions:
                math_misconceptions = json.dumps(misconceptions, indent=2)

    if math_misconceptions == "No math misconceptions data available." and misconceptions_data:
        math_misconceptions = yaml.dump(misconceptions_data, default_flow_style=False, allow_unicode=True)

    # Build profile fields with fallbacks
    profile_summary = "No diagnostic profile available."
    priorities = "Not assessed."
    gaps = "Not assessed."

    if profile_data:
        profile_summary = profile_data.get("profile_summary") or profile_summary
        if profile_data.get("priorities"):
            priorities = ", ".join(profile_data["priorities"])
        if profile_data.get("gaps"):
            gaps = json.dumps(profile_data["gaps"], indent=2)

    user_message = prompt_data["user_template"].format(
        name=student_info.get("name", "Unknown"),
        age=student_info.get("age", "Not specified"),
        current_level=student_info.get("current_level", "pending"),
        goals=", ".join(student_info.get("goals", [])) or "Not specified",
        problem_areas=", ".join(student_info.get("problem_areas", [])) or "Not specified",
        determined_level=determined_level,
        confidence_score=confidence_score,
        sub_skill_breakdown=sub_skill_breakdown,
        weak_areas=weak_areas,
        profile_summary=profile_summary,
        priorities=priorities,
        gaps=gaps,
        math_misconceptions=math_misconceptions,
    )

    client = AsyncOpenAI(api_key=settings.api_key)

    response = await client.chat.completions.create(
        model=settings.model_name,
        messages=[
            {"role": "system", "content": prompt_data["system_prompt"]},
            {"role": "user", "content": user_message},
        ],
        temperature=0.5,
        response_format={"type": "json_object"},
    )

    result_text = response.choices[0].message.content
    return json.loads(result_text)
