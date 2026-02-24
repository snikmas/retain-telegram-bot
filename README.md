# Retain — Telegram Flashcard Bot

Spaced repetition flashcards inside Telegram. Send text or photos, organize into decks, review at scientifically optimal intervals.

---

## Quick start (user)

1. Send `/start`
2. Tap **New Card**, send `front | back` (or two lines)
3. Choose a deck, tap **Save**
4. Tap **Review** when cards are due

---

## Features

| Feature | Details |
|---------|---------|
| Card types | **Basic** (one direction) · **Reverse** (auto-creates a flipped copy) |
| Content | Plain text or photo with caption |
| Card format | `front \| back` or two lines; `|` takes priority |
| Decks | Create, rename, delete; paginated list |
| Card management | Edit content, delete; accessible from deck view |
| Review | Deck picker when cards span multiple decks; edit card mid-review |
| Stats | Counts by state (new / learning / review / relearning) + 7-day forecast |
| Commands | `/start` `/review` `/stats` `/decks` `/help` `/cancel` `/clear` |

---

## Spaced repetition

Custom SM-2-inspired scheduler. States: `new → learning → review ⇄ relearning`

| State | Again (1) | Hard (2) | Good (3) | Easy (4) |
|-------|-----------|---------|---------|---------|
| New / Learning | 1 min | 10 min | 1 day | 4 days |
| Review | relearn 10 min | ×1.2 | ×ease | ×ease ×1.3 |
| Relearning | 10 min | 10 min | back to review | back + bonus |

Ease is derived from difficulty (1–10): difficulty=1 → ease=3.0 (fast growth), difficulty=10 → ease=1.3 (slow growth).

---

## Setup

```bash
git clone <repo-url>
cd retain-tg-bot
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create `.env` in the project root:

```
TELEGRAM_BOT_TOKEN=your_token_here
DB_PATH=retain.db          # optional, defaults to retain.db
PROXY_URL=                 # optional HTTP proxy
```

Get a token from [@BotFather](https://t.me/BotFather).

```bash
python bot.py
```

The SQLite database is created automatically on first run.

---

## Running tests

```bash
pytest tests/
pytest tests/ -v          # verbose
pytest tests/test_srs.py  # SRS logic only
```

255+ tests covering SRS scheduler, all DB operations, and text/photo parsing. Handlers are not tested (Telegram API is not mocked).

---

## Project structure

```
bot.py                      Entry point — handler registration
config.py                   Token, DB path, proxy from .env (no side-effects)
database/
  schema.py                 DDL: users, decks, cards, indexes
  database.py               All DB operations + get_db() context manager
handlers/
  start.py                  /start, main menu, /clear, force_start fallback
  cards.py                  Add-card flow: entry, save, type/deck settings
  flow_handlers.py          Content parsing, card preview, navigation
  decks.py                  Deck picker and creation inside add-card flow
  decks_menu.py             My Decks list (paginated)
  manage.py                 Edit/delete cards; rename/delete decks
  review.py                 Review session: show front → rate → next
  stats.py                  Stats and 7-day forecast
  help.py                   Static help screen
utils/
  constants.py              ConversationHandler states, button constants
  srs.py                    SM-2 scheduler: schedule(), schedule_all_ratings()
  telegram_helpers.py       safe_edit_text / safe_send_text / safe_send_photo / safe_delete
  utils.py                  parse_text(), parse_photo(), get_buttons()
tests/
  test_srs.py               95 tests — state transitions, intervals, ease
  test_database.py          130+ tests — CRUD, reverse cards, stats, forecast
  test_utils.py             30+ tests — text/photo parsing
```

---

## Tech stack

- Python 3.10+
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) 22.x
- SQLite via stdlib `sqlite3`
- python-dotenv
- pytest

---

## Known limitations

- No daily review reminders (users forget the bot exists)
- `elapsed_days` is always stored as 0 — low impact now, affects long-term SRS accuracy
- No bulk import (CSV / Anki)
- Bot restart during an active review loses session state
- Per-call SQLite connections; not designed for concurrent multi-user load
