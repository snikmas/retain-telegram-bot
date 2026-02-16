
# ==================== SYSTEM IMPORTS ====================
from dotenv import load_dotenv
import os

# ===================== UTILS IMPORT =====================
import logging
import sqlite3
from contextlib import contextmanager

# ==================== FOLDERS IMPORT ====================
from database.schema import user_schema, deck_schema, card_schema
# ========================================================

load_dotenv()

logger = logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)





# USER COMMANDS ============================================

def create_user(user_id, username, first_name):
    with get_db() as conn:
        cursor = conn.cursor()

        create_user_schema = 'INSERT INTO users (user_id, username, name) VALUES (?, ?, ?)'

        cursor.execute(create_user_schema, (user_id, username, first_name))
        logging.info(f"Created uesr: {user_id}")
    pass

def get_user(user_id):
    with get_db() as conn:
        cursor = conn.cursor()

        find_user_query = 'SELECT * FROM users WHERE user_id=?'

        cursor.execute(find_user_query, (user_id,))
        conn.commit()
        
        return cursor.fetchone()  

def get_user_defaults(user_id):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT default_deck_id, default_card_type FROM users WHERE user_id = ?', (user_id,))
        
        row = cursor.fetchone()
        if row:
            return {
                'deck_id': row['default_deck_id'],
                'card_type': row['default_card_type']
            }
        return None

# ============================================================
# DECKS COMMANDS =============================================

def get_all_decks(user_id):
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute('SELECT deck_id, deck_name FROM decks WHERE user_id = ?', (user_id,))
        rows = cursor.fetchall()

        if rows:
            return [{'id': row['deck_id'], 'name': row['deck_name']} for row in rows]
        else: 
            return []

def get_deck_id(user_id, deck_name):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT deck_id FROM decks WHERE user_id = ? AND deck_name = ?", (user_id, deck_name))
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
        else:
            return None
        

def create_deck_db(user_id, deck_name):
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute('INSERT INTO decks (user_id, deck_name) VALUES (?, ?)', (user_id, deck_name))


# ============================================================
# CARDS COMMANDS =============================================
def save_card(card_dict, card_type, deck_id, user_id):
    """card_dict is always {'front': ..., 'back': ...}"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        front = card_dict['front']
        back = card_dict['back']
        
        # Save original
        cursor.execute(
            "INSERT INTO cards (front, back, card_type, deck_id, user_id) VALUES (?, ?, ?, ?, ?)",
            (front, back, card_type, deck_id, user_id)
        )
        
        # If reverse, save flipped version too
        if card_type.lower() == 'reverse':
            cursor.execute(
                "INSERT INTO cards (front, back, card_type, deck_id, user_id) VALUES (?, ?, ?, ?, ?)",
                (back, front, card_type, deck_id, user_id)
            )

# ============================================================

@contextmanager
def get_db():
    conn = sqlite3.connect('retain.db') # later have to create a folder for it
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
        cursor = conn.cursor()
        conn.execute(user_schema)
        conn.execute(deck_schema)
        conn.execute(card_schema)
        