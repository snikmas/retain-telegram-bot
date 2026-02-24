"""Tests for database/persistence.py — SQLite-backed PTB persistence."""

import json
import pytest
import pytest_asyncio

from database.persistence import SQLitePersistence


@pytest.fixture()
def persistence(tmp_path):
    db_path = str(tmp_path / "persist_test.db")
    return SQLitePersistence(db_path)


# ── Bot data ─────────────────────────────────────────────────

@pytest.mark.asyncio
class TestBotData:
    async def test_empty_on_start(self, persistence):
        assert await persistence.get_bot_data() == {}

    async def test_update_and_read(self, persistence):
        await persistence.update_bot_data({"key": "value"})
        assert await persistence.get_bot_data() == {"key": "value"}

    async def test_overwrite(self, persistence):
        await persistence.update_bot_data({"a": 1})
        await persistence.update_bot_data({"b": 2})
        assert await persistence.get_bot_data() == {"b": 2}


# ── User data ────────────────────────────────────────────────

@pytest.mark.asyncio
class TestUserData:
    async def test_empty_on_start(self, persistence):
        assert await persistence.get_user_data() == {}

    async def test_update_and_read(self, persistence):
        await persistence.update_user_data(111, {"name": "Alice"})
        result = await persistence.get_user_data()
        assert result == {111: {"name": "Alice"}}

    async def test_multiple_users(self, persistence):
        await persistence.update_user_data(1, {"a": 1})
        await persistence.update_user_data(2, {"b": 2})
        result = await persistence.get_user_data()
        assert result == {1: {"a": 1}, 2: {"b": 2}}

    async def test_overwrite_user(self, persistence):
        await persistence.update_user_data(1, {"v": 1})
        await persistence.update_user_data(1, {"v": 2})
        result = await persistence.get_user_data()
        assert result[1] == {"v": 2}

    async def test_drop_user(self, persistence):
        await persistence.update_user_data(1, {"a": 1})
        await persistence.drop_user_data(1)
        assert await persistence.get_user_data() == {}


# ── Chat data ────────────────────────────────────────────────

@pytest.mark.asyncio
class TestChatData:
    async def test_empty_on_start(self, persistence):
        assert await persistence.get_chat_data() == {}

    async def test_update_and_read(self, persistence):
        await persistence.update_chat_data(100, {"topic": "test"})
        result = await persistence.get_chat_data()
        assert result == {100: {"topic": "test"}}

    async def test_drop_chat(self, persistence):
        await persistence.update_chat_data(100, {"x": 1})
        await persistence.drop_chat_data(100)
        assert await persistence.get_chat_data() == {}


# ── Conversations ────────────────────────────────────────────

@pytest.mark.asyncio
class TestConversations:
    async def test_empty_on_start(self, persistence):
        assert await persistence.get_conversations("add_card") == {}

    async def test_store_and_read(self, persistence):
        await persistence.update_conversation("add_card", (111, 222), 2)
        result = await persistence.get_conversations("add_card")
        assert result == {(111, 222): 2}

    async def test_delete_on_none(self, persistence):
        await persistence.update_conversation("review", (1, 2), 3)
        await persistence.update_conversation("review", (1, 2), None)
        assert await persistence.get_conversations("review") == {}

    async def test_multiple_handlers(self, persistence):
        await persistence.update_conversation("add_card", (1, 1), 1)
        await persistence.update_conversation("review", (1, 1), 5)
        assert await persistence.get_conversations("add_card") == {(1, 1): 1}
        assert await persistence.get_conversations("review") == {(1, 1): 5}

    async def test_update_existing(self, persistence):
        await persistence.update_conversation("add_card", (1, 1), 1)
        await persistence.update_conversation("add_card", (1, 1), 3)
        result = await persistence.get_conversations("add_card")
        assert result == {(1, 1): 3}


# ── Callback data (disabled, returns None) ────────────────────

@pytest.mark.asyncio
class TestCallbackData:
    async def test_returns_none(self, persistence):
        assert await persistence.get_callback_data() is None


# ── Flush (no-op, should not raise) ──────────────────────────

@pytest.mark.asyncio
class TestFlush:
    async def test_flush_no_error(self, persistence):
        await persistence.flush()
