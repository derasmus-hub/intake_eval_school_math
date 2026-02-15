from pydantic import BaseModel
from typing import Optional
from enum import Enum
from datetime import datetime


class MathLevel(str, Enum):
    PODSTAWOWY = "podstawowy"
    GIMNAZJALNY = "gimnazjalny"
    LICEALNY = "licealny"
    LICEALNY_ROZSZERZONY = "licealny_rozszerzony"
    ZAAWANSOWANY = "zaawansowany"


class StudentIntake(BaseModel):
    name: str
    age: Optional[int] = None
    current_level: Optional[MathLevel] = None
    goals: list[str] = []
    problem_areas: list[str] = []
    exam_target: Optional[str] = None  # e.g. "matura_podstawowa", "matura_rozszerzona", "egzamin_osmoklasisty"
    filler: str = "student"  # student / teacher / parent
    additional_notes: Optional[str] = None


class StudentResponse(BaseModel):
    id: int
    name: str
    age: Optional[int] = None
    current_level: str
    goals: list[str] = []
    problem_areas: list[str] = []
    exam_target: Optional[str] = None
    filler: str = "student"
    additional_notes: Optional[str] = None
    created_at: Optional[str] = None


class LearnerProfile(BaseModel):
    student_id: int
    identified_gaps: list[dict] = []
    priority_areas: list[str] = []
    profile_summary: str = ""
    recommended_start_level: Optional[str] = None


class LearnerProfileResponse(BaseModel):
    id: int
    student_id: int
    gaps: list[dict] = []
    priorities: list[str] = []
    profile_summary: str = ""
    recommended_start_level: Optional[str] = None
    created_at: Optional[str] = None
