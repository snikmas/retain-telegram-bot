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
import database.database as db
# later put them to one folder and just folder import *
from handlers.cards import add_card_entry
from handlers.start import start
from handlers.flow_handlers import get_content
from handlers.decks import create_deck_db

from utils.constants import AddCardState

# ========================================================


async def create_deck(update: Update, context:ContextTypes.DEFAULT_TYPE):
    deck_name = update.message.text
    
    if deck_name is None:
        logging.info("Error during creating deck: no deck_name")
        return
    
    db.create_deck_db(update.effective_user.id, deck_name)
    context.user_data['cur_deck_id'] = db.get_deck_id(update.effective_user.id, deck_name)

    # we call it from 'get_content' next one is preview
    return AddCardState.PREVIEW