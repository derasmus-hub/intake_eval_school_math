# ARCHITECTURE AUDIT: English Tutor → Math Tutor Conversion

## Project Overview

This is a **full-stack adaptive English tutoring platform** for Polish-speaking students,
built with FastAPI (Python) + vanilla HTML/JS frontend + SQLite. It features AI-driven
assessment, lesson generation, spaced-repetition recall, gamification, and teacher/student
scheduling.

The goal is to convert it into a **Polish math tutoring platform** while preserving
all adaptive logic, gamification, SRS, and scheduling infrastructure.

---

## 1. COMPLETE LEARNING LOOP (Step by Step)

```
INTAKE (student registers, declares level/goals/problem areas)
   │
   ▼
PLACEMENT TEST (5 sentences: judge correct/incorrect, difficulty 1-5)
   │  → Determines bracket: beginner / intermediate / advanced
   ▼
DIAGNOSTIC TEST (12 questions: 5 grammar + 4 vocabulary + 3 reading)
   │  → Questions drawn from bracket-specific pool
   │  → Auto-scored per skill area
   ▼
AI ANALYSIS (assessment_engine.analyze_with_ai)
   │  → Uses prompts/assessment_analyzer.yaml
   │  → Cross-references prompts/polish_struggles.yaml
   │  → Outputs: CEFR level, confidence score, sub-skill breakdown,
   │    weak areas, L1 interference patterns, recommendations
   ▼
DIAGNOSTIC AGENT (diagnostic_agent.run_diagnostic)
   │  → Uses prompts/diagnostic.yaml + prompts/polish_struggles.yaml
   │  → Outputs: LearnerProfile (gaps, priorities, summary, start level)
   ▼
LEARNING PATH GENERATION (learning_path_generator.generate_learning_path)
   │  → Uses prompts/learning_path.yaml
   │  → Outputs: 12-week roadmap with weekly themes, grammar focus,
   │    vocabulary topics, milestones at weeks 4/8/12
   ▼
┌──────────────── LESSON LOOP ────────────────┐
│                                              │
│  RECALL CHECK (recall_generator.get_points_due_for_review)
│     │  → Checks learning_points table for items due via SRS
│     │  → If items due → generate recall quiz first
│     ▼
│  RECALL QUIZ (if needed)
│     │  → Uses prompts/generate_recall_questions.yaml
│     │  → Student answers questions on past material
│     │  → Evaluated via prompts/evaluate_recall.yaml
│     │  → SRS schedule updated via srs_engine.sm2_update
│     │  → Weak areas fed into next lesson generation
│     ▼
│  LESSON GENERATION (lesson_generator.generate_lesson)
│     │  → Uses prompts/lesson_generator.yaml
│     │  → Inputs: profile, progress history, previous topics,
│     │    recall weak areas
│     │  → Outputs: 5-phase lesson (warm-up, presentation,
│     │    controlled practice, free practice, wrap-up)
│     │  → Adaptation rules prevent topic repetition,
│     │    force focus on struggling areas
│     ▼
│  LESSON DELIVERY (teacher presents lesson)
│     │
│     ▼
│  PROGRESS SUBMISSION (teacher scores lesson)
│     │  → Records: score, areas_improved, areas_struggling
│     │  → Awards XP (xp_engine.award_xp)
│     │  → Updates streak (xp_engine.update_streak)
│     │  → Checks achievements (achievement_checker.check_achievements)
│     ▼
│  LEARNING POINT EXTRACTION (learning_point_extractor.extract_learning_points)
│     │  → Uses prompts/extract_learning_points.yaml
│     │  → Extracts 3-7 testable points from the lesson
│     │  → Stored in learning_points table with SRS fields
│     │  → These points will appear in future recall quizzes
│     ▼
│  LOOP BACK → next session starts with recall check
│                                              │
└──────────────────────────────────────────────┘

PARALLEL ACTIVITIES (available anytime):
  - Vocabulary flashcards (vocab routes + SRS via srs_engine)
  - Conversation practice (AI chat via conversation_partner.yaml)
  - Mini-games (word match, sentence builder, error hunt, speed translate)
  - Daily challenges (3 per day, various types)
  - Leaderboard (weekly XP, all-time XP, streak rankings)
```

---

