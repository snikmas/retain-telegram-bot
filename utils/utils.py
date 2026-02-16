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

def parse_photo(content):
    pass

def parse_text(content, card_type=None):
    """
    returns: {'front': str, 'back': str}
    """
    text = content.strip()
    
    if '|' in text:
        parts = text.split('|', 1)
        return {'front': parts[0].strip(), 'back': parts[1].strip()}
    
    if '\n' in text:
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        if len(lines) >= 2:
            return {'front': lines[0], 'back': '\n'.join(lines[1:])}
    
    return {'front': text, 'back': ""}


def get_buttons(items, prefix):
    buttons = []
    for item in items:
        buttons.append([
            InlineKeyboardButton(
                item['name'],  
                callback_data=f"{prefix}_{item['id']}"  
            )
        ])
    return buttons

# TEXT TEMPLATES
# A - stmhg
# A, B, C - smthg
# A - smthg. B, C, D - smthg