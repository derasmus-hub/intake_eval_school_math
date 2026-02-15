from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class Rozgrzewka(BaseModel):
    """Warm-up: mental math drill or quick review."""
    description: str = ""
    activity: str = ""
    duration_minutes: int = 5
    materials: Optional[list[str]] = None


class WyjasnienieTematu(BaseModel):
    """Topic explanation with theory and definitions."""
    topic: str = ""
    explanation: str = ""
    definitions: list[str] = []
    examples: list[str] = []
    visual_aid: Optional[str] = None


class PrzykladyRozwiazane(BaseModel):
    """Step-by-step worked examples."""
    exercises: list[dict] = []
    instructions: str = ""
    instructions_pl: Optional[str] = None


class ZadaniaDoPraktyki(BaseModel):
    """Independent practice problems with progressive hints."""
    problems: list[dict] = []
    description: str = ""
    hints: list[str] = []
    success_criteria: Optional[str] = None


class Podsumowanie(BaseModel):
    """Wrap-up: summary, key formulas, homework."""
    summary: str = ""
    key_formulas: list[str] = []
    homework: Optional[str] = None
    next_preview: Optional[str] = None


class LessonContent(BaseModel):
    objective: str = ""
    explanation: str = ""
    exercises: list[dict] = []
    practice_problems: list[str] = []
    key_formulas: list[str] = []
    difficulty: str = ""
    math_domain: str = ""
    # 5-phase structure
    rozgrzewka: Optional[Rozgrzewka] = None
    wyjasnienie_tematu: Optional[WyjasnienieTematu] = None
    przyklady_rozwiazane: Optional[PrzykladyRozwiazane] = None
    zadania_do_praktyki: Optional[ZadaniaDoPraktyki] = None
    podsumowanie: Optional[Podsumowanie] = None


class LessonResponse(BaseModel):
    id: int
    student_id: int
    session_number: int
    objective: Optional[str] = None
    content: Optional[LessonContent] = None
    difficulty: Optional[str] = None
    math_domain: Optional[str] = None
    status: str = "generated"
    created_at: Optional[str] = None


class ProgressEntry(BaseModel):
    lesson_id: int
    student_id: int
    score: float
    notes: Optional[str] = None
    areas_improved: list[str] = []
    areas_struggling: list[str] = []


class ProgressResponse(BaseModel):
    id: int
    student_id: int
    lesson_id: int
    score: float
    notes: Optional[str] = None
    areas_improved: list[str] = []
    areas_struggling: list[str] = []
    completed_at: Optional[str] = None


class ProgressSummary(BaseModel):
    student_id: int
    total_lessons: int = 0
    average_score: float = 0.0
    entries: list[ProgressResponse] = []
    skill_averages: dict[str, float] = {}