## 2. FILE-BY-FILE INVENTORY

### 2.1 Services (`app/services/`)

| File | Purpose | English-Specific? |
|------|---------|-------------------|
| `assessment_engine.py` | Placement scoring, diagnostic question selection (grammar/vocab/reading), AI analysis | **YES** — skill categories are grammar, vocabulary, reading; question types are GRAMMAR_MCQ, VOCABULARY_FILL, READING_COMPREHENSION |
| `diagnostic_agent.py` | Runs AI diagnostic on intake data, produces LearnerProfile | **YES** — loads polish_struggles.yaml (English L1 interference); produces English-focused gaps |
| `lesson_generator.py` | Generates 5-phase lessons via AI | **YES** — lesson phases designed for ESL (warm-up, presentation, controlled practice, free practice, wrap-up); references polish_explanation |
| `learning_path_generator.py` | Generates 12-week learning roadmap | **YES** — references CEFR levels, L1 interference, grammar_focus, vocabulary_topic, skills (reading/writing/speaking/listening) |
| `learning_point_extractor.py` | Extracts testable points from lessons | **YES** — point types: grammar_rule, vocabulary, phrase, pronunciation, usage_pattern; references polish_explanation |
| `recall_generator.py` | Generates recall quiz questions, evaluates answers, updates SRS | **YES** — question types: translate_pl_en, correct_error; references Polish explanations |
| `srs_engine.py` | SM-2 spaced repetition algorithm | **NO** — Pure math algorithm, subject-agnostic |
| `xp_engine.py` | XP awards, levels, streaks, titles | **PARTIALLY** — Level titles are bilingual (Polish/English); XP sources reference "vocab_review", "conversation" |
| `achievement_checker.py` | Achievement definitions and checking | **PARTIALLY** — Achievement types reference "vocab_10", "vocab_50", etc.; CEFR level achievements (B1, B2); descriptions are in English |
| `progress_tracker.py` | Skill averages, focus area selection | **NO** — Generic progress tracking, subject-agnostic |
| `availability_validator.py` | Teacher scheduling/availability | **NO** — Subject-agnostic scheduling logic |

### 2.2 Prompts (`prompts/`)

| File | Purpose | Variables Used | English-Specific? |
|------|---------|----------------|-------------------|
| `assessment_analyzer.yaml` | AI analysis of assessment results | student_id, name, age, bracket, placement_score, diagnostic_responses, grammar_score, vocab_score, reading_score, overall_score, incorrect_details, polish_struggles | **YES** — Entire prompt is about English proficiency analysis, CEFR levels, Polish-English contrastive linguistics |
| `diagnostic.yaml` | AI diagnostic from intake data | name, age, current_level, goals, problem_areas, filler, additional_notes, polish_struggles | **YES** — Specialized for Polish-English contrastive analysis (articles, prepositions, word order, pronunciation, tenses, false friends) |
| `placement_questions.yaml` | Question bank for placement + diagnostic | N/A (data file) | **YES** — All questions test English grammar, vocabulary, and reading comprehension |
| `polish_struggles.yaml` | Polish-English contrastive reference | N/A (data file) | **YES** — Entirely about Polish speakers' English difficulties (articles, prepositions, word order, pronunciation, tenses, false friends, conditionals, phrasal verbs) |
| `lesson_generator.yaml` | AI lesson generation prompt | session_number, current_level, profile_summary, priorities, gaps, progress_history, previous_topics, recall_weak_areas | **YES** — ESL lesson structure (grammar/vocab focus), exercise types (fill_in, translate, reorder, correct_error, multiple_choice), Polish explanations |
| `learning_path.yaml` | AI learning path generation | name, age, current_level, goals, problem_areas, determined_level, confidence_score, sub_skill_breakdown, weak_areas, profile_summary, priorities, gaps, l1_interference | **YES** — 12-week English curriculum, CEFR progression, skills (reading, writing, speaking, listening), Polish L1 interference |
| `extract_learning_points.yaml` | Extract testable points from lessons | student_level, objective, presentation_text, exercises_text, conversation_text | **YES** — Point types: grammar_rule, vocabulary, phrase, pronunciation, usage_pattern |
| `generate_recall_questions.yaml` | Generate recall quiz questions | student_level, learning_points_text | **YES** — Question types include translate_pl_en, correct_error; distractors based on Polish L1 interference |
| `evaluate_recall.yaml` | Evaluate recall quiz answers | student_level, qa_text | **YES** — Scoring is lenient on articles/prepositions (Polish-specific), strict on tested English concepts |
| `conversation_partner.yaml` | AI conversation partner | level, name, scenario_title, scenario_description, weak_areas | **YES** — English conversation scenarios (coffee shop, job interview, debate), correction format for English errors, CEFR level guidelines |

