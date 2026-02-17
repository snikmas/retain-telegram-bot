import logging
import sqlite3
from contextlib import contextmanager

from database.schema import user_schema, deck_schema, card_schema
from config import DB_PATH


# USER COMMANDS ============================================

def create_user(user_id, username, first_name):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO users (user_id, username, name) VALUES (?, ?, ?)',
            (user_id, username, first_name)
        )
        logging.info(f"Created user: {user_id}")


def get_user(user_id):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE user_id=?', (user_id,))
        return cursor.fetchone()


def get_user_defaults(user_id):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT default_deck_id, default_card_type FROM users WHERE user_id = ?',
            (user_id,)
        )
        row = cursor.fetchone()
        if row:
            return {
                'deck_id': row['default_deck_id'],
                'card_type': row['default_card_type']
            }
        return None


def update_user_defaults(user_id, deck_id=None, card_type=None):
    with get_db() as conn:
        cursor = conn.cursor()
        if deck_id is not None:
            cursor.execute(
                'UPDATE users SET default_deck_id = ? WHERE user_id = ?',
                (deck_id, user_id)
            )
        if card_type is not None:
            cursor.execute(
                'UPDATE users SET default_card_type = ? WHERE user_id = ?',
                (card_type, user_id)
            )
        logging.info(f"Updated defaults for user {user_id}: deck={deck_id}, type={card_type}")


# DECKS COMMANDS =============================================

def get_all_decks(user_id):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT deck_id, deck_name FROM decks WHERE user_id = ?', (user_id,))
        rows = cursor.fetchall()
        return [{'id': row['deck_id'], 'name': row['deck_name']} for row in rows]


def get_deck_id(user_id, deck_name):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT deck_id FROM decks WHERE user_id = ? AND deck_name = ?",
            (user_id, deck_name)
        )
        row = cursor.fetchone()
        if row:
            return row['deck_id']


def get_deck_name(deck_id):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT deck_name FROM decks WHERE deck_id = ?", (deck_id,))
        row = cursor.fetchone()
        if row:
            return row['deck_name']
        return None


def create_deck_db(user_id, deck_name):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO decks (user_id, deck_name) VALUES (?, ?)',
            (user_id, deck_name)
        )
        return cursor.lastrowid


def get_decks_with_stats(user_id):
    """Get all decks with card count and due count in a single query."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT d.deck_id, d.deck_name,
                      COUNT(c.card_id) AS card_count,
                      SUM(CASE WHEN c.due_date <= datetime('now') THEN 1 ELSE 0 END) AS due_count
               FROM decks d
               LEFT JOIN cards c ON c.deck_id = d.deck_id
               WHERE d.user_id = ?
               GROUP BY d.deck_id
               ORDER BY d.deck_name
            """,
            (user_id,)
        )
        return [dict(row) for row in cursor.fetchall()]


# CARDS COMMANDS =============================================

def save_card(card_dict, card_type, deck_id, user_id):
    """card_dict is always {'front': ..., 'back': ..., optional 'is_photo': bool}"""
    with get_db() as conn:
        cursor = conn.cursor()

        front = card_dict['front']
        back = card_dict['back']
        content_type = 'photo' if card_dict.get('is_photo') else 'text'

        cursor.execute(
            "INSERT INTO cards (front, back, card_type, content_type, deck_id, user_id) VALUES (?, ?, ?, ?, ?, ?)",
            (front, back, card_type, content_type, deck_id, user_id)
        )

        if card_type.lower() == 'reverse':
            cursor.execute(
                "INSERT INTO cards (front, back, card_type, content_type, deck_id, user_id) VALUES (?, ?, ?, ?, ?, ?)",
                (back, front, card_type, content_type, deck_id, user_id)
            )


# REVIEW COMMANDS ============================================

def get_due_cards(user_id):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT card_id, front, back, card_type, content_type, state,
                      stability, difficulty, reps, lapses, deck_id
               FROM cards
               WHERE user_id = ? AND due_date <= datetime('now')
               ORDER BY
                   CASE state WHEN 'new' THEN 0 WHEN 'learning' THEN 1
                              WHEN 'relearning' THEN 2 ELSE 3 END,
                   due_date
            """,
            (user_id,)
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def update_card_srs(card_id, due_date, stability, difficulty, reps, lapses, state, scheduled_days):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """UPDATE cards
               SET due_date = ?, stability = ?, difficulty = ?,
                   reps = ?, lapses = ?, state = ?, scheduled_days = ?,
                   updated_at = datetime('now')
               WHERE card_id = ?
            """,
            (due_date, stability, difficulty, reps, lapses, state, scheduled_days, card_id)
        )


# STATS COMMANDS =============================================

def get_card_stats(user_id):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT
                   COUNT(*) AS total,
                   SUM(state = 'new') AS new,
                   SUM(state = 'learning') AS learning,
                   SUM(state = 'review') AS review,
                   SUM(state = 'relearning') AS relearning,
                   SUM(due_date <= datetime('now')) AS due_today
               FROM cards WHERE user_id = ?
            """,
            (user_id,)
        )
        row = cursor.fetchone()
        return {k: (row[k] or 0) for k in row.keys()}


def get_forecast(user_id, days=7):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT date(due_date) AS day, COUNT(*) AS cnt
               FROM cards
               WHERE user_id = ?
                 AND due_date > datetime('now')
                 AND due_date <= datetime('now', ? || ' days')
               GROUP BY date(due_date)
               ORDER BY day
            """,
            (user_id, str(days))
        )
        rows = {row['day']: row['cnt'] for row in cursor.fetchall()}

    from datetime import date, timedelta
    today = date.today()
    return [
        {'day': (today + timedelta(d)).isoformat(), 'count': rows.get((today + timedelta(d)).isoformat(), 0)}
        for d in range(1, days + 1)
    ]


# DB CONNECTION ==============================================

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        conn.execute(user_schema)
        conn.execute(deck_schema)
        conn.execute(card_schema)
