import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.db.database import get_db
from app.services.srs_engine import sm2_update
from app.services.xp_engine import award_xp
from app.routes.challenges import update_challenge_progress

router = APIRouter(prefix="/api/concepts", tags=["concepts"])


class ConceptCard(BaseModel):
    concept: str
    formula: Optional[str] = None
    explanation: str
    example: Optional[str] = None
    math_domain: str = "arytmetyka"


class ReviewSubmission(BaseModel):
    card_id: int
    quality: int  # 0-5


@router.get("/{student_id}/due")
async def get_due_cards(student_id: int):
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM math_concept_cards WHERE student_id = ? AND next_review <= CURRENT_TIMESTAMP ORDER BY next_review LIMIT 20",
            (student_id,),
        )
        rows = await cursor.fetchall()

        cards = [
            {
                "id": row["id"],
                "concept": row["concept"],
                "formula": row["formula"],
                "explanation": row["explanation"],
                "example": row["example"],
                "math_domain": row["math_domain"],
                "ease_factor": row["ease_factor"],
                "interval_days": row["interval_days"],
                "repetitions": row["repetitions"],
                "review_count": row["review_count"],
            }
            for row in rows
        ]

        return {"student_id": student_id, "due_count": len(cards), "cards": cards}
    finally:
        await db.close()


@router.post("/{student_id}/add")
async def add_card(student_id: int, card: ConceptCard):
    db = await get_db()
    try:
        # Check for duplicate
        cursor = await db.execute(
            "SELECT id FROM math_concept_cards WHERE student_id = ? AND concept = ?",
            (student_id, card.concept),
        )
        if await cursor.fetchone():
            raise HTTPException(status_code=409, detail="Card already exists for this concept")

        cursor = await db.execute(
            "INSERT INTO math_concept_cards (student_id, concept, formula, explanation, example, math_domain) VALUES (?, ?, ?, ?, ?, ?)",
            (student_id, card.concept, card.formula, card.explanation, card.example, card.math_domain),
        )
        await db.commit()

        # Update challenge progress for adding concept
        await update_challenge_progress(student_id, "concept_add")

        return {"id": cursor.lastrowid, "concept": card.concept, "status": "added"}
    finally:
        await db.close()


@router.post("/{student_id}/review")
async def submit_review(student_id: int, review: ReviewSubmission):
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM math_concept_cards WHERE id = ? AND student_id = ?",
            (review.card_id, student_id),
        )
        card = await cursor.fetchone()
        if not card:
            raise HTTPException(status_code=404, detail="Card not found")

        updated = sm2_update(
            ease_factor=card["ease_factor"],
            interval_days=card["interval_days"],
            repetitions=card["repetitions"],
            quality=review.quality,
        )

        await db.execute(
            "UPDATE math_concept_cards SET ease_factor = ?, interval_days = ?, repetitions = ?, next_review = ?, review_count = review_count + 1 WHERE id = ?",
            (
                updated["ease_factor"],
                updated["interval_days"],
                updated["repetitions"],
                updated["next_review"],
                review.card_id,
            ),
        )
        await db.commit()

        # Award XP for concept review
        await award_xp(student_id, 10, "concept_review", f"Reviewed: {card['concept']}")
        await update_challenge_progress(student_id, "review_concept")

        return {"card_id": review.card_id, "next_review": updated["next_review"], "interval_days": updated["interval_days"]}
    finally:
        await db.close()


@router.get("/{student_id}/stats")
async def get_concept_stats(student_id: int):
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT COUNT(*) as total FROM math_concept_cards WHERE student_id = ?",
            (student_id,),
        )
        total = (await cursor.fetchone())["total"]

        cursor = await db.execute(
            "SELECT COUNT(*) as due FROM math_concept_cards WHERE student_id = ? AND next_review <= CURRENT_TIMESTAMP",
            (student_id,),
        )
        due = (await cursor.fetchone())["due"]

        cursor = await db.execute(
            "SELECT COUNT(*) as mastered FROM math_concept_cards WHERE student_id = ? AND repetitions >= 5",
            (student_id,),
        )
        mastered = (await cursor.fetchone())["mastered"]

        cursor = await db.execute(
            "SELECT COUNT(*) as learning FROM math_concept_cards WHERE student_id = ? AND repetitions > 0 AND repetitions < 5",
            (student_id,),
        )
        learning = (await cursor.fetchone())["learning"]

        cursor = await db.execute(
            "SELECT SUM(review_count) as total_reviews FROM math_concept_cards WHERE student_id = ?",
            (student_id,),
        )
        total_reviews = (await cursor.fetchone())["total_reviews"] or 0

        return {
            "student_id": student_id,
            "total_cards": total,
            "due_now": due,
            "mastered": mastered,
            "learning": learning,
            "new": total - mastered - learning,
            "total_reviews": total_reviews,
        }
    finally:
        await db.close()
