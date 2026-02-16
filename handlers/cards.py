# ==================== TELEGRAM IMPORTS ====================
from telegram.ext import (
    filters, 
    ApplicationBuilder, 
    ContextTypes, 
    CommandHandler, 
    MessageHandler,
    ConversationHandler,
    PicklePersistence,
    CallbackQueryHandler,
    )

from telegram import (
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
    InlineKeyboardButton, 
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    _replykeyboardremove,      
)

# ===================== UTILS IMPORT =====================
import logging

# ==================== FOLDERS IMPORT =====================
import database.database as db
import utils.utils as utils
from utils.constants import AddCardState, CARD_TYPE_BUTTONS


# ===================== ============ =====================

async def add_card_entry(update:Update, context:ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    query.answer()

    deck_id = context.user_data.get('default_deck_id')
    card_type = context.user_data.get('default_card_type')


    # check if its a user with defaults
    if deck_id and card_type:
        deck_name = db.get_deck_name(deck_id)

        if deck_name is None:
            # impossible, only if the user db file was failed
            logging.info("Can't get a deck name from the db. Creating a new one..")
            return 

    
        await query.edit_message_text(
            f"""
        📩 Send me text or an image

        ⚙️ Current Defaults:
        🗂 Deck: {deck_name}
        🏷 Type: {card_type}
        """,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔄 Change Defaults", callback_data='change_defaults')
            ]])
        )
        # im not sure how to do that if its choosing some button it would return a state (like change settings -> go for awaiting deck or type)

    else: # no defaults: a new user or just dont wanna set defaults guy
        await query.edit_message_text("Send me text or image\nNo Defaults selected yet.")
    
    return AddCardState.AWAITING_CONTENT


async def save_card(update:Update, context:ContextTypes.DEFAULT_TYPE):
    logging.info(f"CARD TYPE: {context.user_data.get('default_card_type')}  ")
    db.save_card(
    context.user_data.get('cur_card'),
    context.user_data.get('default_card_type') or context.user_data.get('temp_type'),
    context.user_data.get('cur_deck_id') or context.user_data.get('default_deck_id'),
    update.effective_user.id)

# cards.py or decks.py
async def change_settings(update, context):
    query = update.callback_query
    await query.answer()
    
    # Show deck choices
    user_id = update.effective_user.id
    decks = db.get_all_decks(user_id)
    
    buttons = utils.get_buttons(decks, 'deck')
    buttons.append([InlineKeyboardButton("+ Create New", callback_data='new_deck')])
    
    await query.edit_message_text(
        "Which deck?",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    
    return AddCardState.AWAITING_DECK


async def edit_card(update, context):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "Send new content for the card:"
    )
    
    return AddCardState.EDITING 