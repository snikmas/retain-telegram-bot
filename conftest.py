# Makes the project root importable when running: pytest

import pytest

import database.database as db


@pytest.fixture()
def tdb(tmp_path, monkeypatch):
    """Patch DB_PATH to a fresh temp file and initialise the schema.

    Shared across test modules — import in test files that need a clean DB.
    """
    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr(db, 'DB_PATH', db_path)
    import database.database as _db
    monkeypatch.setattr(_db, 'DB_PATH', db_path)
    db.init_db()
    return db_path
