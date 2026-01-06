"""SQLite database models for AWS Quiz app."""

import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "quiz.db"

def get_db():
    """Get database connection with row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database schema."""
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY,
            question_number INTEGER UNIQUE,
            topic INTEGER,
            question_text TEXT NOT NULL,
            options TEXT NOT NULL,  -- JSON
            correct_answer TEXT NOT NULL,
            community_vote TEXT,
            tags TEXT DEFAULT '[]'  -- JSON array of AWS service tags
        );

        CREATE TABLE IF NOT EXISTS answer_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_id INTEGER NOT NULL,
            answer_given TEXT NOT NULL,
            is_correct INTEGER NOT NULL,
            answered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (question_id) REFERENCES questions(id)
        );

        CREATE TABLE IF NOT EXISTS question_stats (
            question_id INTEGER PRIMARY KEY,
            times_correct INTEGER DEFAULT 0,
            times_wrong INTEGER DEFAULT 0,
            last_answered TIMESTAMP,
            next_review TIMESTAMP,
            ease_factor REAL DEFAULT 2.5,  -- SM-2 algorithm
            interval_days INTEGER DEFAULT 0,
            FOREIGN KEY (question_id) REFERENCES questions(id)
        );

        CREATE INDEX IF NOT EXISTS idx_answer_history_question
            ON answer_history(question_id);
        CREATE INDEX IF NOT EXISTS idx_answer_history_date
            ON answer_history(answered_at);
        CREATE INDEX IF NOT EXISTS idx_question_stats_review
            ON question_stats(next_review);
    """)
    conn.commit()
    conn.close()

def get_question(question_id):
    """Get a single question by ID."""
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM questions WHERE id = ?", (question_id,)
    ).fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

def get_questions_for_session(count, filter_mode="all", tags=None):
    """
    Get questions for a quiz session.

    filter_mode options:
    - all: random selection from all questions
    - new: questions never answered
    - wrong: questions answered wrong more than right
    - due: questions due for spaced repetition review

    tags: optional list of AWS service tags to filter by
    """
    conn = get_db()

    # Build tag filter clause
    tag_filter = ""
    if tags:
        tag_conditions = " OR ".join([f"q.tags LIKE '%\"{tag}\"%'" for tag in tags])
        tag_filter = f" AND ({tag_conditions})"

    if filter_mode == "new":
        query = f"""
            SELECT q.* FROM questions q
            LEFT JOIN question_stats qs ON q.id = qs.question_id
            WHERE qs.question_id IS NULL {tag_filter}
            ORDER BY RANDOM()
            LIMIT ?
        """
    elif filter_mode == "wrong":
        query = f"""
            SELECT q.* FROM questions q
            JOIN question_stats qs ON q.id = qs.question_id
            WHERE qs.times_wrong > qs.times_correct {tag_filter}
            ORDER BY (qs.times_wrong - qs.times_correct) DESC, RANDOM()
            LIMIT ?
        """
    elif filter_mode == "due":
        query = f"""
            SELECT q.* FROM questions q
            JOIN question_stats qs ON q.id = qs.question_id
            WHERE qs.next_review <= datetime('now') {tag_filter}
            ORDER BY qs.next_review ASC
            LIMIT ?
        """
    else:  # all
        query = f"""
            SELECT q.* FROM questions q
            WHERE 1=1 {tag_filter}
            ORDER BY RANDOM()
            LIMIT ?
        """

    rows = conn.execute(query, (count,)).fetchall()
    conn.close()
    return [dict(row) for row in rows]

def record_answer(question_id, answer_given, is_correct):
    """Record an answer and update stats."""
    conn = get_db()
    now = datetime.now()

    # Record in history
    conn.execute(
        """INSERT INTO answer_history (question_id, answer_given, is_correct, answered_at)
           VALUES (?, ?, ?, ?)""",
        (question_id, answer_given, 1 if is_correct else 0, now)
    )

    # Get or create stats
    stats = conn.execute(
        "SELECT * FROM question_stats WHERE question_id = ?", (question_id,)
    ).fetchone()

    if stats is None:
        # Create new stats record
        ease_factor = 2.5
        interval_days = 1 if is_correct else 0
        next_review = now + timedelta(days=interval_days)

        conn.execute(
            """INSERT INTO question_stats
               (question_id, times_correct, times_wrong, last_answered, next_review, ease_factor, interval_days)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (question_id, 1 if is_correct else 0, 0 if is_correct else 1,
             now, next_review, ease_factor, interval_days)
        )
    else:
        # Update existing stats with SM-2 algorithm
        ease_factor = stats['ease_factor']
        interval_days = stats['interval_days']

        if is_correct:
            # Increase interval
            if interval_days == 0:
                interval_days = 1
            elif interval_days == 1:
                interval_days = 3
            else:
                interval_days = int(interval_days * ease_factor)
            # Adjust ease factor (slight increase for correct)
            ease_factor = min(ease_factor + 0.1, 3.0)
        else:
            # Reset interval on wrong answer
            interval_days = 0
            # Decrease ease factor
            ease_factor = max(ease_factor - 0.2, 1.3)

        next_review = now + timedelta(days=interval_days)

        conn.execute(
            """UPDATE question_stats SET
               times_correct = times_correct + ?,
               times_wrong = times_wrong + ?,
               last_answered = ?,
               next_review = ?,
               ease_factor = ?,
               interval_days = ?
               WHERE question_id = ?""",
            (1 if is_correct else 0, 0 if is_correct else 1,
             now, next_review, ease_factor, interval_days, question_id)
        )

    conn.commit()
    conn.close()

