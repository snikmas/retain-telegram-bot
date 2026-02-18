import html
from datetime import date
from typing import Any

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

import database.database as db
from utils.telegram_helpers import safe_edit_text, safe_send_text


def _forecast_lines(forecast: list[dict[str, Any]]) -> str:
    if not forecast:
        return "<i>No cards due in the next 7 days</i>"

    lines = []
    for entry in forecast:
        day = date.fromisoformat(entry['day'])
        day_label = day.strftime('%b %d')
        count = entry['count']
        lines.append(f"  {day_label}  \u00b7  {count} card{'s' if count != 1 else ''}")
    return '\n'.join(lines)


def _build_stats_text(user_id: int) -> str:
    stats = db.get_card_stats(user_id)
    forecast = db.get_forecast(user_id, days=7)
    return (
        f"<b>\U0001f4ca Stats</b>\n\n"
        f"\U0001f4da Total: <b>{stats['total']}</b>\n"
        f"\U0001f195 New: <b>{stats['new']}</b>\n"
        f"\U0001f4d6 Learning: <b>{stats['learning']}</b>\n"
        f"\u2705 Review: <b>{stats['review']}</b>\n"
        f"\U0001f504 Relearning: <b>{stats['relearning']}</b>\n\n"
        f"\U0001f514 Due today: <b>{stats['due_today']}</b>\n\n"
        f"<b>\U0001f4c5 Next 7 days</b>\n"
        f"{_forecast_lines(forecast)}"
    )


async def stats_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    text = _build_stats_text(update.effective_user.id)
    buttons = [[InlineKeyboardButton('Menu', callback_data='main_menu')]]
    await safe_edit_text(query, text, reply_markup=InlineKeyboardMarkup(buttons))


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = _build_stats_text(update.effective_user.id)
    buttons = [[InlineKeyboardButton('Menu', callback_data='main_menu')]]
    await safe_send_text(update.message, text, reply_markup=InlineKeyboardMarkup(buttons))
