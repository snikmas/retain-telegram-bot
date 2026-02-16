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


# ==================== SYSTEM IMPORTS ====================
from dotenv import load_dotenv
import os

# ===================== UTILS IMPORT =====================
import logging

# ==================== FOLDERS IMPORT ====================
from database.database import init_db
import database.database as db
# later put them to one folder and just folder import *
from handlers.cards import add_card_entry
from handlers import start

from utils.constants import AddCardState
import utils.utils as utils

# ==================== ============== ====================


async def get_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.info("Got content")
    
    card_type = context.user_data.get('default_card_type') # or do basic by default. go with it
    if update.message.photo:
        raw_content = update.message.photo[-1]
        context.user_data['cur_card'] = utils.parse_photo(raw_content, card_type)
    else:
        raw_content = update.message.text
        context.user_data['cur_card'] = utils.parse_text(raw_content, card_type)

    


    if context.user_data.get('default_deck_id'): #does it has default deck
        return AddCardState.PREVIEW
    else: 
        msg = update.edited_message("Which deck?")
        
        decks = db.get_all_decks(update.effective_user.id)
        decks_id = [deck.id for deck in decks]

        if len(decks_id) == 0:
            await update.message.reply_text("A name for a deck:")
            logging.info("going to creating_deck")
            return AddCardState.CREATING_DECK

        buttons = utils.get_buttons(decks_id, 'deck')
        buttons.append([InlineKeyboardButton("+ Add A New Deck")])
        
        await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(buttons))
        logging.info("going to awaiting_deck")

        return AddCardState.AWAITING_DECK
        

async def preview(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pass