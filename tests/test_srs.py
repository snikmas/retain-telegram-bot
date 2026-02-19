"""
Tests for utils/srs.py — pure Python, no Telegram, no DB, no async.
"""
from datetime import datetime, timedelta

import pytest

from utils.srs import (
    AGAIN, EASY, GOOD, HARD,
    MAX_DIFFICULTY, MIN_DIFFICULTY,
    _ease_from_difficulty, _format_interval,
    schedule, schedule_all_ratings,
)


# ── Shared helper ─────────────────────────────────────────────

def card(state='new', stability=0.0, difficulty=5.0, reps=0, lapses=0):
    """Build a minimal card dict the same way the DB would return one."""
    return {
        'state': state,
        'stability': stability,
        'difficulty': difficulty,
        'reps': reps,
        'lapses': lapses,
    }


# ── New / Learning state ──────────────────────────────────────

class TestLearningState:
    def test_again_stays_learning(self):
        r = schedule(card(), AGAIN)
        assert r['state'] == 'learning'
        assert r['scheduled_days'] == 0
        assert r['reps'] == 0

    def test_hard_stays_learning(self):
        r = schedule(card(), HARD)
        assert r['state'] == 'learning'
        assert r['scheduled_days'] == 0

    def test_good_graduates_to_review(self):
        r = schedule(card(), GOOD)
        assert r['state'] == 'review'
        assert r['scheduled_days'] == 1
        assert r['reps'] == 1

    def test_easy_graduates_with_4_day_interval(self):
        r = schedule(card(), EASY)
        assert r['state'] == 'review'
        assert r['scheduled_days'] == 4
        assert r['reps'] == 1

    def test_easy_reduces_difficulty(self):
        r = schedule(card(difficulty=5.0), EASY)
        assert r['difficulty'] < 5.0

    def test_again_does_not_change_difficulty(self):
        r = schedule(card(difficulty=5.0), AGAIN)
        assert r['difficulty'] == 5.0

    def test_learning_state_behaves_same_as_new(self):
        r_new = schedule(card(state='new'), GOOD)
        r_learning = schedule(card(state='learning'), GOOD)
        assert r_new['state'] == r_learning['state']
        assert r_new['scheduled_days'] == r_learning['scheduled_days']
        assert r_new['reps'] == r_learning['reps']

    def test_unknown_state_falls_back_to_learning(self):
        r = schedule(card(state='bogus'), GOOD)
        assert r['state'] == 'review'   # graduates just like 'new'
        assert r['scheduled_days'] == 1


# ── Review state ──────────────────────────────────────────────

class TestReviewState:
    def test_again_moves_to_relearning(self):
        r = schedule(card(state='review', stability=10.0), AGAIN)
        assert r['state'] == 'relearning'

    def test_again_increments_lapses(self):
        r = schedule(card(state='review', stability=10.0, lapses=2), AGAIN)
        assert r['lapses'] == 3

    def test_again_does_not_increment_reps(self):
        r = schedule(card(state='review', stability=10.0, reps=5), AGAIN)
        assert r['reps'] == 5

    def test_again_increases_difficulty(self):
        r = schedule(card(state='review', stability=10.0, difficulty=5.0), AGAIN)
        assert r['difficulty'] > 5.0

    def test_again_difficulty_clamped_at_max(self):
        r = schedule(card(state='review', stability=10.0, difficulty=9.5), AGAIN)
        assert r['difficulty'] <= MAX_DIFFICULTY

    def test_hard_stays_in_review(self):
        r = schedule(card(state='review', stability=10.0), HARD)
        assert r['state'] == 'review'

    def test_hard_grows_interval_by_1_2(self):
        r = schedule(card(state='review', stability=10.0), HARD)
        # 10 * 1.2 = 12
        assert r['scheduled_days'] == 12

    def test_hard_increases_difficulty(self):
        r = schedule(card(state='review', stability=10.0, difficulty=5.0), HARD)
        assert r['difficulty'] > 5.0

    def test_good_stays_in_review(self):
        r = schedule(card(state='review', stability=10.0), GOOD)
        assert r['state'] == 'review'

    def test_good_grows_interval(self):
        r = schedule(card(state='review', stability=10.0, difficulty=5.0), GOOD)
        assert r['scheduled_days'] > 10

    def test_good_does_not_change_difficulty(self):
        r = schedule(card(state='review', stability=10.0, difficulty=5.0), GOOD)
        assert r['difficulty'] == 5.0

    def test_easy_grows_interval_more_than_good(self):
        c = card(state='review', stability=10.0, difficulty=5.0)
        assert schedule(c, EASY)['scheduled_days'] > schedule(c, GOOD)['scheduled_days']

    def test_easy_reduces_difficulty(self):
        r = schedule(card(state='review', stability=10.0, difficulty=5.0), EASY)
        assert r['difficulty'] < 5.0

    def test_reps_incremented_on_hard_good_easy(self):
        for rating in (HARD, GOOD, EASY):
            r = schedule(card(state='review', stability=10.0, reps=3), rating)
            assert r['reps'] == 4, f"reps not incremented for rating={rating}"

    def test_min_interval_is_1_day_when_stability_zero(self):
        r = schedule(card(state='review', stability=0.0), GOOD)
        assert r['scheduled_days'] >= 1


# ── Relearning state ──────────────────────────────────────────

