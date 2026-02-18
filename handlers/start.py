import html
import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

import database.database as db
from utils.telegram_helpers import safe_edit_text, safe_send_text


def build_main_menu(user_id: int) -> tuple[str, InlineKeyboardMarkup]:
    """
    Returns (message_text, markup) for the main menu.
    Text includes a one-line stats summary when the user has cards.
    """
    stats = db.get_card_stats(user_id)
    total = stats['total']
    due = stats['due_today']

    if total > 0:
        due_part = f"  \u00b7  {due} due today" if due > 0 else "  \u00b7  all caught up"
        stats_line = f"\n<i>{total} cards{due_part}</i>"
    else:
        stats_line = ""

    text = f"\U0001f3e0 Main menu{stats_line}"

    review_label = f'\U0001f9e0 Review \u00b7 {due} due' if due > 0 else '\U0001f9e0 Review'
    markup = InlineKeyboardMarkup([
        [
            InlineKeyboardButton('\U0001f4dd New Card', callback_data='add_card'),
            InlineKeyboardButton(review_label, callback_data='review'),
        ],
        [
            InlineKeyboardButton('\U0001f4da My Decks', callback_data='my_decks'),
            InlineKeyboardButton('\u2753 How it works', callback_data='help'),
        ],
    ])

    return text, markup


def _load_defaults(user_id: int, context: ContextTypes.DEFAULT_TYPE, force: bool = False) -> None:
    """Load user defaults from DB into user_data. Skips if already cached."""
    if not force and context.user_data.get('_defaults_loaded'):
        return
    defaults = db.get_user_defaults(user_id)
    if defaults:
        if defaults['deck_id']:
            context.user_data['default_deck_id'] = defaults['deck_id']
        if defaults['card_type']:
            context.user_data['default_card_type'] = defaults['card_type']
    context.user_data['_defaults_loaded'] = True


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logging.info("Started /start")

    user_id = update.effective_user.id
    user = db.get_user(user_id)
    name = update.effective_user.first_name

    if user:
        _load_defaults(user_id, context)
        _, markup = build_main_menu(user_id)
        await safe_send_text(
            update.message,
            f"Hey {html.escape(name)} \U0001f44b",
            reply_markup=markup,
        )

    else:
        db.create_user(user_id, update.effective_user.username, name)
        context.user_data['default_card_type'] = 'basic'

        await safe_send_text(
            update.message,
            f"Hey {html.escape(name)}, welcome to Retain \U0001f9e0\n\n"
            "I help you remember things using spaced repetition. "
            "Send me anything \u2014 text, photos, notes \u2014 "
            "and I'll quiz you before you forget.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Let's go", callback_data='add_card')],
            ])
        )


async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Callback handler for the 'Menu' button (outside conversation)."""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    _load_defaults(user_id, context)

    text, markup = build_main_menu(user_id)
    await safe_edit_text(query, text, reply_markup=markup)
