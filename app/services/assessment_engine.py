import json
import random
import yaml
from pathlib import Path
from openai import AsyncOpenAI
from app.config import settings
from app.models.assessment import (
    Bracket,
    PlacementQuestion,
    DiagnosticQuestion,
    PlacementAnswer,
    DiagnosticAnswer,
    PlacementResult,
    QuestionType,
)

PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"


class AssessmentEngine:
    _instance = None
    _question_bank = None
    _analyzer_prompt = None
    _math_misconceptions = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _load_question_bank(self):
        if self._question_bank is None:
            with open(PROMPTS_DIR / "placement_questions.yaml", "r") as f:
                self._question_bank = yaml.safe_load(f)
        return self._question_bank

    def _load_analyzer_prompt(self):
        if self._analyzer_prompt is None:
            with open(PROMPTS_DIR / "assessment_analyzer.yaml", "r") as f:
                self._analyzer_prompt = yaml.safe_load(f)
        return self._analyzer_prompt

    def _load_math_misconceptions(self):
        if self._math_misconceptions is None:
            with open(PROMPTS_DIR / "polish_struggles.yaml", "r") as f:
                self._math_misconceptions = yaml.safe_load(f)
        return self._math_misconceptions

    def get_placement_questions(self) -> list[PlacementQuestion]:
        bank = self._load_question_bank()
        questions = []
        for q in bank["placement"]:
            questions.append(
                PlacementQuestion(
                    id=q["id"],
                    problem=q["problem"],
                    correct_answer=q["correct_answer"],
                    difficulty=q["difficulty"],
                    math_domain=q["math_domain"],
                    explanation=q["explanation"],
                )
            )
        return questions

    def score_placement(self, answers: list[PlacementAnswer]) -> PlacementResult:
        bank = self._load_question_bank()
        questions_by_id = {q["id"]: q for q in bank["placement"]}

        correct_count = 0
        max_correct_difficulty = 0

        for answer in answers:
            q = questions_by_id.get(answer.question_id)
            if q is None:
                continue
            if answer.answer.strip().lower() == str(q["correct_answer"]).strip().lower():
                correct_count += 1
                max_correct_difficulty = max(max_correct_difficulty, q["difficulty"])

        # Bracket determination:
        # Only got difficulty 1-2 correct = beginner
        # Got difficulty 1-3 correct = intermediate
        # Got difficulty 4+ correct = advanced
        if max_correct_difficulty <= 2:
            bracket = Bracket.BEGINNER
            detail = f"Correctly solved problems up to difficulty {max_correct_difficulty}. Assigned to beginner diagnostic."
        elif max_correct_difficulty <= 3:
            bracket = Bracket.INTERMEDIATE
            detail = f"Correctly solved problems up to difficulty {max_correct_difficulty}. Assigned to intermediate diagnostic."
        else:
            bracket = Bracket.ADVANCED
            detail = f"Correctly solved problems up to difficulty {max_correct_difficulty}. Assigned to advanced diagnostic."

        return PlacementResult(
            bracket=bracket,
            score=correct_count,
            detail=detail,
        )

    def get_diagnostic_questions(self, bracket: Bracket) -> list[DiagnosticQuestion]:
        bank = self._load_question_bank()
        bracket_data = bank["diagnostic"][bracket.value]

        # Select 5 arytmetyka, 4 algebra, 3 geometria = 12 total
        arytmetyka_pool = bracket_data["arytmetyka"]
        algebra_pool = bracket_data["algebra"]
        geometria_pool = bracket_data["geometria"]

        arytmetyka_qs = random.sample(arytmetyka_pool, min(5, len(arytmetyka_pool)))
        algebra_qs = random.sample(algebra_pool, min(4, len(algebra_pool)))
        geometria_qs = random.sample(geometria_pool, min(3, len(geometria_pool)))

        questions = []
        for q in arytmetyka_qs:
            questions.append(
                DiagnosticQuestion(
                    id=q["id"],
                    type=QuestionType.ARITHMETIC,
                    bracket=bracket,
                    question=q["question"],
                    options=q.get("options"),
                    correct_answer=q["correct_answer"],
                    skill="arytmetyka",
                    topic=q["topic"],
                )
            )
        for q in algebra_qs:
            questions.append(
                DiagnosticQuestion(
                    id=q["id"],
                    type=QuestionType.ALGEBRA,
                    bracket=bracket,
                    question=q["question"],
                    options=q.get("options"),
                    correct_answer=q["correct_answer"],
                    skill="algebra",
                    topic=q["topic"],
                )
            )
        for q in geometria_qs:
            questions.append(
                DiagnosticQuestion(
                    id=q["id"],
                    type=QuestionType.GEOMETRY,
                    bracket=bracket,
                    question=q["question"],
                    options=q.get("options"),
                    correct_answer=q["correct_answer"],
                    skill="geometria",
                    topic=q["topic"],
                )
            )

        return questions

    def score_diagnostic_responses(
        self,
        answers: list[DiagnosticAnswer],
        questions: list[DiagnosticQuestion],
    ) -> dict:
        questions_by_id = {q.id: q for q in questions}

        results = {
            "arytmetyka": {"correct": 0, "total": 0, "details": []},
            "algebra": {"correct": 0, "total": 0, "details": []},
            "geometria": {"correct": 0, "total": 0, "details": []},
        }

        for answer in answers:
            q = questions_by_id.get(answer.question_id)
            if q is None:
                continue

            is_correct = answer.answer.strip().lower() == q.correct_answer.strip().lower()
            results[q.skill]["total"] += 1
            if is_correct:
                results[q.skill]["correct"] += 1

            results[q.skill]["details"].append(
                {
                    "question_id": q.id,
                    "question": q.question,
                    "student_answer": answer.answer,
                    "correct_answer": q.correct_answer,
                    "is_correct": is_correct,
                    "topic": q.topic,
                }
            )

        # Calculate percentages
        for skill in results:
            total = results[skill]["total"]
            correct = results[skill]["correct"]
            results[skill]["score"] = round((correct / total * 100) if total > 0 else 0, 1)

        total_correct = sum(r["correct"] for r in results.values())
        total_questions = sum(r["total"] for r in results.values())
        results["overall_score"] = round(
            (total_correct / total_questions * 100) if total_questions > 0 else 0, 1
        )

        return results

    async def analyze_with_ai(
        self,
        student_id: int,
        student_info: dict,
        bracket: Bracket,
        placement_score: int,
        diagnostic_scores: dict,
        questions: list[DiagnosticQuestion],
        answers: list[DiagnosticAnswer],
    ) -> dict:
        prompt_data = self._load_analyzer_prompt()
        math_misconceptions = self._load_math_misconceptions()

        # Build diagnostic responses text
        questions_by_id = {q.id: q for q in questions}
        responses_lines = []
        incorrect_lines = []

        for answer in answers:
            q = questions_by_id.get(answer.question_id)
            if q is None:
                continue
            is_correct = answer.answer.strip().lower() == q.correct_answer.strip().lower()
            status = "CORRECT" if is_correct else "INCORRECT"
            responses_lines.append(
                f"[{q.skill.upper()} - {q.topic}] Q: {q.question} | "
                f"Student answered: {answer.answer} | Correct: {q.correct_answer} | {status}"
            )
            if not is_correct:
                incorrect_lines.append(
                    f"- [{q.skill}/{q.topic}] Expected '{q.correct_answer}', "
                    f"got '{answer.answer}' — Question: {q.question}"
                )

        user_message = prompt_data["user_template"].format(
            student_id=student_id,
            name=student_info.get("name", "Unknown"),
            age=student_info.get("age", "Not specified"),
            bracket=bracket.value,
            placement_score=placement_score,
            diagnostic_responses="\n".join(responses_lines),
            arytmetyka_score=f"{diagnostic_scores['arytmetyka']['correct']}/{diagnostic_scores['arytmetyka']['total']} ({diagnostic_scores['arytmetyka']['score']}%)",
            algebra_score=f"{diagnostic_scores['algebra']['correct']}/{diagnostic_scores['algebra']['total']} ({diagnostic_scores['algebra']['score']}%)",
            geometria_score=f"{diagnostic_scores['geometria']['correct']}/{diagnostic_scores['geometria']['total']} ({diagnostic_scores['geometria']['score']}%)",
            overall_score=f"{diagnostic_scores['overall_score']}%",
            incorrect_details="\n".join(incorrect_lines) if incorrect_lines else "No incorrect answers.",
            math_misconceptions=yaml.dump(
                math_misconceptions, default_flow_style=False, allow_unicode=True
            ),
        )

        client = AsyncOpenAI(api_key=settings.api_key)

        response = await client.chat.completions.create(
            model=settings.model_name,
            messages=[
                {"role": "system", "content": prompt_data["system_prompt"]},
                {"role": "user", "content": user_message},
            ],
            temperature=0.3,
            response_format={"type": "json_object"},
        )

        result_text = response.choices[0].message.content
        return json.loads(result_text)


# Module-level singleton
assessment_engine = AssessmentEngine()