### 2.3 Database Schema (`app/db/schema.sql`)

| Table | English-Specific Fields | Notes |
|-------|------------------------|-------|
| `students` | `native_language DEFAULT 'Polish'`, `current_level` (stores CEFR like A1/B2) | Level field stores CEFR values |
| `learner_profiles` | `gaps` (stores English skill gaps as JSON), `priorities` (English skill areas) | Content is English-specific, structure is generic |
| `lessons` | `objective`, `content` (stores English lesson JSON) | Content is English-specific |
| `progress` | `areas_improved`, `areas_struggling` (store English skill names like "grammar", "articles") | Skill names are English-specific |
| `assessments` | `bracket`, `sub_skill_breakdown` (grammar/vocab/reading scores), `weak_areas`, `ai_analysis` (L1 interference) | Deeply English-specific structure |
| `learning_paths` | `weeks` (English curriculum JSON), `milestones` | Content is English curriculum |
| `vocabulary_cards` | `word`, `translation` (English-Polish pairs) | **Entire table is English vocabulary** |
| `learning_points` | `point_type` (grammar_rule/vocabulary/phrase/pronunciation/usage_pattern), `polish_explanation`, `example_sentence` | Types and content are English-specific |
| `recall_sessions` | `questions`, `answers` (English recall content) | Content is English-specific |
| `daily_challenges` | `challenge_type` (references vocab, conversation) | Some types are English-specific |
| `game_scores` | `game_type` (word-match, sentence-builder, error-hunt, speed-translate) | **All game types are English-specific** |
| `achievements` | Stored achievement types reference vocab counts, CEFR levels | Some types are English-specific |
| `xp_log` | `source` (references vocab_review, conversation) | Some sources are English-specific |
| `sessions`, `teacher_availability`, `teacher_invites` | None | Fully subject-agnostic |

### 2.4 Models (`app/models/`)

| File | Class | English-Specific? |
|------|-------|-------------------|
| `assessment.py` | `Bracket` (beginner/intermediate/advanced) | Reusable for math |
| | `QuestionType` (PLACEMENT, GRAMMAR_MCQ, VOCABULARY_FILL, READING_COMPREHENSION) | **YES** — English skill types |
| | `PlacementQuestion` (sentence, is_correct) | **YES** — Tests English sentence correctness |
| | `DiagnosticQuestion` (skill: grammar/vocabulary/reading) | **YES** — English skills |
| | `PlacementAnswer`, `DiagnosticAnswer` | Reusable |
| | `PlacementResult`, `SubSkillScore`, `AssessmentResultResponse` | Partially reusable |
| `student.py` | `EnglishLevel` (A1-C2) | **YES** — CEFR levels for English |
| | `StudentIntake` (goals, problem_areas) | Content is English-specific |
| | `LearnerProfile` | Reusable structure |
| `lesson.py` | `WarmUp`, `Presentation`, `ControlledPractice`, `FreePractice`, `WrapUp` | **YES** — ESL lesson phases |
| | `LessonContent` (polish_explanation, conversation_prompts) | **YES** — English lesson fields |
| | `ProgressEntry`, `ProgressResponse`, `ProgressSummary` | Mostly reusable |

### 2.5 Routes (`app/routes/`)

