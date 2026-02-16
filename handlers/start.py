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


# ========================================================



async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    
    logging.info("Started /start")

    user_id = update.effective_user.id
    user = db.get_user(user_id)

    if user:
        username = update.effective_user.username
        
        defaults = db.get_user_defaults(user_id)
        if defaults:
            if defaults['deck_id']:
                context.user_data['default_deck_id'] = defaults['deck_id']
            if defaults['card_type']:
                context.user_data['default_card_type'] = defaults['card_type']
        
        buttons = [
            [InlineKeyboardButton('Add Card', callback_data='add_card')],
            [InlineKeyboardButton('Review Now', callback_data='review')],
            [InlineKeyboardButton('My Decks', callback_data='my_decks')],
            [InlineKeyboardButton('Stats', callback_data='stats')]
        ]
        await update.message.reply_text(f"Welcome back, {username}! Your stats for now", reply_markup=InlineKeyboardMarkup(buttons))

    else:
        username = update.effective_user.username
        db.create_user(user_id, username, update.effective_user.first_name)

        # context.user_data.get('default_card_type') =
        context.user_data['default_card_type'] = 'basic'

        buttons = [
            [InlineKeyboardButton('Create Card', callback_data='add_card')],
            [InlineKeyboardButton('Tutorial', callback_data='tutorial')]
        ]

        message = f"""👋 Hey {username}!

        I help you remember anything using flashcards and spaced repetition.
        
        📸 Send screenshots or text
        🧠 Review at perfect intervals  
        ✅ Never forget what you learn
        
        Ready to try?"""

        await update.message.reply_text(message, reply_markup=InlineKeyboardMarkup(buttons))

