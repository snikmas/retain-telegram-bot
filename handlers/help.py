from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from utils.telegram_helpers import safe_send_text


HELP_TEXT = (
    "<b>\u2753 How it works</b>\n\n"
    "1. Send me text or a photo \u2014 I'll make a card\n"
    "2. Use <code>front | back</code> to set both sides\n"
    "3. Hit Review when cards are due\n"
    "4. Rate how well you remembered\n\n"
    "I'll schedule each card so you review it "
    "right before you'd forget \U0001f9e0"
)

_MARKUP = InlineKeyboardMarkup([
    [InlineKeyboardButton("Menu", callback_data='main_menu')]
])


async def help_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(HELP_TEXT, reply_markup=_MARKUP, parse_mode='HTML')


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await safe_send_text(update.message, HELP_TEXT, reply_markup=_MARKUP)
