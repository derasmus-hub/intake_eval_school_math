import json
from fastapi import APIRouter, HTTPException
from app.db.database import get_db
from app.models.assessment import (
    Bracket,
    StartAssessmentRequest,
    PlacementSubmission,
    DiagnosticSubmission,
    AssessmentResultResponse,
    SubSkillScore,
)
from app.services.assessment_engine import assessment_engine

router = APIRouter(prefix="/api/assessment", tags=["assessment"])


@router.post("/start")
async def start_assessment(request: StartAssessmentRequest):
    """Create assessment record and return 5 placement questions."""
    db = await get_db()
    try:
        # Verify student exists
        cursor = await db.execute(
            "SELECT id, name FROM students WHERE id = ?", (request.student_id,)
        )
        student = await cursor.fetchone()
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")

        # Create assessment record
        cursor = await db.execute(
            """INSERT INTO assessments (student_id, stage, status)
               VALUES (?, 'placement', 'in_progress')""",
            (request.student_id,),
        )
        await db.commit()
        assessment_id = cursor.lastrowid

        # Get placement questions
        questions = assessment_engine.get_placement_questions()

        return {
            "assessment_id": assessment_id,
            "stage": "placement",
            "questions": [
                {
                    "id": q.id,
                    "problem": q.problem,
                    "difficulty": q.difficulty,
                    "math_domain": q.math_domain,
                }
                for q in questions
            ],
        }
    finally:
        await db.close()


