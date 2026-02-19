"""
Tests for database/database.py.

Uses a real SQLite file in a pytest tmp_path so every test gets an isolated DB.
No Telegram objects, no async — pure DB logic.
"""
import sqlite3
import pytest

import database.database as db


# ── Fixture ───────────────────────────────────────────────────

@pytest.fixture()
def tdb(tmp_path, monkeypatch):
    """Patch DB_PATH to a fresh temp file and initialise the schema."""
    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr(db, 'DB_PATH', db_path)
    # also patch the import inside get_db's closure
    import database.database as _db
    monkeypatch.setattr(_db, 'DB_PATH', db_path)
    db.init_db()
    return db_path


# ── Helpers ───────────────────────────────────────────────────

def _raw(db_path: str, sql: str, params=()):
    """Run a raw query against the test DB and return fetchall."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.execute(sql, params)
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── User ──────────────────────────────────────────────────────

class TestUser:
    def test_create_and_get(self, tdb):
        db.create_user(1, 'alice', 'Alice')
        user = db.get_user(1)
        assert user is not None
        assert user['user_id'] == 1
        assert user['username'] == 'alice'
        assert user['name'] == 'Alice'

    def test_get_nonexistent_returns_none(self, tdb):
        assert db.get_user(999) is None

    def test_get_user_defaults_fresh_user(self, tdb):
        db.create_user(2, None, 'Bob')
        defaults = db.get_user_defaults(2)
        assert defaults is not None
        assert defaults['deck_id'] is None
        assert defaults['card_type'] == 'basic'

    def test_update_defaults_deck(self, tdb):
        db.create_user(3, None, 'Carol')
        deck_id = db.create_deck_db(3, 'French')
        db.update_user_defaults(3, deck_id=deck_id)
        assert db.get_user_defaults(3)['deck_id'] == deck_id

    def test_update_defaults_card_type(self, tdb):
        db.create_user(4, None, 'Dan')
        db.update_user_defaults(4, card_type='reverse')
        assert db.get_user_defaults(4)['card_type'] == 'reverse'

    def test_clear_default_deck_sets_null(self, tdb):
        db.create_user(5, None, 'Eve')
        deck_id = db.create_deck_db(5, 'Spanish')
        db.update_user_defaults(5, deck_id=deck_id)
        assert db.get_user_defaults(5)['deck_id'] == deck_id

        db.clear_default_deck(5)
        assert db.get_user_defaults(5)['deck_id'] is None

    def test_update_defaults_none_deck_id_does_not_clear(self, tdb):
        """Regression: update_user_defaults(deck_id=None) must NOT clear the stored deck."""
        db.create_user(6, None, 'Frank')
        deck_id = db.create_deck_db(6, 'German')
        db.update_user_defaults(6, deck_id=deck_id)
        # calling with deck_id=None should be a no-op for that column
        db.update_user_defaults(6, deck_id=None)
        assert db.get_user_defaults(6)['deck_id'] == deck_id


# ── Deck ──────────────────────────────────────────────────────

class TestDeck:
    def test_create_returns_id(self, tdb):
        db.create_user(10, None, 'U')
        deck_id = db.create_deck_db(10, 'Vocab')
        assert isinstance(deck_id, int)
        assert deck_id > 0

    def test_get_deck_name(self, tdb):
        db.create_user(11, None, 'U')
        deck_id = db.create_deck_db(11, 'History')
        assert db.get_deck_name(deck_id) == 'History'

    def test_get_deck_name_nonexistent(self, tdb):
        assert db.get_deck_name(9999) is None

    def test_get_all_decks(self, tdb):
        db.create_user(12, None, 'U')
        db.create_deck_db(12, 'A')
        db.create_deck_db(12, 'B')
        decks = db.get_all_decks(12)
        names = {d['name'] for d in decks}
        assert names == {'A', 'B'}

    def test_get_all_decks_empty(self, tdb):
        db.create_user(13, None, 'U')
        assert db.get_all_decks(13) == []

    def test_get_all_decks_isolated_per_user(self, tdb):
        db.create_user(14, None, 'U1')
        db.create_user(15, None, 'U2')
        db.create_deck_db(14, 'OnlyForU1')
        assert db.get_all_decks(15) == []

    def test_rename_deck(self, tdb):
        db.create_user(16, None, 'U')
        deck_id = db.create_deck_db(16, 'Old')
        db.rename_deck(deck_id, 16, 'New')
        assert db.get_deck_name(deck_id) == 'New'

    def test_delete_deck_removes_deck_and_cards(self, tdb):
        db.create_user(17, None, 'U')
        deck_id = db.create_deck_db(17, 'ToDelete')
        db.save_card({'front': 'q', 'back': 'a'}, 'basic', deck_id, 17)
        db.delete_deck(deck_id, 17)
        assert db.get_deck_name(deck_id) is None
        assert db.get_cards_in_deck(deck_id, 17) == []

    def test_get_decks_with_stats_card_count(self, tdb):
        db.create_user(18, None, 'U')
        deck_id = db.create_deck_db(18, 'Stats')
        db.save_card({'front': 'q1', 'back': 'a1'}, 'basic', deck_id, 18)
        db.save_card({'front': 'q2', 'back': 'a2'}, 'basic', deck_id, 18)
        decks = db.get_decks_with_stats(18)
        assert len(decks) == 1
        assert decks[0]['card_count'] == 2

    def test_get_decks_with_stats_due_count(self, tdb):
        db.create_user(19, None, 'U')
        deck_id = db.create_deck_db(19, 'Due')
        # Two cards with default due_date (= now, so immediately due)
        db.save_card({'front': 'q1', 'back': 'a1'}, 'basic', deck_id, 19)
        db.save_card({'front': 'q2', 'back': 'a2'}, 'basic', deck_id, 19)
        decks = db.get_decks_with_stats(19)
        assert decks[0]['due_count'] == 2


# ── Card ──────────────────────────────────────────────────────

class TestCard:
    def test_save_basic_card(self, tdb):
        db.create_user(20, None, 'U')
        deck_id = db.create_deck_db(20, 'D')
        db.save_card({'front': 'hello', 'back': 'world'}, 'basic', deck_id, 20)
        cards = db.get_cards_in_deck(deck_id, 20)
        assert len(cards) == 1
        assert cards[0]['front'] == 'hello'
        assert cards[0]['back'] == 'world'
        assert cards[0]['card_type'] == 'basic'
        assert cards[0]['content_type'] == 'text'

    def test_save_reverse_creates_two_cards(self, tdb):
        db.create_user(21, None, 'U')
        deck_id = db.create_deck_db(21, 'D')
        db.save_card({'front': 'cat', 'back': 'кот'}, 'reverse', deck_id, 21)
        cards = db.get_cards_in_deck(deck_id, 21)
        assert len(cards) == 2
        fronts = {c['front'] for c in cards}
        backs = {c['back'] for c in cards}
        assert fronts == {'cat', 'кот'}
        assert backs == {'cat', 'кот'}

    def test_save_photo_card(self, tdb):
        db.create_user(22, None, 'U')
        deck_id = db.create_deck_db(22, 'D')
        db.save_card({'front': 'file_id_123', 'back': 'a dog', 'is_photo': True}, 'basic', deck_id, 22)
        cards = db.get_cards_in_deck(deck_id, 22)
        assert cards[0]['content_type'] == 'photo'
        assert cards[0]['front'] == 'file_id_123'
        assert cards[0]['back'] == 'a dog'

    def test_get_card_returns_correct(self, tdb):
        db.create_user(23, None, 'U')
        deck_id = db.create_deck_db(23, 'D')
        db.save_card({'front': 'X', 'back': 'Y'}, 'basic', deck_id, 23)
        card_id = db.get_cards_in_deck(deck_id, 23)[0]['card_id']
        card = db.get_card(card_id, 23)
        assert card is not None
        assert card['front'] == 'X'
        assert card['back'] == 'Y'
        assert card['deck_id'] == deck_id

    def test_get_card_wrong_user_returns_none(self, tdb):
        db.create_user(24, None, 'U1')
        db.create_user(25, None, 'U2')
        deck_id = db.create_deck_db(24, 'D')
        db.save_card({'front': 'secret', 'back': 'data'}, 'basic', deck_id, 24)
        card_id = db.get_cards_in_deck(deck_id, 24)[0]['card_id']
        assert db.get_card(card_id, 25) is None  # wrong user

    def test_delete_card(self, tdb):
        db.create_user(26, None, 'U')
        deck_id = db.create_deck_db(26, 'D')
        db.save_card({'front': 'q', 'back': 'a'}, 'basic', deck_id, 26)
        card_id = db.get_cards_in_deck(deck_id, 26)[0]['card_id']
        db.delete_card(card_id, 26)
        assert db.get_cards_in_deck(deck_id, 26) == []

    def test_update_card_content(self, tdb):
        db.create_user(27, None, 'U')
        deck_id = db.create_deck_db(27, 'D')
        db.save_card({'front': 'old front', 'back': 'old back'}, 'basic', deck_id, 27)
        card_id = db.get_cards_in_deck(deck_id, 27)[0]['card_id']
        db.update_card_content(card_id, 27, 'new front', 'new back')
        card = db.get_card(card_id, 27)
        assert card['front'] == 'new front'
        assert card['back'] == 'new back'

    def test_update_card_content_syncs_reverse_sibling(self, tdb):
        """P-3: editing one card of a reverse pair must update the other."""
        db.create_user(28, None, 'U')
        deck_id = db.create_deck_db(28, 'D')
        db.save_card({'front': 'cat', 'back': 'кот'}, 'reverse', deck_id, 28)
        cards = db.get_cards_in_deck(deck_id, 28)
        # find the card whose front is 'cat'
        original = next(c for c in cards if c['front'] == 'cat')
        db.update_card_content(original['card_id'], 28, 'kitten', 'котёнок')
        updated = db.get_cards_in_deck(deck_id, 28)
        fronts = {c['front'] for c in updated}
        backs = {c['back'] for c in updated}
        assert fronts == {'kitten', 'котёнок'}
        assert backs == {'kitten', 'котёнок'}

    def test_update_card_content_reverse_sibling_not_found_is_safe(self, tdb):
        """If sibling was manually deleted, update_card_content must not crash."""
        db.create_user(29, None, 'U')
        deck_id = db.create_deck_db(29, 'D')
        db.save_card({'front': 'a', 'back': 'b'}, 'reverse', deck_id, 29)
        cards = db.get_cards_in_deck(deck_id, 29)
        sibling = next(c for c in cards if c['front'] == 'b')
        db.delete_card(sibling['card_id'], 29)
        original = next(c for c in cards if c['front'] == 'a')
        # Should not raise
        db.update_card_content(original['card_id'], 29, 'x', 'y')
        card = db.get_card(original['card_id'], 29)
        assert card['front'] == 'x'

    def test_update_card_caption_only_updates_back(self, tdb):
        """P-6: update_card_caption must not touch front (the file_id)."""
        db.create_user(30, None, 'U')
        deck_id = db.create_deck_db(30, 'D')
        db.save_card({'front': 'file_id_abc', 'back': 'old caption', 'is_photo': True}, 'basic', deck_id, 30)
        card_id = db.get_cards_in_deck(deck_id, 30)[0]['card_id']
        db.update_card_caption(card_id, 30, 'new caption')
        card = db.get_card(card_id, 30)
        assert card['front'] == 'file_id_abc'   # unchanged
        assert card['back'] == 'new caption'

    def test_update_card_caption_empty_string(self, tdb):
        db.create_user(31, None, 'U')
        deck_id = db.create_deck_db(31, 'D')
        db.save_card({'front': 'fid', 'back': 'caption', 'is_photo': True}, 'basic', deck_id, 31)
        card_id = db.get_cards_in_deck(deck_id, 31)[0]['card_id']
        db.update_card_caption(card_id, 31, '')
        assert db.get_card(card_id, 31)['back'] == ''


# ── Due cards ─────────────────────────────────────────────────

class TestDueCards:
    def test_new_cards_are_immediately_due(self, tdb):
        db.create_user(40, None, 'U')
        deck_id = db.create_deck_db(40, 'D')
        db.save_card({'front': 'q', 'back': 'a'}, 'basic', deck_id, 40)
        due = db.get_due_cards(40)
        assert len(due) == 1
        assert due[0]['front'] == 'q'

    def test_future_due_card_not_returned(self, tdb):
        db.create_user(41, None, 'U')
        deck_id = db.create_deck_db(41, 'D')
        db.save_card({'front': 'q', 'back': 'a'}, 'basic', deck_id, 41)
        card_id = db.get_cards_in_deck(deck_id, 41)[0]['card_id']
        # push due_date into the future
        with db.get_db() as conn:
            conn.execute(
                "UPDATE cards SET due_date = datetime('now', '+7 days') WHERE card_id = ?",
                (card_id,)
            )
        assert db.get_due_cards(41) == []

    def test_get_due_cards_filtered_by_deck(self, tdb):
        db.create_user(42, None, 'U')
        d1 = db.create_deck_db(42, 'D1')
        d2 = db.create_deck_db(42, 'D2')
        db.save_card({'front': 'in_d1', 'back': 'a'}, 'basic', d1, 42)
        db.save_card({'front': 'in_d2', 'back': 'a'}, 'basic', d2, 42)
        due = db.get_due_cards(42, deck_id=d1)
        assert len(due) == 1
        assert due[0]['front'] == 'in_d1'

    def test_due_cards_contain_required_fields(self, tdb):
        db.create_user(43, None, 'U')
        deck_id = db.create_deck_db(43, 'D')
        db.save_card({'front': 'f', 'back': 'b'}, 'basic', deck_id, 43)
        card = db.get_due_cards(43)[0]
        for field in ('card_id', 'front', 'back', 'state', 'stability',
                      'difficulty', 'reps', 'lapses', 'deck_id', 'due_date', 'scheduled_days'):
            assert field in card, f"missing field: {field}"

    def test_due_cards_isolated_per_user(self, tdb):
        db.create_user(44, None, 'U1')
        db.create_user(45, None, 'U2')
        d1 = db.create_deck_db(44, 'D')
        db.save_card({'front': 'q', 'back': 'a'}, 'basic', d1, 44)
        assert db.get_due_cards(45) == []

    def test_due_cards_order_new_before_review(self, tdb):
        """New cards must appear before review-state cards in the queue."""
        db.create_user(46, None, 'U')
        deck_id = db.create_deck_db(46, 'D')
        db.save_card({'front': 'review_card', 'back': 'a'}, 'basic', deck_id, 46)
        db.save_card({'front': 'new_card', 'back': 'b'}, 'basic', deck_id, 46)
        # promote first card to 'review' state
        review_id = db.get_cards_in_deck(deck_id, 46)[0]['card_id']
        with db.get_db() as conn:
            conn.execute("UPDATE cards SET state = 'review' WHERE card_id = ?", (review_id,))
        due = db.get_due_cards(46)
        assert due[0]['state'] == 'new'


# ── SRS update ────────────────────────────────────────────────

class TestSrsUpdate:
    def test_update_card_srs_persists_fields(self, tdb):
        db.create_user(50, None, 'U')
        deck_id = db.create_deck_db(50, 'D')
        db.save_card({'front': 'q', 'back': 'a'}, 'basic', deck_id, 50)
        card_id = db.get_cards_in_deck(deck_id, 50)[0]['card_id']
        db.update_card_srs(
            card_id,
            due_date='2099-01-01 00:00:00',
            stability=4.5,
            difficulty=3.2,
            reps=1,
            lapses=0,
            state='review',
            scheduled_days=7,
            elapsed_days=1,
        )
        card = db.get_card(card_id, 50)
        # get_card doesn't return srs fields, check via raw query
        rows = _raw(tdb,
            "SELECT stability, difficulty, reps, lapses, state, scheduled_days, elapsed_days "
            "FROM cards WHERE card_id = ?", (card_id,))
        r = rows[0]
        assert abs(r['stability'] - 4.5) < 1e-6
        assert abs(r['difficulty'] - 3.2) < 1e-6
        assert r['reps'] == 1
        assert r['lapses'] == 0
        assert r['state'] == 'review'
        assert r['scheduled_days'] == 7
        assert r['elapsed_days'] == 1


# ── Stats ─────────────────────────────────────────────────────

class TestStats:
    def test_card_stats_empty(self, tdb):
        db.create_user(60, None, 'U')
        stats = db.get_card_stats(60)
        assert stats['total'] == 0
        assert stats['due_today'] == 0

    def test_card_stats_counts(self, tdb):
        db.create_user(61, None, 'U')
        deck_id = db.create_deck_db(61, 'D')
        db.save_card({'front': 'a', 'back': 'b'}, 'basic', deck_id, 61)
        db.save_card({'front': 'c', 'back': 'd'}, 'basic', deck_id, 61)
        stats = db.get_card_stats(61)
        assert stats['total'] == 2
        assert stats['new'] == 2
        assert stats['due_today'] == 2

    def test_card_stats_due_today_excludes_future(self, tdb):
        db.create_user(62, None, 'U')
        deck_id = db.create_deck_db(62, 'D')
        db.save_card({'front': 'q', 'back': 'a'}, 'basic', deck_id, 62)
        card_id = db.get_cards_in_deck(deck_id, 62)[0]['card_id']
        with db.get_db() as conn:
            conn.execute(
                "UPDATE cards SET due_date = datetime('now', '+1 day') WHERE card_id = ?",
                (card_id,)
            )
        stats = db.get_card_stats(62)
        assert stats['total'] == 1
        assert stats['due_today'] == 0

    def test_card_stats_isolated_per_user(self, tdb):
        db.create_user(63, None, 'U1')
        db.create_user(64, None, 'U2')
        deck_id = db.create_deck_db(63, 'D')
        db.save_card({'front': 'q', 'back': 'a'}, 'basic', deck_id, 63)
        assert db.get_card_stats(64)['total'] == 0

    def test_forecast_returns_7_days(self, tdb):
        db.create_user(65, None, 'U')
        forecast = db.get_forecast(65, days=7)
        assert len(forecast) == 7

    def test_forecast_counts_future_cards(self, tdb):
        db.create_user(66, None, 'U')
        deck_id = db.create_deck_db(66, 'D')
        db.save_card({'front': 'q', 'back': 'a'}, 'basic', deck_id, 66)
        card_id = db.get_cards_in_deck(deck_id, 66)[0]['card_id']
        with db.get_db() as conn:
            conn.execute(
                "UPDATE cards SET due_date = datetime('now', '+3 days') WHERE card_id = ?",
                (card_id,)
            )
        forecast = db.get_forecast(66, days=7)
        total_future = sum(d['count'] for d in forecast)
        assert total_future == 1

    def test_forecast_does_not_count_already_due(self, tdb):
        """Cards due now (already overdue) should not appear in forecast."""
        db.create_user(67, None, 'U')
        deck_id = db.create_deck_db(67, 'D')
        db.save_card({'front': 'q', 'back': 'a'}, 'basic', deck_id, 67)
        forecast = db.get_forecast(67, days=7)
        assert sum(d['count'] for d in forecast) == 0
