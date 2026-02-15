#!/usr/bin/env python3
"""
Migration script: Convert English tutoring database to Math tutoring database.

Run from project root:
    python migrate_to_math.py

This script:
1. Backs up the existing database
2. Adds new columns (exam_target, math_domain, etc.)
3. Renames vocabulary_cards -> math_concept_cards (creates new, copies data)
4. Updates learning_points columns (polish_explanation -> explanation, example_sentence -> example_problem)
5. Updates enum values in existing data
"""

import sqlite3
import shutil
import sys
from pathlib import Path
from datetime import datetime


DB_PATH = Path("intake_eval.db")

# Map old English skill names to math domain names
SKILL_MAP = {
    "grammar": "arytmetyka",
    "vocabulary": "algebra",
    "reading": "geometria",
    "listening": "trygonometria",
    "speaking": "logika",
    "writing": "statystyka_i_prawdopodobienstwo",
    "articles": "arytmetyka",
    "prepositions": "algebra",
    "word_order": "geometria",
    "pronunciation": "arytmetyka",
    "tenses": "algebra",
    "false_friends": "logika",
    "conditionals": "analiza_matematyczna",
    "phrasal_verbs": "algebra",
}

# Map CEFR levels to math levels
LEVEL_MAP = {
    "A1": "podstawowy",
    "A2": "podstawowy",
    "B1": "gimnazjalny",
    "B2": "licealny",
    "C1": "licealny_rozszerzony",
    "C2": "zaawansowany",
    "pending": "pending",
}

# Map old game types to new math game types
GAME_TYPE_MAP = {
    "word-match": "dopasuj-wzory",
    "sentence-builder": "ukladanka-rownan",
    "error-hunt": "znajdz-blad",
    "speed-translate": "szybkie-liczenie",
}

# Map old point types to new math point types
POINT_TYPE_MAP = {
    "grammar_rule": "wzor_formula",
    "vocabulary": "definicja",
    "phrase": "twierdzenie",
    "pronunciation": "metoda",
    "usage_pattern": "zastosowanie",
}


def backup_db():
    if not DB_PATH.exists():
        print(f"Database {DB_PATH} not found. Nothing to migrate.")
        sys.exit(0)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = DB_PATH.with_name(f"intake_eval_backup_{timestamp}.db")
    shutil.copy2(DB_PATH, backup_path)
    print(f"Backup created: {backup_path}")
    return backup_path


def add_column_if_missing(cursor, table, column, sql):
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in cursor.fetchall()]
    if column not in columns:
        cursor.execute(sql)
        print(f"  Added column {table}.{column}")
    else:
        print(f"  Column {table}.{column} already exists, skipping")


def migrate():
    backup_path = backup_db()
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print("\n--- Step 1: Add new columns ---")

    add_column_if_missing(cursor, "students", "exam_target",
        "ALTER TABLE students ADD COLUMN exam_target TEXT")
    add_column_if_missing(cursor, "lessons", "math_domain",
        "ALTER TABLE lessons ADD COLUMN math_domain TEXT")
    add_column_if_missing(cursor, "learning_points", "math_domain",
        "ALTER TABLE learning_points ADD COLUMN math_domain TEXT")

    print("\n--- Step 2: Create math_concept_cards table ---")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS math_concept_cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            concept TEXT NOT NULL,
            formula TEXT,
            explanation TEXT NOT NULL,
            example TEXT,
            math_domain TEXT DEFAULT 'arytmetyka',
            ease_factor REAL DEFAULT 2.5,
            interval_days INTEGER DEFAULT 0,
            repetitions INTEGER DEFAULT 0,
            next_review TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            review_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES students(id)
        )
    """)
    print("  Created math_concept_cards table")

    # Migrate data from vocabulary_cards if it exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='vocabulary_cards'")
    if cursor.fetchone():
        cursor.execute("SELECT COUNT(*) FROM vocabulary_cards")
        count = cursor.fetchone()[0]
        if count > 0:
            cursor.execute("""
                INSERT INTO math_concept_cards (student_id, concept, explanation, example,
                    ease_factor, interval_days, repetitions, next_review, review_count, created_at)
                SELECT student_id, word, translation, example,
                    ease_factor, interval_days, repetitions, next_review, review_count, created_at
                FROM vocabulary_cards
            """)
            print(f"  Migrated {count} vocabulary cards -> math concept cards")
        print("  Note: vocabulary_cards table left intact as backup")
    else:
        print("  No vocabulary_cards table found, skipping migration")

    print("\n--- Step 3: Rename learning_points columns ---")

    # SQLite doesn't support RENAME COLUMN in older versions, so we check first
    cursor.execute("PRAGMA table_info(learning_points)")
    lp_columns = {row[1] for row in cursor.fetchall()}

    if "polish_explanation" in lp_columns and "explanation" not in lp_columns:
        cursor.execute("ALTER TABLE learning_points RENAME COLUMN polish_explanation TO explanation")
        print("  Renamed learning_points.polish_explanation -> explanation")
    elif "explanation" in lp_columns:
        print("  learning_points.explanation already exists")

    if "example_sentence" in lp_columns and "example_problem" not in lp_columns:
        cursor.execute("ALTER TABLE learning_points RENAME COLUMN example_sentence TO example_problem")
        print("  Renamed learning_points.example_sentence -> example_problem")
    elif "example_problem" in lp_columns:
        print("  learning_points.example_problem already exists")

    print("\n--- Step 4: Update CEFR levels to math levels ---")

    for old_level, new_level in LEVEL_MAP.items():
        cursor.execute(
            "UPDATE students SET current_level = ? WHERE current_level = ?",
            (new_level, old_level),
        )
        affected = cursor.rowcount
        if affected > 0:
            print(f"  Updated {affected} students: {old_level} -> {new_level}")

    print("\n--- Step 5: Update learning_points point_type values ---")

    for old_type, new_type in POINT_TYPE_MAP.items():
        cursor.execute(
            "UPDATE learning_points SET point_type = ? WHERE point_type = ?",
            (new_type, old_type),
        )
        affected = cursor.rowcount
        if affected > 0:
            print(f"  Updated {affected} learning points: {old_type} -> {new_type}")

    print("\n--- Step 6: Update game_scores game_type values ---")

    for old_type, new_type in GAME_TYPE_MAP.items():
        cursor.execute(
            "UPDATE game_scores SET game_type = ? WHERE game_type = ?",
            (new_type, old_type),
        )
        affected = cursor.rowcount
        if affected > 0:
            print(f"  Updated {affected} game scores: {old_type} -> {new_type}")

    conn.commit()
    conn.close()

    print(f"\n--- Migration complete! ---")
    print(f"Backup at: {backup_path}")
    print(f"Database updated: {DB_PATH}")


if __name__ == "__main__":
    migrate()
