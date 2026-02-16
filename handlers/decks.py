import logging

from telegram import Update
from telegram.ext import ContextTypes

import database.database as db
import handlers.flow_handlers as hand_flow
from utils.constants import AddCardState


async def create_deck(update: Update, context: ContextTypes.DEFAULT_TYPE):
    deck_name = update.message.text

    if deck_name is None:
        logging.info("Error during creating deck: no deck_name")
        return

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

    await query.edit_message_text("Name for the new deck:")
    return AddCardState.CREATING_DECK
