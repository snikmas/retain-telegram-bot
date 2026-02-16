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
from utils.constants import AddCardState

# ===================== ============ =====================

async def add_card_entry(update:Update, context:ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
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

    else: # no defaults: a new user or just dont wanna set defaults guy
        await query.edit_message_text("Send me text or image\nNo Defaults selected yet.")
    
    return AddCardState.AWAITING_CONTENT


