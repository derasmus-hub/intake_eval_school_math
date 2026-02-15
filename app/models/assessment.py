from pydantic import BaseModel
from typing import Optional
from enum import Enum


class Bracket(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class QuestionType(str, Enum):
    PLACEMENT = "placement"
    ARITHMETIC = "arithmetic"
    ALGEBRA = "algebra"
    GEOMETRY = "geometry"
    TRIGONOMETRY = "trigonometry"
    CALCULUS = "calculus"
    STATISTICS = "statistics"
    LOGIC = "logic"


class PlacementQuestion(BaseModel):
    id: int
    problem: str  # math problem statement
    correct_answer: str
    difficulty: int  # 1-5
    math_domain: str
    explanation: str


class DiagnosticQuestion(BaseModel):
    id: str
    type: QuestionType
    bracket: Bracket
    question: str
    options: Optional[list[str]] = None
    correct_answer: str
    skill: str  # "arytmetyka", "algebra", "geometria", etc.
    topic: str  # e.g. "ulamki", "rownania_liniowe"
    hint: Optional[str] = None


class PlacementAnswer(BaseModel):
    question_id: int
    answer: str


class DiagnosticAnswer(BaseModel):
    question_id: str
    answer: str


class StartAssessmentRequest(BaseModel):
    student_id: int


class PlacementSubmission(BaseModel):
    student_id: int
    assessment_id: int
    answers: list[PlacementAnswer]


class DiagnosticSubmission(BaseModel):
    student_id: int
    assessment_id: int
    answers: list[DiagnosticAnswer]


class PlacementResult(BaseModel):
    bracket: Bracket
    score: int
    detail: str


class SubSkillScore(BaseModel):
    skill: str
    score: float
    level: str
    details: str


class AssessmentResultResponse(BaseModel):
    id: int
    student_id: int
    stage: str
    bracket: Optional[str] = None
    determined_level: Optional[str] = None
    confidence_score: Optional[float] = None
    sub_skill_breakdown: Optional[list[SubSkillScore]] = None
    weak_areas: Optional[list[str]] = None
    ai_analysis: Optional[dict] = None
    status: str
    created_at: Optional[str] = None
