import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

import database.database as db
import utils.utils as utils
from utils.constants import AddCardState, CARD_TYPE_BUTTONS


async def add_card_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    deck_id = context.user_data.get('default_deck_id')
    card_type = context.user_data.get('default_card_type')

    if deck_id and card_type:
        deck_name = db.get_deck_name(deck_id)

        if deck_name is None:
            logging.info("Can't get a deck name from the db")
            await query.edit_message_text(
                "Your saved deck was deleted.\n"
                "Send your card and you'll pick a new one."
            )
            context.user_data.pop('default_deck_id', None)
            db.update_user_defaults(update.effective_user.id, deck_id=None)

        else:
            await query.edit_message_text(
                "Send me text or a photo.\n\n"
                f"  Deck:  {deck_name}\n"
                f"  Type:  {card_type}\n",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("Change defaults", callback_data='change_settings')
                ]])
            )
    else:
        await query.edit_message_text(
            "Send me text or a photo.\n\n"
            "Tip: use  front | back  or two lines."
        )

    return AddCardState.AWAITING_CONTENT


async def save_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    card_type = context.user_data.get('default_card_type') or context.user_data.get('temp_type')
    deck_id = context.user_data.get('cur_deck_id') or context.user_data.get('default_deck_id')

    logging.info("Saving card...")
    db.save_card(
        context.user_data.get('cur_card'),
        card_type,
        deck_id,
        update.effective_user.id
    )

    if context.user_data.get('cur_deck_id'):
        new_deck_id = context.user_data['cur_deck_id']
        context.user_data['default_deck_id'] = new_deck_id
        db.update_user_defaults(update.effective_user.id, deck_id=new_deck_id)

    context.user_data.pop('cur_card', None)
    context.user_data.pop('cur_deck_id', None)
    context.user_data.pop('temp_type', None)

    await query.edit_message_text(
        "Saved.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("+ Another card", callback_data='add_card'),
             InlineKeyboardButton("Menu", callback_data='main_menu')]
        ])
    )

    return ConversationHandler.END


async def change_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    decks = db.get_all_decks(user_id)

    buttons = utils.get_buttons(decks, 'deck')
    buttons.append([InlineKeyboardButton("+ New deck", callback_data='new_deck')])
    buttons.append([InlineKeyboardButton("< Back", callback_data='back')])

    await query.edit_message_text(
        "Pick a deck:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

    return AddCardState.AWAITING_DECK


async def edit_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await query.edit_message_text("Send the new content:")

    return AddCardState.AWAITING_CONTENT