class TestRelearningState:
    def test_again_stays_relearning(self):
        r = schedule(card(state='relearning', stability=5.0), AGAIN)
        assert r['state'] == 'relearning'
        assert r['scheduled_days'] == 0

    def test_hard_stays_relearning(self):
        r = schedule(card(state='relearning', stability=5.0), HARD)
        assert r['state'] == 'relearning'
        assert r['scheduled_days'] == 0

    def test_good_graduates_to_review(self):
        r = schedule(card(state='relearning', stability=5.0), GOOD)
        assert r['state'] == 'review'
        assert r['reps'] == 1

    def test_good_interval_based_on_stability(self):
        r = schedule(card(state='relearning', stability=8.0), GOOD)
        assert r['scheduled_days'] == 8

    def test_easy_graduates_to_review(self):
        r = schedule(card(state='relearning', stability=5.0), EASY)
        assert r['state'] == 'review'

    def test_easy_interval_bigger_than_good(self):
        c = card(state='relearning', stability=10.0)
        assert schedule(c, EASY)['scheduled_days'] >= schedule(c, GOOD)['scheduled_days']

    def test_easy_reduces_difficulty(self):
        r = schedule(card(state='relearning', stability=5.0, difficulty=5.0), EASY)
        assert r['difficulty'] < 5.0

    def test_again_hard_do_not_change_reps(self):
        for rating in (AGAIN, HARD):
            r = schedule(card(state='relearning', stability=5.0, reps=4), rating)
            assert r['reps'] == 4


# ── Difficulty clamping ───────────────────────────────────────

class TestDifficultyClamping:
    def test_difficulty_never_below_min_on_easy(self):
        r = schedule(card(state='review', stability=10.0, difficulty=1.0), EASY)
        assert r['difficulty'] >= MIN_DIFFICULTY

    def test_difficulty_never_above_max_on_again(self):
        r = schedule(card(state='review', stability=10.0, difficulty=10.0), AGAIN)
        assert r['difficulty'] <= MAX_DIFFICULTY

    def test_result_difficulty_always_in_range(self):
        states = ['new', 'review', 'relearning']
        ratings = [AGAIN, HARD, GOOD, EASY]
        for state in states:
            for rating in ratings:
                r = schedule(card(state=state, stability=5.0), rating)
                assert MIN_DIFFICULTY <= r['difficulty'] <= MAX_DIFFICULTY, (
                    f"state={state} rating={rating} difficulty={r['difficulty']}"
                )


# ── _ease_from_difficulty ─────────────────────────────────────

class TestEaseFromDifficulty:
    def test_min_difficulty_gives_max_ease(self):
        assert _ease_from_difficulty(1.0) == pytest.approx(3.0)

    def test_max_difficulty_gives_min_ease(self):
        assert _ease_from_difficulty(10.0) == pytest.approx(1.3)

    def test_mid_difficulty_is_between_bounds(self):
        ease = _ease_from_difficulty(5.5)
        assert 1.3 < ease < 3.0

    def test_ease_decreases_as_difficulty_increases(self):
        assert _ease_from_difficulty(3.0) > _ease_from_difficulty(7.0)


# ── schedule_all_ratings ──────────────────────────────────────

class TestScheduleAllRatings:
    def test_returns_all_four_keys(self):
        results = schedule_all_ratings(card(state='review', stability=10.0))
        assert set(results.keys()) == {AGAIN, HARD, GOOD, EASY}

    def test_each_result_has_required_fields(self):
        required = {'due_date', 'stability', 'difficulty', 'reps', 'lapses', 'state', 'scheduled_days'}
        for r in schedule_all_ratings(card()).values():
            assert required <= r.keys()

    def test_intervals_ordered_again_lt_good_lt_easy_on_review(self):
        results = schedule_all_ratings(card(state='review', stability=10.0, difficulty=5.0))
        assert results[AGAIN]['scheduled_days'] < results[GOOD]['scheduled_days']
        assert results[GOOD]['scheduled_days'] <= results[EASY]['scheduled_days']

    def test_hard_interval_between_again_and_good(self):
        results = schedule_all_ratings(card(state='review', stability=10.0))
        assert results[AGAIN]['scheduled_days'] <= results[HARD]['scheduled_days']
        assert results[HARD]['scheduled_days'] <= results[GOOD]['scheduled_days']


# ── _format_interval ──────────────────────────────────────────

def _make_result(scheduled_days: int, future_minutes: int = 0) -> dict:
    """Build a minimal result dict for _format_interval."""
    due = datetime.now() + timedelta(minutes=future_minutes)
    return {'scheduled_days': scheduled_days, 'due_date': due.strftime('%Y-%m-%d %H:%M:%S')}


class TestFormatInterval:
    def test_zero_days_shows_minutes(self):
        result = _make_result(scheduled_days=0, future_minutes=5)
        assert _format_interval(result) == '5m'

    def test_zero_days_past_due_date_shows_1m(self):
        past = datetime.now() - timedelta(minutes=30)
        result = {'scheduled_days': 0, 'due_date': past.strftime('%Y-%m-%d %H:%M:%S')}
        assert _format_interval(result) == '1m'

    def test_1_day(self):
        assert _format_interval(_make_result(1)) == '1d'

    def test_15_days(self):
        assert _format_interval(_make_result(15)) == '15d'

    def test_29_days_stays_as_days(self):
        assert _format_interval(_make_result(29)) == '29d'

    def test_30_days_converts_to_months(self):
        assert _format_interval(_make_result(30)) == '1mo'

    def test_60_days_is_2_months(self):
        assert _format_interval(_make_result(60)) == '2mo'

    def test_364_days_stays_as_months(self):
        label = _format_interval(_make_result(364))
        assert label.endswith('mo')

    def test_365_days_converts_to_years(self):
        assert _format_interval(_make_result(365)) == '1.0y'
