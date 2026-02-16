# Retain — Telegram Flashcard Bot

A spaced repetition flashcard bot for Telegram. Create cards by sending text or photos, organize them into decks, and review at optimal intervals so you never forget what you learn.

## How it works

1. **/start** — Register and see the main menu
2. **Add Card** — Send text (`front | back` or two lines) or a photo. Pick a deck, preview, save.
3. **Review Now** — The bot shows due cards one at a time. Tap "Show Answer", then rate how well you remembered (Again / Hard / Good / Easy). The scheduler adjusts the next review date based on your response.

### Card formats

```
question | answer              # pipe separator
question                       # newline separator
answer
```

Photos are stored as-is and shown during review.

### Card types

- **Basic** — front and back
- **Reverse** — automatically creates a flipped copy (back → front)

### Spaced repetition

The bot uses a custom SRS scheduler (SM-2 inspired) with these intervals:

| State | Again | Hard | Good | Easy |
|-------|-------|------|------|------|
| New/Learning | 1 min | 10 min | 1 day | 4 days |
| Review | relearn | ×1.2 | ×ease | ×ease ×1.3 |

Difficulty adjusts over time — cards you struggle with are shown more often.

## Setup

```bash
git clone <repo-url>
cd retain-tg-bot
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file:

```
TELEGRAM_BOT_TOKEN=your_token_here
```

Get a token from [@BotFather](https://t.me/BotFather) on Telegram.

Run:

```bash
python bot.py
```

## Project structure

```
bot.py                  Entry point, conversation handlers
config.py               Token, DB path, logging setup
database/
  schema.py             SQL table definitions (users, decks, cards)
  database.py           All DB operations
handlers/
  start.py              /start command, main menu
  cards.py              Add / save / edit card
  decks.py              Deck selection and creation
  flow_handlers.py      Content parsing, preview, navigation
  review.py             Review session flow
utils/
  constants.py          States, button layouts
  utils.py              Text/photo parsing, button builder
  srs.py                Spaced repetition scheduler
```

## Tech stack

- Python 3.10+
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) 22.x
- SQLite

## Roadmap

- [ ] Cloze card type (`{{c1::answer}}` syntax)
- [ ] My Decks — list, rename, delete decks
- [ ] Stats — cards reviewed, streak, upcoming reviews
- [ ] Daily review reminders via job queue
- [ ] Tutorial for new users