def get_dashboard_stats():
    """Get statistics for the dashboard."""
    conn = get_db()

    # Total questions
    total = conn.execute("SELECT COUNT(*) as count FROM questions").fetchone()['count']

    # Questions attempted
    attempted = conn.execute(
        "SELECT COUNT(*) as count FROM question_stats"
    ).fetchone()['count']

    # Total answers
    total_answers = conn.execute(
        "SELECT COUNT(*) as count FROM answer_history"
    ).fetchone()['count']

    # Correct answers
    correct_answers = conn.execute(
        "SELECT COUNT(*) as count FROM answer_history WHERE is_correct = 1"
    ).fetchone()['count']

    # Questions mastered (correct > wrong and interval > 7 days)
    mastered = conn.execute(
        """SELECT COUNT(*) as count FROM question_stats
           WHERE times_correct > times_wrong AND interval_days >= 7"""
    ).fetchone()['count']

    # Questions due for review
    due_count = conn.execute(
        """SELECT COUNT(*) as count FROM question_stats
           WHERE next_review <= datetime('now')"""
    ).fetchone()['count']

    # Recent activity (last 7 days)
    recent_activity = conn.execute(
        """SELECT DATE(answered_at) as date,
                  COUNT(*) as total,
                  SUM(is_correct) as correct
           FROM answer_history
           WHERE answered_at >= datetime('now', '-7 days')
           GROUP BY DATE(answered_at)
           ORDER BY date"""
    ).fetchall()

    # Weakest questions (most wrong)
    weakest = conn.execute(
        """SELECT q.question_number, q.question_text, qs.times_correct, qs.times_wrong
           FROM questions q
           JOIN question_stats qs ON q.id = qs.question_id
           WHERE qs.times_wrong > 0
           ORDER BY (qs.times_wrong - qs.times_correct) DESC
           LIMIT 5"""
    ).fetchall()

    conn.close()

    return {
        'total_questions': total,
        'attempted': attempted,
        'new_questions': total - attempted,
        'total_answers': total_answers,
        'correct_answers': correct_answers,
        'accuracy': round(correct_answers / total_answers * 100, 1) if total_answers > 0 else 0,
        'mastered': mastered,
        'due_for_review': due_count,
        'recent_activity': [dict(row) for row in recent_activity],
        'weakest_questions': [dict(row) for row in weakest]
    }

def get_filter_counts(tags=None):
    """Get counts for each filter mode, optionally filtered by tags."""
    conn = get_db()

    # Build tag filter clause
    tag_filter = ""
    if tags:
        # Match any of the provided tags using JSON
        tag_conditions = " OR ".join([f"q.tags LIKE '%\"{tag}\"%'" for tag in tags])
        tag_filter = f" AND ({tag_conditions})"

    total = conn.execute(
        f"SELECT COUNT(*) as count FROM questions q WHERE 1=1 {tag_filter}"
    ).fetchone()['count']

    new_count = conn.execute(
        f"""SELECT COUNT(*) as count FROM questions q
           LEFT JOIN question_stats qs ON q.id = qs.question_id
           WHERE qs.question_id IS NULL {tag_filter}"""
    ).fetchone()['count']

    wrong_count = conn.execute(
        f"""SELECT COUNT(*) as count FROM questions q
           JOIN question_stats qs ON q.id = qs.question_id
           WHERE qs.times_wrong > qs.times_correct {tag_filter}"""
    ).fetchone()['count']

    due_count = conn.execute(
        f"""SELECT COUNT(*) as count FROM questions q
           JOIN question_stats qs ON q.id = qs.question_id
           WHERE qs.next_review <= datetime('now') {tag_filter}"""
    ).fetchone()['count']

    conn.close()

    return {
        'all': total,
        'new': new_count,
        'wrong': wrong_count,
        'due': due_count
    }


def get_all_tags():
    """Get all unique tags with their question counts."""
    conn = get_db()
    rows = conn.execute("SELECT tags FROM questions").fetchall()
    conn.close()

    tag_counts = {}
    for row in rows:
        tags = json.loads(row['tags']) if row['tags'] else []
        for tag in tags:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1

    # Sort by count descending
    sorted_tags = sorted(tag_counts.items(), key=lambda x: -x[1])
    return [{'tag': tag, 'count': count} for tag, count in sorted_tags]
