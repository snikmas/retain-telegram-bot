import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

import database.database as db
from utils.constants import MAIN_MENU_BUTTONS


def _load_defaults(user_id, context):
    """Load user defaults from DB into user_data for the session."""
    defaults = db.get_user_defaults(user_id)
    if defaults:
        if defaults['deck_id']:
            context.user_data['default_deck_id'] = defaults['deck_id']
        if defaults['card_type']:
            context.user_data['default_card_type'] = defaults['card_type']


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.info("Started /start")

    user_id = update.effective_user.id
    user = db.get_user(user_id)
    name = update.effective_user.first_name

    if user:
        _load_defaults(user_id, context)

        await update.message.reply_text(
            f"Hey {name} !\n\n"
            "What are we working on?",
            reply_markup=InlineKeyboardMarkup(MAIN_MENU_BUTTONS)
        )

    else:
        db.create_user(user_id, update.effective_user.username, name)
        context.user_data['default_card_type'] = 'basic'

        buttons = [
            [InlineKeyboardButton('Let\'s go', callback_data='add_card')],
        ]

        await update.message.reply_text(
            f"Hey {name}, welcome to Retain\n\n"
            "I'm your flashcard assistant. Send me anything\n"
            "you want to remember — text, screenshots,\n"
            "notes — and I'll quiz you at the right time.\n\n"
            "The trick? Spaced repetition.\n"
            "You review right before you'd forget.\n\n"
            "Send your first card to get started.",
            reply_markup=InlineKeyboardMarkup(buttons)
        )


async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback handler for the 'Main Menu' button (outside conversation)."""
    query = update.callback_query
    await query.answer()

    _load_defaults(update.effective_user.id, context)

    await query.edit_message_text(
        "What are we working on?",
        reply_markup=InlineKeyboardMarkup(MAIN_MENU_BUTTONS)
    )
