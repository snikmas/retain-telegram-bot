"""
Spaced repetition scheduler using the existing FSRS-like schema fields.

Card states: 'new' -> 'learning' -> 'review'
                                  -> 'relearning' (on lapse) -> 'review'

Ratings: 'again' (1), 'hard' (2), 'good' (3), 'easy' (4)
"""

from datetime import datetime, timedelta
from typing import Any

# Rating constants
AGAIN = 1
HARD = 2
GOOD = 3
EASY = 4

# Learning steps in minutes
LEARNING_STEPS = [1, 10]
RELEARNING_STEPS = [10]

# Difficulty bounds (1-10 scale)
MIN_DIFFICULTY = 1.0
MAX_DIFFICULTY = 10.0


def schedule(card: dict[str, Any], rating: int) -> dict[str, Any]:
    """
    Given a card dict (from DB) and a rating (1-4), returns updated SRS fields.

    Returns dict with: due_date, stability, difficulty, reps, lapses, state, scheduled_days
    """
    state = card.get('state', 'new')
    stability = card.get('stability', 0.0)
    difficulty = card.get('difficulty', 5.0)
    reps = card.get('reps', 0)
    lapses = card.get('lapses', 0)

    if state in ('new', 'learning'):
        return _schedule_learning(rating, stability, difficulty, reps, lapses)
    elif state == 'review':
        return _schedule_review(rating, stability, difficulty, reps, lapses)
    elif state == 'relearning':
        return _schedule_relearning(rating, stability, difficulty, reps, lapses)

    # Fallback: treat as new
    return _schedule_learning(rating, stability, difficulty, reps, lapses)


def _schedule_learning(
    rating: int,
    stability: float,
    difficulty: float,
    reps: int,
    lapses: int,
) -> dict[str, Any]:
    """Handle new and learning cards."""
    now = datetime.now()

    if rating == AGAIN:
        # Back to first learning step
        due = now + timedelta(minutes=LEARNING_STEPS[0])
        return _result(due, 0.0, difficulty, reps, lapses, 'learning', 0)

    elif rating == HARD:
        # Second learning step (or repeat first if only one step)
        step = LEARNING_STEPS[min(1, len(LEARNING_STEPS) - 1)]
        due = now + timedelta(minutes=step)
        return _result(due, 0.0, difficulty, reps, lapses, 'learning', 0)

    elif rating == GOOD:
        # Graduate to review — first real interval: 1 day
        stability = 1.0
        due = now + timedelta(days=1)
        return _result(due, stability, difficulty, reps + 1, lapses, 'review', 1)

    elif rating == EASY:
        # Graduate fast — 4 day interval
        stability = 4.0
        difficulty = max(MIN_DIFFICULTY, difficulty - 1.0)
        due = now + timedelta(days=4)
        return _result(due, stability, difficulty, reps + 1, lapses, 'review', 4)

    return _result(now, 0.0, difficulty, reps, lapses, 'learning', 0)


def _schedule_review(
    rating: int,
    stability: float,
    difficulty: float,
    reps: int,
    lapses: int,
) -> dict[str, Any]:
    """Handle cards in review state."""
    now = datetime.now()
    interval = max(stability, 1.0)

    if rating == AGAIN:
        # Lapse — back to relearning
        new_difficulty = min(MAX_DIFFICULTY, difficulty + 2.0)
        due = now + timedelta(minutes=RELEARNING_STEPS[0])
        # Stability drops significantly on lapse
        new_stability = max(0.5, stability * 0.3)
        return _result(due, new_stability, new_difficulty, reps, lapses + 1, 'relearning', 0)

    elif rating == HARD:
        new_interval = interval * 1.2
        new_difficulty = min(MAX_DIFFICULTY, difficulty + 0.5)
        days = max(1, round(new_interval))
        due = now + timedelta(days=days)
        return _result(due, new_interval, new_difficulty, reps + 1, lapses, 'review', days)

    elif rating == GOOD:
        # Standard interval growth based on difficulty
        ease = _ease_from_difficulty(difficulty)
        new_interval = interval * ease
        days = max(1, round(new_interval))
        due = now + timedelta(days=days)
        return _result(due, new_interval, difficulty, reps + 1, lapses, 'review', days)

    elif rating == EASY:
        ease = _ease_from_difficulty(difficulty)
        new_interval = interval * ease * 1.3
        new_difficulty = max(MIN_DIFFICULTY, difficulty - 0.5)
        days = max(1, round(new_interval))
        due = now + timedelta(days=days)
        return _result(due, new_interval, new_difficulty, reps + 1, lapses, 'review', days)

    return _result(now, stability, difficulty, reps, lapses, 'review', 0)


def _schedule_relearning(
    rating: int,
    stability: float,
    difficulty: float,
    reps: int,
    lapses: int,
) -> dict[str, Any]:
    """Handle cards that lapsed and are being relearned."""
    now = datetime.now()

    if rating == AGAIN:
        due = now + timedelta(minutes=RELEARNING_STEPS[0])
        return _result(due, stability, difficulty, reps, lapses, 'relearning', 0)

    elif rating == HARD:
        due = now + timedelta(minutes=RELEARNING_STEPS[0])
        return _result(due, stability, difficulty, reps, lapses, 'relearning', 0)

    elif rating == GOOD:
        # Graduate back to review with reduced stability
        days = max(1, round(stability))
        due = now + timedelta(days=days)
        return _result(due, stability, difficulty, reps + 1, lapses, 'review', days)

    elif rating == EASY:
        # Graduate with a bonus
        days = max(1, round(stability * 1.5))
        new_difficulty = max(MIN_DIFFICULTY, difficulty - 0.5)
        due = now + timedelta(days=days)
        return _result(due, stability * 1.5, new_difficulty, reps + 1, lapses, 'review', days)

    return _result(now, stability, difficulty, reps, lapses, 'relearning', 0)


def _ease_from_difficulty(difficulty: float) -> float:
    """Convert difficulty (1-10) to an ease multiplier (1.3-3.0)."""
    # difficulty 1 -> ease 3.0 (easy cards grow fast)
    # difficulty 10 -> ease 1.3 (hard cards grow slow)
    return 3.0 - (difficulty - 1.0) * (1.7 / 9.0)


def _result(
    due: datetime,
    stability: float,
    difficulty: float,
    reps: int,
    lapses: int,
    state: str,
    scheduled_days: int,
) -> dict[str, Any]:
    return {
        'due_date': due.strftime('%Y-%m-%d %H:%M:%S'),
        'stability': round(stability, 2),
        'difficulty': round(max(MIN_DIFFICULTY, min(MAX_DIFFICULTY, difficulty)), 2),
        'reps': reps,
        'lapses': lapses,
        'state': state,
        'scheduled_days': scheduled_days,
    }


def schedule_all_ratings(card: dict[str, Any]) -> dict[int, dict[str, Any]]:
    """Compute schedule results for all 4 ratings at once. Returns dict {rating: result}."""
    return {r: schedule(card, r) for r in (AGAIN, HARD, GOOD, EASY)}


def _format_interval(result: dict[str, Any]) -> str:
    """Human-readable label from a schedule result."""
    days = result['scheduled_days']

    if days == 0:
        due = datetime.strptime(result['due_date'], '%Y-%m-%d %H:%M:%S')
        diff = due - datetime.now()
        minutes = max(1, round(diff.total_seconds() / 60))
        return f"{minutes}m"
    elif days == 1:
        return "1d"
    elif days < 30:
        return f"{days}d"
    elif days < 365:
        months = round(days / 30)
        return f"{months}mo"
    else:
        years = round(days / 365, 1)
        return f"{years}y"