@router.post("/placement")
async def submit_placement(submission: PlacementSubmission):
    """Score placement, determine bracket, return diagnostic questions."""
    db = await get_db()
    try:
        # Verify assessment exists and is in placement stage
        cursor = await db.execute(
            "SELECT id, student_id, stage, status FROM assessments WHERE id = ?",
            (submission.assessment_id,),
        )
        assessment = await cursor.fetchone()
        if not assessment:
            raise HTTPException(status_code=404, detail="Assessment not found")
        if assessment["status"] != "in_progress":
            raise HTTPException(status_code=400, detail="Assessment is not in progress")

        # Score placement
        result = assessment_engine.score_placement(submission.answers)

        # Get diagnostic questions for determined bracket
        diagnostic_questions = assessment_engine.get_diagnostic_questions(result.bracket)

        # Store placement responses and bracket
        placement_data = {
            "answers": [a.model_dump() for a in submission.answers],
            "score": result.score,
            "bracket": result.bracket.value,
            "detail": result.detail,
        }

        await db.execute(
            """UPDATE assessments
               SET stage = 'diagnostic',
                   bracket = ?,
                   responses = ?,
                   updated_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (
                result.bracket.value,
                json.dumps({"placement": placement_data}),
                submission.assessment_id,
            ),
        )
        await db.commit()

        # Return bracket and diagnostic questions (without correct answers)
        return {
            "assessment_id": submission.assessment_id,
            "stage": "diagnostic",
            "placement_result": {
                "bracket": result.bracket.value,
                "score": result.score,
                "detail": result.detail,
            },
            "questions": [
                {
                    "id": q.id,
                    "type": q.type.value,
                    "question": q.question,
                    "options": q.options,
                    "skill": q.skill,
                    "topic": q.topic,
                    "hint": q.hint,
                }
                for q in diagnostic_questions
            ],
        }
    finally:
        await db.close()


@router.post("/diagnostic")
async def submit_diagnostic(submission: DiagnosticSubmission):
    """Auto-score diagnostic + AI analysis, return math level + breakdown."""
    db = await get_db()
    try:
        # Verify assessment
        cursor = await db.execute(
            "SELECT * FROM assessments WHERE id = ?",
            (submission.assessment_id,),
        )
        assessment = await cursor.fetchone()
        if not assessment:
            raise HTTPException(status_code=404, detail="Assessment not found")
        if assessment["status"] != "in_progress":
            raise HTTPException(status_code=400, detail="Assessment is not in progress")

        bracket = Bracket(assessment["bracket"])

        # Get student info
        cursor = await db.execute(
            "SELECT * FROM students WHERE id = ?", (submission.student_id,)
        )
        student = await cursor.fetchone()
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")

        student_info = {
            "name": student["name"],
            "age": student["age"],
        }

        # Reconstruct diagnostic questions for this bracket
        diagnostic_questions = assessment_engine.get_diagnostic_questions(bracket)

        # If the stored questions differ from the newly generated ones (due to randomness),
        # we need the questions that match the submitted answer IDs.
        # Pull the full question bank for scoring
        bank = assessment_engine._load_question_bank()
        bracket_data = bank["diagnostic"][bracket.value]

        # Build a complete lookup of all questions in this bracket
        from app.models.assessment import DiagnosticQuestion, QuestionType

        all_questions = []
        for q in bracket_data["arytmetyka"]:
            all_questions.append(
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
        for q in bracket_data["algebra"]:
            all_questions.append(
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
        for q in bracket_data["geometria"]:
            all_questions.append(
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

        # Filter to only questions that were answered
        answered_ids = {a.question_id for a in submission.answers}
        matched_questions = [q for q in all_questions if q.id in answered_ids]

        # Score diagnostic
        diagnostic_scores = assessment_engine.score_diagnostic_responses(
            submission.answers, matched_questions
        )

        # Get placement score from stored responses
        existing_responses = json.loads(assessment["responses"]) if assessment["responses"] else {}
        placement_score = existing_responses.get("placement", {}).get("score", 0)

        # AI analysis — wrapped so a failed OpenAI call still returns scores
        ai_error = None
        try:
            ai_result = await assessment_engine.analyze_with_ai(
                student_id=submission.student_id,
                student_info=student_info,
                bracket=bracket,
                placement_score=placement_score,
                diagnostic_scores=diagnostic_scores,
                questions=matched_questions,
                answers=submission.answers,
            )
        except Exception as exc:
            import traceback
            traceback.print_exc()
            ai_error = str(exc)[:200]

            bracket_to_level = {
                "beginner": "podstawowy",
                "intermediate": "gimnazjalny",
                "advanced": "licealny",
            }
            overall = diagnostic_scores["overall_score"]
            base_level = bracket_to_level.get(bracket.value, "podstawowy")

            weak_areas_list = [
                skill
                for skill in ("arytmetyka", "algebra", "geometria")
                if diagnostic_scores[skill]["score"] < 60
            ]

            ai_result = {
                "determined_level": base_level,
                "confidence_score": 0.5,
                "sub_skill_breakdown": [
                    {
                        "skill": "Arytmetyka",
                        "score": diagnostic_scores["arytmetyka"]["score"],
                        "level": base_level,
                        "details": "Wynik z testu diagnostycznego (analiza AI niedostepna)",
                    },
                    {
                        "skill": "Algebra",
                        "score": diagnostic_scores["algebra"]["score"],
                        "level": base_level,
                        "details": "Wynik z testu diagnostycznego (analiza AI niedostepna)",
                    },
                    {
                        "skill": "Geometria",
                        "score": diagnostic_scores["geometria"]["score"],
                        "level": base_level,
                        "details": "Wynik z testu diagnostycznego (analiza AI niedostepna)",
                    },
                ],
                "weak_areas": weak_areas_list,
                "common_misconceptions": [],
                "summary": (
                    f"Analiza AI byla niedostepna ({ai_error}). "
                    f"Wyniki testu diagnostycznego sa ponizej. Ogolny wynik: {overall}%."
                ),
                "recommendations": [
                    "Przejrzyj obszary, w ktorych uzyskales wynik ponizej 60%.",
                    "Sprobuj ponownie, gdy analiza AI bedzie dostepna, aby uzyskac szczegolowe podsumowanie.",
                ],
            }

        # Store results
        diagnostic_data = {
            "answers": [a.model_dump() for a in submission.answers],
            "scores": {
                "arytmetyka": diagnostic_scores["arytmetyka"]["score"],
                "algebra": diagnostic_scores["algebra"]["score"],
                "geometria": diagnostic_scores["geometria"]["score"],
                "overall": diagnostic_scores["overall_score"],
            },
            "details": {
                "arytmetyka": diagnostic_scores["arytmetyka"]["details"],
                "algebra": diagnostic_scores["algebra"]["details"],
                "geometria": diagnostic_scores["geometria"]["details"],
            },
        }

        # Merge with existing placement responses
        existing_responses["diagnostic"] = diagnostic_data

        sub_skill_breakdown = ai_result.get("sub_skill_breakdown", [])
        weak_areas = ai_result.get("weak_areas", [])

        await db.execute(
            """UPDATE assessments
               SET stage = 'completed',
                   status = 'completed',
                   responses = ?,
                   ai_analysis = ?,
                   determined_level = ?,
                   confidence_score = ?,
                   sub_skill_breakdown = ?,
                   weak_areas = ?,
                   updated_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (
                json.dumps(existing_responses),
                json.dumps(ai_result),
                ai_result.get("determined_level"),
                ai_result.get("confidence_score"),
                json.dumps(sub_skill_breakdown),
                json.dumps(weak_areas),
                submission.assessment_id,
            ),
        )

        # Update student's current_level
        determined_level = ai_result.get("determined_level")
        if determined_level:
            await db.execute(
                "UPDATE students SET current_level = ? WHERE id = ?",
                (determined_level, submission.student_id),
            )

        await db.commit()

        response = {
            "assessment_id": submission.assessment_id,
            "stage": "completed",
            "determined_level": ai_result.get("determined_level"),
            "confidence_score": ai_result.get("confidence_score"),
            "sub_skill_breakdown": sub_skill_breakdown,
            "weak_areas": weak_areas,
            "common_misconceptions": ai_result.get("common_misconceptions", []),
            "summary": ai_result.get("summary", ""),
            "recommendations": ai_result.get("recommendations", []),
            "scores": {
                "arytmetyka": diagnostic_scores["arytmetyka"]["score"],
                "algebra": diagnostic_scores["algebra"]["score"],
                "geometria": diagnostic_scores["geometria"]["score"],
                "overall": diagnostic_scores["overall_score"],
            },
        }
        if ai_error:
            response["ai_error"] = ai_error
        return response
    finally:
        await db.close()


