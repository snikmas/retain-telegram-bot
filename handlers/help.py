from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes


HELP_TEXT = (
    "\u2753 How it works\n\n"
    "1. Send me text or a photo \u2014 I'll make a card\n"
    "2. Use front | back to set both sides\n"
    "3. Hit Review when cards are due\n"
    "4. Rate how well you remembered\n\n"
    "I'll schedule each card so you review it "
    "right before you'd forget \U0001f9e0"
)


async def help_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        HELP_TEXT,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("\U0001f3e0 Menu", callback_data='main_menu')]
        ])
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        HELP_TEXT,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("\U0001f3e0 Menu", callback_data='main_menu')]
        ])
    )