| File | Endpoints | English-Specific Content |
|------|-----------|------------------------|
| `auth.py` | POST register, login; GET me; POST teacher/register | No — subject-agnostic |
| `intake.py` | POST intake; PUT level, goals; GET student(s) | Stores English goals/problem areas |
| `diagnostic.py` | POST/GET diagnostic/{student_id} | Calls English diagnostic agent |
| `assessment.py` | POST start, placement, diagnostic; GET latest, results | English skill labels (Grammar, Vocabulary, Reading); CEFR levels |
| `lessons.py` | POST generate, complete; GET lessons | Calls English lesson generator |
| `progress.py` | POST/GET progress | References English skill areas |
| `learning_path.py` | POST generate; GET path; PUT week progress | Generates English curriculum |
| `analytics.py` | GET skills, timeline, achievements, streak | Displays English skill averages |
| `vocabulary.py` | GET due, stats; POST add, review | **Entire route is English vocabulary** |
| `conversation.py` | GET scenarios; POST chat | English conversation practice with AI |
| `recall.py` | GET check; POST start, submit | English recall quiz |
| `challenges.py` | GET today; POST claim, claim-bonus | Challenge titles reference "Vocab Review", "Chat Practice" |
| `leaderboard.py` | GET weekly, alltime, streak | Subject-agnostic |
| `games.py` | GET word-match, sentence-builder, error-hunt, speed-translate; POST submit; GET history | **All games are English-specific** with hardcoded AI prompts |
| `gamification.py` | GET/PUT profile; POST check-achievements, activity; GET weekly-summary | Avatar names bilingual; encouragement in Polish |
| `scheduling.py` | Multiple student/teacher session endpoints | Subject-agnostic |
| `admin.py` | POST/GET teacher-invites | Subject-agnostic |

### 2.6 Frontend (`frontend/`)

| File | English-Specific Content |
|------|------------------------|
| **HTML Files** | |
| `index.html` | Intake form with English problem areas (articles, prepositions, tenses, etc.), CEFR levels |
| `login.html` | Minimal — mostly subject-agnostic |
| `register.html` | Minimal — mostly subject-agnostic |
| `teacher_register.html` | Subject-agnostic |
| `assessment.html` | English assessment UI (grammar MCQ, reading comprehension, vocabulary fill), L1 interference display |
| `dashboard.html` | Teacher dashboard — lesson phases (Warm-Up/Presentation/etc.), "English Lesson" in ICS, skill labels |
| `student_dashboard.html` | "Schedule English Class", CEFR levels, vocab/conversation quick links |
| `session.html` | Recall check gateway — subject-agnostic structure |
| `conversation.html` | English conversation practice with AI |
| `games.html` | 4 English word/grammar games |
| `recall.html` | Spaced-repetition for English content |
| `leaderboard.html` | Subject-agnostic |
| `profile.html` | XP/achievements — "vocabulary" category |
| `vocab.html` | English-Polish flashcard system |
| **JS Files** | |
| `api.js` | Subject-agnostic |
| `app.js` | Subject-agnostic (role routing) |
| `auth.js` | Subject-agnostic |
| `state.js` | Subject-agnostic |
| `nav.js` | Subject-agnostic |
| `assessment.js` | English assessment flow (grammar/vocab/reading), CEFR bracket labels |
| `intake.js` | Hardcoded English problem area mappings (articles, prepositions, "th" sounds, tenses, etc.) |
| `dashboard.js` | "English Lesson" ICS, lesson phase rendering, polish_explanation/polish_context references |
| `conversation.js` | English conversation with correction format |
| `games.js` | All 4 games are English-specific (Word Match, Sentence Builder, Error Hunt, Speed Translate) |
| `recall.js` | Renders English recall quiz |
| `vocab.js` | English-Polish flashcard rendering ("English" / "Polski" labels) |
| `celebrations.js` | Mostly subject-agnostic (Polish encouragement messages) |
| `charts.js` | Subject-agnostic chart rendering |
| **CSS** | |
| `style.css` | `.skill-grammar`, `.skill-vocabulary`, `.skill-reading` color classes; `.polish-text` class |

---

## 3. FILES REQUIRING CHANGES (by conversion priority)

### Priority 1: Core Data & Logic (MUST change)