@router.get("/{student_id}/latest")
async def get_latest_assessment(student_id: int):
    """Return the most recent assessment, or {exists: false} if none."""
    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT * FROM assessments
               WHERE student_id = ?
               ORDER BY created_at DESC LIMIT 1""",
            (student_id,),
        )
        row = await cursor.fetchone()
        if not row:
            return {"exists": False}

        ai_analysis = None
        if row["ai_analysis"]:
            ai_analysis = json.loads(row["ai_analysis"])

        return {
            "exists": True,
            "id": row["id"],
            "student_id": row["student_id"],
            "stage": row["stage"],
            "bracket": row["bracket"],
            "determined_level": row["determined_level"],
            "confidence_score": row["confidence_score"],
            "sub_skill_breakdown": json.loads(row["sub_skill_breakdown"]) if row["sub_skill_breakdown"] else None,
            "weak_areas": json.loads(row["weak_areas"]) if row["weak_areas"] else None,
            "ai_analysis": ai_analysis,
            "status": row["status"],
            "created_at": row["created_at"],
        }
    finally:
        await db.close()


@router.get("/{student_id}")
async def get_assessment(student_id: int):
    """Retrieve latest completed assessment for a student."""
    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT * FROM assessments
               WHERE student_id = ?
               ORDER BY created_at DESC
               LIMIT 1""",
            (student_id,),
        )
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(
                status_code=404,
                detail="No assessment found for this student",
            )

        sub_skills = None
        if row["sub_skill_breakdown"]:
            raw = json.loads(row["sub_skill_breakdown"])
            sub_skills = [
                SubSkillScore(
                    skill=s.get("skill", ""),
                    score=s.get("score", 0),
                    level=s.get("level", ""),
                    details=s.get("details", ""),
                )
                for s in raw
            ]

        weak_areas = None
        if row["weak_areas"]:
            weak_areas = json.loads(row["weak_areas"])

        ai_analysis = None
        if row["ai_analysis"]:
            ai_analysis = json.loads(row["ai_analysis"])

        return AssessmentResultResponse(
            id=row["id"],
            student_id=row["student_id"],
            stage=row["stage"],
            bracket=row["bracket"],
            determined_level=row["determined_level"],
            confidence_score=row["confidence_score"],
            sub_skill_breakdown=sub_skills,
            weak_areas=weak_areas,
            ai_analysis=ai_analysis,
            status=row["status"],
            created_at=row["created_at"],
        )
    finally:
        await db.close()
