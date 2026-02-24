"""SQLite-backed persistence for python-telegram-bot.

Stores user_data, chat_data, bot_data, and conversation states as JSON blobs
in dedicated tables. Uses the same DB file as the main application data.
"""

import json
import logging
import sqlite3

from telegram.ext import BasePersistence, PersistenceInput

logger = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS persistence_user_data (
    user_id INTEGER PRIMARY KEY,
    data TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS persistence_chat_data (
    chat_id INTEGER PRIMARY KEY,
    data TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS persistence_bot_data (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    data TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS persistence_conversations (
    handler_name TEXT NOT NULL,
    key TEXT NOT NULL,
    state TEXT,
    PRIMARY KEY (handler_name, key)
);
"""


class SQLitePersistence(BasePersistence):
    """Persist PTB state to SQLite — survives bot restarts."""

    def __init__(self, db_path: str) -> None:
        super().__init__(
            store_data=PersistenceInput(
                bot_data=True,
                chat_data=True,
                user_data=True,
                callback_data=False,
            ),
        )
        self.db_path = db_path
        self._init_tables()

    # ── Internals ────────────────────────────────────────────

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_tables(self) -> None:
        conn = self._conn()
        try:
            for stmt in _SCHEMA.strip().split(';'):
                stmt = stmt.strip()
                if stmt:
                    conn.execute(stmt)
            conn.commit()
        finally:
            conn.close()

    # ── Read ─────────────────────────────────────────────────

    async def get_bot_data(self) -> dict:
        conn = self._conn()
        try:
            row = conn.execute(
                "SELECT data FROM persistence_bot_data WHERE id = 1"
            ).fetchone()
            return json.loads(row['data']) if row else {}
        finally:
            conn.close()

    async def get_user_data(self) -> dict[int, dict]:
        conn = self._conn()
        try:
            rows = conn.execute(
                "SELECT user_id, data FROM persistence_user_data"
            ).fetchall()
            return {row['user_id']: json.loads(row['data']) for row in rows}
        finally:
            conn.close()

    async def get_chat_data(self) -> dict[int, dict]:
        conn = self._conn()
        try:
            rows = conn.execute(
                "SELECT chat_id, data FROM persistence_chat_data"
            ).fetchall()
            return {row['chat_id']: json.loads(row['data']) for row in rows}
        finally:
            conn.close()

    async def get_conversations(self, name: str) -> dict:
        conn = self._conn()
        try:
            rows = conn.execute(
                "SELECT key, state FROM persistence_conversations WHERE handler_name = ?",
                (name,),
            ).fetchall()
            result = {}
            for row in rows:
                key = tuple(json.loads(row['key']))
                state = json.loads(row['state'])
                result[key] = state
            return result
        finally:
            conn.close()

    async def get_callback_data(self) -> None:
        return None

    # ── Write ────────────────────────────────────────────────

    async def update_bot_data(self, data: dict) -> None:
        conn = self._conn()
        try:
            conn.execute(
                "INSERT INTO persistence_bot_data (id, data) VALUES (1, ?) "
                "ON CONFLICT(id) DO UPDATE SET data = excluded.data",
                (json.dumps(data),),
            )
            conn.commit()
        finally:
            conn.close()

    async def update_user_data(self, user_id: int, data: dict) -> None:
        conn = self._conn()
        try:
            conn.execute(
                "INSERT INTO persistence_user_data (user_id, data) VALUES (?, ?) "
                "ON CONFLICT(user_id) DO UPDATE SET data = excluded.data",
                (user_id, json.dumps(data)),
            )
            conn.commit()
        finally:
            conn.close()

    async def update_chat_data(self, chat_id: int, data: dict) -> None:
        conn = self._conn()
        try:
            conn.execute(
                "INSERT INTO persistence_chat_data (chat_id, data) VALUES (?, ?) "
                "ON CONFLICT(chat_id) DO UPDATE SET data = excluded.data",
                (chat_id, json.dumps(data)),
            )
            conn.commit()
        finally:
            conn.close()

    async def update_callback_data(self, data) -> None:
        pass

    async def update_conversation(
        self, name: str, key: tuple, new_state: object | None
    ) -> None:
        conn = self._conn()
        try:
            key_json = json.dumps(list(key))
            if new_state is None:
                conn.execute(
                    "DELETE FROM persistence_conversations "
                    "WHERE handler_name = ? AND key = ?",
                    (name, key_json),
                )
            else:
                conn.execute(
                    "INSERT INTO persistence_conversations (handler_name, key, state) "
                    "VALUES (?, ?, ?) "
                    "ON CONFLICT(handler_name, key) DO UPDATE SET state = excluded.state",
                    (name, key_json, json.dumps(new_state)),
                )
            conn.commit()
        finally:
            conn.close()

    # ── Refresh (no external source — no-ops) ────────────────

    async def refresh_user_data(self, user_id: int, user_data: dict) -> None:
        pass

    async def refresh_chat_data(self, chat_id: int, chat_data: dict) -> None:
        pass

    async def refresh_bot_data(self, bot_data: dict) -> None:
        pass

    # ── Drop ─────────────────────────────────────────────────

    async def drop_user_data(self, user_id: int) -> None:
        conn = self._conn()
        try:
            conn.execute(
                "DELETE FROM persistence_user_data WHERE user_id = ?",
                (user_id,),
            )
            conn.commit()
        finally:
            conn.close()

    async def drop_chat_data(self, chat_id: int) -> None:
        conn = self._conn()
        try:
            conn.execute(
                "DELETE FROM persistence_chat_data WHERE chat_id = ?",
                (chat_id,),
            )
            conn.commit()
        finally:
            conn.close()

    # ── Flush (all writes are immediate — no-op) ─────────────

    async def flush(self) -> None:
        pass