| File | Change Required |
|------|----------------|
| `app/db/schema.sql` | Replace vocabulary_cards with math concept cards; update learning_points point_types; update game_scores game_types |
| `app/models/assessment.py` | Replace QuestionType enum (GRAMMAR_MCQ → ARITHMETIC, ALGEBRA, etc.); replace PlacementQuestion model; update DiagnosticQuestion skill field |
| `app/models/student.py` | Replace EnglishLevel with MathLevel enum; update StudentIntake fields (goals, problem_areas for math) |
| `app/models/lesson.py` | Replace ESL lesson phases with math lesson phases (explanation, worked examples, practice problems, hints) |
| `prompts/placement_questions.yaml` | Replace all English questions with math questions |
| `prompts/polish_struggles.yaml` | Replace with common math misconceptions for Polish students |
| `prompts/diagnostic.yaml` | Replace English diagnostic with math diagnostic |
| `prompts/assessment_analyzer.yaml` | Replace English assessment analysis with math assessment analysis |
| `prompts/lesson_generator.yaml` | Replace ESL lesson generation with math lesson generation |
| `prompts/learning_path.yaml` | Replace English curriculum with math curriculum |
| `prompts/extract_learning_points.yaml` | Replace English point types with math point types (formula, theorem, method, concept) |
| `prompts/generate_recall_questions.yaml` | Replace English quiz types with math quiz types |
| `prompts/evaluate_recall.yaml` | Replace English evaluation criteria with math evaluation criteria |
| `prompts/conversation_partner.yaml` | **REMOVE or REPLACE** — conversation practice doesn't apply to math; could become "math problem-solving dialogue" |

### Priority 2: Services (wire to new prompts/models)

| File | Change Required |
|------|----------------|
| `app/services/assessment_engine.py` | Update skill categories (grammar/vocab/reading → arytmetyka/algebra/geometria/etc.); update question selection logic |
| `app/services/diagnostic_agent.py` | Update to use math diagnostic prompt instead of English diagnostic |
| `app/services/lesson_generator.py` | Update to use math lesson prompt; update LessonContent construction |
| `app/services/learning_path_generator.py` | Update to use math learning path prompt; remove L1 interference references |
| `app/services/learning_point_extractor.py` | Update point types for math; remove "polish_explanation" → "wyjasnienie" |
| `app/services/recall_generator.py` | Update for math recall questions |
| `app/services/xp_engine.py` | Update XP source names (vocab_review → concept_review); update Polish titles |
| `app/services/achievement_checker.py` | Replace English achievements (vocab_10, level_up_b1) with math achievements |
| `app/services/srs_engine.py` | **NO CHANGE** — SM-2 algorithm is subject-agnostic |
| `app/services/progress_tracker.py` | **NO CHANGE** — Generic progress tracking |
| `app/services/availability_validator.py` | **NO CHANGE** — Subject-agnostic scheduling |

### Priority 3: Routes (wire to new services)

| File | Change Required |
|------|----------------|
| `app/routes/assessment.py` | Update skill labels, fallback messages |
| `app/routes/vocabulary.py` | **RENAME/REPURPOSE** → formula/concept cards |
| `app/routes/conversation.py` | **REPURPOSE** → math problem-solving dialogue or remove |
| `app/routes/games.py` | Replace 4 English games with 4 math games (mental math, equation solver, geometry quiz, speed calc) |
| `app/routes/challenges.py` | Update challenge titles/descriptions for math |
| `app/routes/gamification.py` | Update encouragement messages |
| `app/routes/recall.py` | Update encouragement strings |
| `app/routes/lessons.py` | Minor — wire to updated lesson generator |
| `app/routes/intake.py` | Update for math intake fields |
| `app/routes/diagnostic.py` | Minor — wire to updated diagnostic |
| `app/routes/learning_path.py` | Minor — wire to updated generator |
| `app/routes/progress.py` | Minor — skill names change |
| `app/routes/analytics.py` | Minor — skill names change |
| `app/routes/scheduling.py` | **NO CHANGE** |
| `app/routes/admin.py` | **NO CHANGE** |
| `app/routes/auth.py` | **NO CHANGE** |
| `app/routes/leaderboard.py` | **NO CHANGE** |

### Priority 4: Frontend (UI conversion)

