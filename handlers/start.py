import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

import database.database as db
from utils.constants import MAIN_MENU_BUTTONS
from utils.telegram_helpers import safe_edit_text, safe_send_text


def _load_defaults(user_id, context, force=False):
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


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.info("Started /start")

    user_id = update.effective_user.id
    user = db.get_user(user_id)
    name = update.effective_user.first_name

    if user:
        _load_defaults(user_id, context)

        await safe_send_text(
            update.message,
            f"Hey {name} \U0001f44b",
            reply_markup=InlineKeyboardMarkup(MAIN_MENU_BUTTONS)
        )

    else:
        db.create_user(user_id, update.effective_user.username, name)
        context.user_data['default_card_type'] = 'basic'

        buttons = [
            [InlineKeyboardButton("\U0001f680 Let's go", callback_data='add_card')],
        ]

        await safe_send_text(
            update.message,
            f"Hey {name}, welcome to Retain \U0001f9e0\n\n"
            "I help you remember things using spaced repetition. "
            "Send me anything — text, photos, notes — "
            "and I'll quiz you before you forget.",
            reply_markup=InlineKeyboardMarkup(buttons)
        )


async def help_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback handler for 'How it works' button."""
    query = update.callback_query
    await query.answer()

    text = (
        "\u2753 How it works\n\n"
        "\U0001f4dd Send me text or a photo — I'll turn it into a flashcard.\n"
        "Use front | back or two lines to set both sides.\n\n"
        "\U0001f9e0 When it's time, hit Review — I'll show the front "
        "and you recall the answer.\n\n"
        "\U0001f3af Rate how well you remembered. "
        "I'll schedule the next review — easy cards appear less, "
        "hard cards come back sooner.\n\n"
        "That's it. The more you review, the more you retain."
    )

    await safe_edit_text(
        query,
        text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("\U0001f3e0 Menu", callback_data='main_menu')]
        ])
    )


async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback handler for the 'Main Menu' button (outside conversation)."""
    query = update.callback_query
    await query.answer()

    _load_defaults(update.effective_user.id, context)

    await safe_edit_text(
        query,
        "\U0001f3e0 Main menu",
        reply_markup=InlineKeyboardMarkup(MAIN_MENU_BUTTONS)
    )
