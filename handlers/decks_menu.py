from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

import database.database as db
from utils.telegram_helpers import safe_edit_text

DECKS_PER_PAGE = 5


async def my_decks_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
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


async def decks_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle page navigation."""
    query = update.callback_query
    await query.answer()

    page = int(query.data.split('_')[2])  # decks_page_N
    await _show_decks_page(query, context, page)


# ── private helpers ──────────────────────────────────────────

def _format_deck_line(index, deck):
    """Format a single deck as a text line."""
    due = deck['due_count'] or 0
    total = deck['card_count'] or 0
    due_part = f" \U0001f534 {due} due" if due > 0 else ""
    return f" {index}. {deck['deck_name']}  \u00b7  {total} cards{due_part}"


async def _show_decks_page(query, context, page):
    """Render a page of decks as a text list with navigation."""
    decks = context.user_data.get('_decks_cache', [])
    total_pages = max(1, (len(decks) + DECKS_PER_PAGE - 1) // DECKS_PER_PAGE)
    page = max(0, min(page, total_pages - 1))

    start = page * DECKS_PER_PAGE
    page_decks = decks[start:start + DECKS_PER_PAGE]

    if total_pages > 1:
        header = f"\U0001f4da My Decks ({page + 1}/{total_pages})"
    else:
        header = "\U0001f4da My Decks"

    lines = [header, ""]
    for i, d in enumerate(page_decks, start=start + 1):
        lines.append(_format_deck_line(i, d))

    text = "\n".join(lines)

    buttons = []
    if total_pages > 1:
        nav = []
        if page > 0:
            nav.append(InlineKeyboardButton("\u2190", callback_data=f'decks_page_{page - 1}'))
        if page < total_pages - 1:
            nav.append(InlineKeyboardButton("\u2192", callback_data=f'decks_page_{page + 1}'))
        buttons.append(nav)

    buttons.append([InlineKeyboardButton("\U0001f3e0 Menu", callback_data='main_menu')])

    await safe_edit_text(query, text, reply_markup=InlineKeyboardMarkup(buttons))