| File | Change Required |
|------|----------------|
| `frontend/index.html` | Replace English problem areas with math topics; replace CEFR levels with math levels |
| `frontend/assessment.html` | Replace English assessment UI with math assessment UI; add math notation rendering |
| `frontend/dashboard.html` | Replace lesson phase names; replace "English Lesson" labels; update skill displays |
| `frontend/student_dashboard.html` | Replace "English Class" with "Lekcja matematyki"; update quick actions |
| `frontend/conversation.html` | Repurpose for math problem-solving or remove |
| `frontend/games.html` | Replace 4 English games with 4 math games |
| `frontend/vocab.html` | Repurpose for math formula/concept cards |
| `frontend/recall.html` | Update for math recall content; add math rendering |
| `frontend/profile.html` | Update achievement categories |
| `frontend/session.html` | Minor label updates |
| `frontend/leaderboard.html` | Minor — mostly subject-agnostic |
| `frontend/login.html` | Minor label updates |
| `frontend/register.html` | Minor label updates |
| `frontend/js/intake.js` | Replace English problem area mappings with math topic mappings |
| `frontend/js/assessment.js` | Replace grammar/vocab/reading rendering with math domain rendering |
| `frontend/js/dashboard.js` | Replace "English Lesson" ICS, lesson phase rendering |
| `frontend/js/games.js` | Rewrite 4 games for math |
| `frontend/js/vocab.js` | Repurpose for math formulas/concepts |
| `frontend/js/conversation.js` | Repurpose or remove |
| `frontend/js/recall.js` | Update for math recall rendering |
| `frontend/js/celebrations.js` | **NO CHANGE** — Already in Polish |
| `frontend/js/charts.js` | Minor — skill label source change |
| `frontend/js/api.js` | **NO CHANGE** |
| `frontend/js/app.js` | **NO CHANGE** |
| `frontend/js/auth.js` | **NO CHANGE** |
| `frontend/js/state.js` | **NO CHANGE** |
| `frontend/js/nav.js` | **NO CHANGE** |
| `frontend/css/style.css` | Replace `.skill-grammar`/`.skill-vocabulary`/`.skill-reading` with math domain classes; add math formula display styles |

### Priority 5: Config & Infrastructure

| File | Change Required |
|------|----------------|
| `app/config.py` | **NO CHANGE** |
| `.env` | **NO CHANGE** |
| `app/db/database.py` | May need new migration entries |
| `app/server.py` | Update FastAPI title |
| `Dockerfile` | **NO CHANGE** (unless new deps) |
| `docker-compose.yml` | **NO CHANGE** |
| `run.py` | **NO CHANGE** |
| `requirements.txt` | May need new deps (e.g., sympy for math) |

---

## 4. CRITICAL DEPENDENCY MAP

```
assessment_engine.py
  ├── reads: prompts/placement_questions.yaml
  ├── reads: prompts/assessment_analyzer.yaml
  ├── reads: prompts/polish_struggles.yaml
  ├── uses model: app/models/assessment.py (Bracket, PlacementQuestion, DiagnosticQuestion, QuestionType, etc.)
  └── called by: app/routes/assessment.py

diagnostic_agent.py
  ├── reads: prompts/diagnostic.yaml
  ├── reads: prompts/polish_struggles.yaml
  ├── uses model: app/models/student.py (LearnerProfile)
  └── called by: app/routes/diagnostic.py

lesson_generator.py
  ├── reads: prompts/lesson_generator.yaml
  ├── uses model: app/models/lesson.py (LessonContent, WarmUp, Presentation, etc.)
  └── called by: app/routes/lessons.py

learning_path_generator.py
  ├── reads: prompts/learning_path.yaml
  └── called by: app/routes/learning_path.py

learning_point_extractor.py
  ├── reads: prompts/extract_learning_points.yaml
  └── called by: app/routes/lessons.py (on lesson complete)

recall_generator.py
  ├── reads: prompts/generate_recall_questions.yaml
  ├── reads: prompts/evaluate_recall.yaml
  ├── uses: srs_engine.py (sm2_update)
  ├── reads DB: learning_points table
  └── called by: app/routes/recall.py

xp_engine.py
  ├── reads/writes DB: students (total_xp, xp_level), xp_log
  └── called by: app/routes/progress.py, recall.py, vocabulary.py, games.py, challenges.py, gamification.py

achievement_checker.py
  ├── reads DB: achievements, students, progress, vocabulary_cards, recall_sessions, game_scores
  ├── uses: xp_engine.py (award_xp)
  └── called by: app/routes/progress.py, analytics.py, gamification.py
```

### Breaking Change Risks

1. **`assessment.py` model ↔ `assessment_engine.py` ↔ `assessment` route ↔ `placement_questions.yaml`**
   All four must be updated in sync. The QuestionType enum, skill field values, and YAML question structure must match.

