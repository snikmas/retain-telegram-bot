# Retain — Telegram Flashcard Bot

A spaced repetition flashcard bot for Telegram. Create cards by sending text or photos, organize them into decks, and review at optimal intervals.

## Features

- **Add cards** — text (`front | back` or two lines) or photo; preview before saving
- **Card types** — Basic (one direction) or Reverse (auto-creates a flipped copy)
- **My Decks** — paginated list of decks; tap a deck to see its cards
- **Deck management** — rename or delete a deck; edit or delete individual cards
- **Review** — due cards sorted by state; deck picker when cards span multiple decks
- **Stats** — counts by state, 7-day forecast
- **Commands** — `/start`, `/review`, `/stats`, `/decks`, `/help`, `/cancel`

## Spaced repetition

Custom SM-2-inspired scheduler. Card states: `new → learning → review ⇄ relearning`.

| State | Again | Hard | Good | Easy |
|-------|-------|------|------|------|
| New / Learning | 1 min | 10 min | 1 day | 4 days |
| Review | relearn (10 min) | ×1.2 | ×ease | ×ease ×1.3 |
| Relearning | 10 min | 10 min | back to review | back + bonus |

Ease factor derived from difficulty (1–10 scale): easy cards grow fast, hard cards grow slow.

## Setup

```bash
git clone <repo-url>
cd retain-tg-bot
python -m venv myvenv
source myvenv/bin/activate
pip install -r requirements.txt
```

Create `.env`:

```
TELEGRAM_BOT_TOKEN=your_token_here
# PROXY_URL=socks5://... (optional)
```

Get a token from [@BotFather](https://t.me/BotFather).

```bash
python bot.py
```

The SQLite database (`retain.db`) is created automatically on first run.

## Project structure

```
bot.py                    Entry point — registers all handlers
config.py                 Token and DB path from .env
database/
  schema.py               SQL table definitions (users, decks, cards + indexes)
  database.py             All DB operations
handlers/
  start.py                /start, main menu
  cards.py                Add-card flow (entry, save, change settings)
  decks.py                Deck selection and creation during card flow
  flow_handlers.py        Content parsing, preview, navigation helpers
  review.py               Review session with deck picker
  stats.py                Stats display and 7-day forecast
  help.py                 Help screen
  decks_menu.py           My Decks list (paginated, clickable buttons)
  manage.py               Card edit/delete, deck rename/delete
utils/
  constants.py            Conversation states, shared button layouts
  utils.py                Text/photo parsing, button builder
  srs.py                  Spaced repetition scheduler
  telegram_helpers.py     Safe wrappers for Telegram API calls
```

## Tech stack

- Python 3.10+
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) 22.x
- SQLite (via stdlib `sqlite3`)
