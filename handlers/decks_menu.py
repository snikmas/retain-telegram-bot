from typing import Any

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, Message
from telegram.ext import ContextTypes

import database.database as db
from utils.telegram_helpers import safe_edit_text, safe_send_text

DECKS_PER_PAGE = 5


async def my_decks_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Entry point from main menu — show first page of decks."""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    decks = db.get_decks_with_stats(user_id)

    if not decks:
        await safe_edit_text(
            query,
            "\U0001f4da No decks yet\n\n"
            "Create your first card and a deck will appear here.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("\U0001f4dd New Card", callback_data='add_card')],
                [InlineKeyboardButton("\U0001f3e0 Menu", callback_data='main_menu')],
            ])
        )
        return

    context.user_data['_decks_cache'] = decks
    await _show_decks_page(query, context, page=0)


async def decks_page(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle page navigation."""
    query = update.callback_query
    await query.answer()

    page = int(query.data.split('_')[2])  # decks_page_N
    await _show_decks_page(query, context, page)


async def decks_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/decks slash command — send a fresh My Decks list."""
    user_id = update.effective_user.id
    decks = db.get_decks_with_stats(user_id)

    if not decks:
        await safe_send_text(
            update.message,
            "\U0001f4da No decks yet\n\n"
            "Create your first card and a deck will appear here.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("\U0001f4dd New Card", callback_data='add_card')],
                [InlineKeyboardButton("\U0001f3e0 Menu", callback_data='main_menu')],
            ])
        )
        return

    context.user_data['_decks_cache'] = decks
    await _send_decks_page(update.message, context, page=0)


# ── private helpers ──────────────────────────────────────────

def _deck_button(deck: dict[str, Any]) -> InlineKeyboardButton:
    """Build a single deck row button."""
    due = deck['due_count'] or 0
    total = deck['card_count'] or 0
    due_part = f"  \u2757 {due} due" if due > 0 else ""
    label = f"\U0001f4da {deck['deck_name']} \u00b7 {total} cards{due_part}"
    return InlineKeyboardButton(label, callback_data=f"deck_open_{deck['deck_id']}")


def _build_decks_markup(
    decks: list[dict[str, Any]],
    page: int,
    total_pages: int,
) -> tuple[str, InlineKeyboardMarkup]:
    start = page * DECKS_PER_PAGE
    page_decks = decks[start:start + DECKS_PER_PAGE]

    if total_pages > 1:
        header = f"\U0001f4da My Decks ({page + 1}/{total_pages})"
    else:
        header = "\U0001f4da My Decks"

    buttons: list[list[InlineKeyboardButton]] = [
        [_deck_button(d)] for d in page_decks
    ]

    if total_pages > 1:
        nav: list[InlineKeyboardButton] = []
        if page > 0:
            nav.append(InlineKeyboardButton("\u2190", callback_data=f'decks_page_{page - 1}'))
        if page < total_pages - 1:
            nav.append(InlineKeyboardButton("\u2192", callback_data=f'decks_page_{page + 1}'))
        buttons.append(nav)

    buttons.append([InlineKeyboardButton("\U0001f3e0 Menu", callback_data='main_menu')])

    return header, InlineKeyboardMarkup(buttons)


async def _show_decks_page(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE, page: int) -> None:
    """Render a page of decks as clickable buttons (edit existing message)."""
    decks = context.user_data.get('_decks_cache', [])
    total_pages = max(1, (len(decks) + DECKS_PER_PAGE - 1) // DECKS_PER_PAGE)
    page = max(0, min(page, total_pages - 1))

    header, markup = _build_decks_markup(decks, page, total_pages)
    await safe_edit_text(query, header, reply_markup=markup)


async def _send_decks_page(message: Message, context: ContextTypes.DEFAULT_TYPE, page: int) -> None:
    """Render a page of decks as clickable buttons (send new message)."""
    decks = context.user_data.get('_decks_cache', [])
    total_pages = max(1, (len(decks) + DECKS_PER_PAGE - 1) // DECKS_PER_PAGE)
    page = max(0, min(page, total_pages - 1))

    header, markup = _build_decks_markup(decks, page, total_pages)
    await safe_send_text(message, header, reply_markup=markup)
