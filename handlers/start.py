import html
import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

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

    if total == 0:
        text = "\U0001f4da <b>Retain</b>\n\n<i>No cards yet \u2014 add your first one!</i>"
    elif due == 0:
        text = f"\u2705 <b>All caught up!</b>\n\n<i>{total} cards in your collection</i>"
    elif due == 1:
        text = f"\U0001f9e0 <b>1 card to review</b>\n\n<i>{total} cards total</i>"
    else:
        text = f"\U0001f9e0 <b>{due} cards to review</b>\n\n<i>{total} cards total</i>"

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


_CONV_KEYS = (
    # add-card flow
    'cur_card', 'cur_deck_id', 'temp_type',
    # review flow
    'review_cards', 'review_index', 'review_correct', 'review_total',
    # manage flow
    'editing_card_id', 'edit_card_parsed', 'editing_card_photo', 'edit_card_is_photo',
    'renaming_deck_id', 'manage_deck_id', 'manage_deck_page', 'manage_page_cards',
    # review edit flow
    'review_editing_is_photo', 'review_edit_is_photo',
)


async def _reset_and_send_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Clear all in-progress conversation state and send a fresh main menu."""
    for key in _CONV_KEYS:
        context.user_data.pop(key, None)
    user_id = update.effective_user.id
    _load_defaults(user_id, context)
    text, markup = build_main_menu(user_id)
    await safe_send_text(update.message, text, reply_markup=markup)


async def force_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """ConversationHandler fallback — abort current flow and show main menu."""
    await _reset_and_send_menu(update, context)
    return ConversationHandler.END


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/clear — reset any stuck state and show a fresh main menu."""
    await _reset_and_send_menu(update, context)


async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Callback handler for the 'Menu' button (outside conversation)."""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    _load_defaults(user_id, context)

    text, markup = build_main_menu(user_id)
    await safe_edit_text(query, text, reply_markup=markup)
