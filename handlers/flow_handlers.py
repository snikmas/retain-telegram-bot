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

from utils.constants import AddCardState, PREVIEW_BUTTONS
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
        await preview(update.message, context)  # ← Actually show preview
        return AddCardState.CONFIRMATION_PREVIEW
    else: 
        msg = "Which deck?"
        
        decks = db.get_all_decks(update.effective_user.id)
        if decks:
            decks_id = [deck['id'] for deck in decks]
        else:
            # No decks
            await update.message.reply_text("Name for your first deck:")
            return AddCardState.CREATING_DECK


        if len(decks_id) == 0:
            await update.message.reply_text("A name for a deck:")
            logging.info("going to creating_deck")
            return AddCardState.CREATING_DECK

        decks = db.get_all_decks(update.effective_user.id)
        buttons = utils.get_buttons(decks, 'deck')  # Pass full deck dicts, not just IDs
        buttons.append([InlineKeyboardButton("+ Add A New Deck", callback_data='new_deck')])
        
        await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(buttons))
        logging.info("going to awaiting_deck")

        return AddCardState.AWAITING_DECK
        

async def preview(message_or_query, context):
    """Works with both Message and CallbackQuery"""
    
    cur_card = context.user_data.get('cur_card', {})
    front = cur_card.get('front', '[No front]')
    back = cur_card.get('back', '[No back]')
    
    deck_id = context.user_data.get('cur_deck_id') or context.user_data.get('default_deck_id')
    card_type = context.user_data.get('temp_type') or context.user_data.get('default_card_type', 'basic')
    
    deck_name = db.get_deck_name(deck_id) if deck_id else "Unknown"
    
    preview_text = f"""📋 Preview

**Front:**
{front}

**Back:**
{back}

━━━━━━━━━━━━━━━━━━━━
📁 {deck_name} · 🎴 {card_type}
"""
    
    markup = InlineKeyboardMarkup(PREVIEW_BUTTONS)
    
    if hasattr(message_or_query, 'reply_text'):
        # Message
        await message_or_query.reply_text(preview_text, reply_markup=markup)
    else:
        # CallbackQuery
        await message_or_query.edit_message_text(preview_text, reply_markup=markup)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Cancelled")
    return ConversationHandler.END

