import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

import database.database as db
import handlers.flow_handlers as hand_flow
from utils.constants import AddCardState
from utils.telegram_helpers import safe_send_text


DECK_NAME_MAX = 50


async def create_deck(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    deck_name = (update.message.text or '').strip()

    if not deck_name:
        await update.message.reply_text(
            "\u26a0\ufe0f Deck name can't be empty. Try again:"
        )
        return AddCardState.CREATING_DECK

    if len(deck_name) > DECK_NAME_MAX:
        await update.message.reply_text(
            f"\u26a0\ufe0f Too long — {DECK_NAME_MAX} characters max. Try again:"
        )
        return AddCardState.CREATING_DECK

    existing = db.get_deck_id(update.effective_user.id, deck_name)
    if existing:
        await update.message.reply_text(
            f"\u26a0\ufe0f \"{deck_name}\" already exists. Pick a different name:"
        )
        return AddCardState.CREATING_DECK

    deck_id = db.create_deck_db(update.effective_user.id, deck_name)
    context.user_data['cur_deck_id'] = deck_id

    # If the user already sent card content before creating the deck → show preview.
    # If they created the deck first (e.g. via Change Settings), ask for content now.
    if context.user_data.get('cur_card'):
        await hand_flow.preview(update.message, context)
        return AddCardState.CONFIRMATION_PREVIEW

    card_type = context.user_data.get('default_card_type', 'basic')
    await safe_send_text(
        update.message,
        f"\u2705 Deck \"{deck_name}\" created!\n\n"
        f"\U0001f4dd Now send me the card content\n\n"
        f"\U0001f4c1 {deck_name}  \u00b7  {card_type}",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("\u2699\ufe0f Change", callback_data='change_settings')
        ]]),
    )
    return AddCardState.AWAITING_CONTENT


async def selected_deck(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    deck_id = int(query.data.split('_')[1])
    context.user_data['cur_deck_id'] = deck_id

    await hand_flow.preview(query, context)
    return AddCardState.CONFIRMATION_PREVIEW


async def create_new_deck(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    await query.edit_message_text("\u270f\ufe0f Name for the new deck:")
    return AddCardState.CREATING_DECK
