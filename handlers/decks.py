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
import handlers.cards as hand_card
import handlers.start as hand_start
import handlers.flow_handlers as hand_flow
import handlers.decks as hand_deck

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
    await hand_flow.preview(update.message, context)
    return AddCardState.CONFIRMATION_PREVIEW

# In decks.py
async def selected_deck(update: Update, context:ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    deck_id = int(query.data.split('_')[1])
    context.user_data['cur_deck_id'] = deck_id
    
    await hand_flow.preview(query, context)
    return AddCardState.CONFIRMATION_PREVIEW

async def create_new_deck(update: Update, context:ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text("What should we call this deck?")
    return AddCardState.CREATING_DECK