import logging

from telegram import Update
from telegram.ext import ContextTypes

import database.database as db
import handlers.flow_handlers as hand_flow
from utils.constants import AddCardState


DECK_NAME_MAX = 50


async def create_deck(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

    await hand_flow.preview(update.message, context)
    return AddCardState.CONFIRMATION_PREVIEW


async def selected_deck(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    deck_id = int(query.data.split('_')[1])
    context.user_data['cur_deck_id'] = deck_id

    await hand_flow.preview(query, context)
    return AddCardState.CONFIRMATION_PREVIEW


async def create_new_deck(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await query.edit_message_text("\u270f\ufe0f Name for the new deck:")
    return AddCardState.CREATING_DECK