2. **`lesson.py` model ↔ `lesson_generator.py` ↔ `lesson_generator.yaml` ↔ `lessons` route ↔ `dashboard.js`**
   The LessonContent model fields must match what the AI returns (via the YAML prompt) and what the frontend renders.

3. **`learning_points` DB table ↔ `extract_learning_points.yaml` ↔ `learning_point_extractor.py` ↔ `recall_generator.py` ↔ `generate_recall_questions.yaml` ↔ `evaluate_recall.yaml`**
   The point_type values and content structure flow through the entire SRS pipeline.

4. **`vocabulary_cards` DB table ↔ `vocabulary.py` route ↔ `srs_engine.py` ↔ `vocab.js` ↔ `vocab.html`**
   If repurposing for math formulas, the table structure, route, and frontend must all change together.

5. **`game_scores` DB table ↔ `games.py` route ↔ `games.js` ↔ `games.html`**
   Game types are hardcoded in all four locations and must match.

6. **Achievement types in `achievement_checker.py` ↔ `achievements` DB table ↔ `gamification.py` route ↔ `profile.html`**
   Achievement type strings must be consistent across all.

---

## 5. MATH DOMAIN MAPPING (Proposed)

### Replacing English Skills with Math Domains

| English Skill | Math Domain (PL) | Math Domain (EN) |
|--------------|-------------------|-------------------|
| grammar | arytmetyka | arithmetic |
| vocabulary | algebra | algebra |
| reading | geometria | geometry |
| (new) | trygonometria | trigonometry |
| (new) | analiza_matematyczna | calculus |
| (new) | statystyka_i_prawdopodobienstwo | statistics & probability |
| (new) | logika | logic/proofs |

### Replacing CEFR Levels with Math Levels

| CEFR | Math Level (PL) | Description |
|------|-----------------|-------------|
| A1 | Poziom 1 - Podstawowy | Elementary arithmetic |
| A2 | Poziom 2 - Rozszerzony podstawowy | Advanced arithmetic, intro algebra |
| B1 | Poziom 3 - Gimnazjalny | Middle school math |
| B2 | Poziom 4 - Licealny podstawowy | High school basic |
| C1 | Poziom 5 - Licealny rozszerzony | High school advanced |
| C2 | Poziom 6 - Zaawansowany | University prep / competition |

### Replacing Lesson Phases

| English Phase | Math Phase (PL) | Purpose |
|--------------|-----------------|---------|
| Warm-Up | Rozgrzewka | Mental math drill or review |
| Presentation | Wyjasnienie tematu | Topic explanation with theory |
| Controlled Practice | Przyklady rozwiazane | Step-by-step worked examples |
| Free Practice | Zadania do rozwiazania | Independent practice problems |
| Wrap-Up | Podsumowanie | Summary + homework |

### Replacing Question/Point Types

| English Type | Math Type | Description |
|-------------|-----------|-------------|
| grammar_rule | wzor_formula | Mathematical formula |
| vocabulary | definicja | Math definition/term |
| phrase | twierdzenie | Theorem/property |
| pronunciation | metoda | Solution method/technique |
| usage_pattern | zastosowanie | Application pattern |

### Replacing Game Types

| English Game | Math Game | Description |
|-------------|-----------|-------------|
| word-match | dopasuj-wzory | Match formulas to descriptions |
| sentence-builder | ukladanka-rownan | Build equations from parts |
| error-hunt | znajdz-blad | Find errors in solutions |
| speed-translate | szybkie-liczenie | Speed mental arithmetic |

---

## 6. SUMMARY STATISTICS

- **Total files requiring changes:** ~55 (of ~70 non-infrastructure source files)
- **Files with NO changes needed:** srs_engine.py, progress_tracker.py, availability_validator.py, auth route, admin route, leaderboard route, scheduling route, api.js, app.js, auth.js, state.js, nav.js, config.py, database.py (migrations only), .env, Dockerfile, docker-compose.yml, run.py
- **Deepest changes:** prompts/ (complete rewrite), games.py/games.js (complete rewrite), vocab.py/vocab.js (repurpose), assessment flow (4-file sync)
- **UI language:** Currently mixed English/Polish → Target: all Polish
