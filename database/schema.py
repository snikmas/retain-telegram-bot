# ======================= DECKS ==========================

deck_schema = '''
    CREATE TABLE IF NOT EXISTS decks (
        deck_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        deck_name TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
    )
'''

# ======================= CARDS ==========================

card_schema = '''
    CREATE TABLE IF NOT EXISTS cards (
        card_id INTEGER PRIMARY KEY AUTOINCREMENT,
        deck_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        
        -- Card content
        front TEXT NOT NULL,
        back TEXT NOT NULL,
        card_type TEXT DEFAULT 'basic',
        content_type TEXT DEFAULT 'text',
        
        -- SRS parameters (for FSRS algorithm)
        state TEXT DEFAULT 'new',
        due_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        stability REAL DEFAULT 0.0,
        difficulty REAL DEFAULT 5.0,
        elapsed_days INTEGER DEFAULT 0,
        scheduled_days INTEGER DEFAULT 0,
        reps INTEGER DEFAULT 0,
        lapses INTEGER DEFAULT 0,
        
        -- Metadata
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        
        -- Foreign key relationship
        FOREIGN KEY (deck_id) REFERENCES decks(deck_id) ON DELETE CASCADE
    )
'''

# ======================= USERS ==========================

user_schema = '''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,

        default_deck_id INTEGER,
        default_card_type TEXT DEFAULT 'basic',

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (default_deck_id) REFERENCES decks(deck_id)
    )
'''