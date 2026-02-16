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

def parse_text(content, card_type):
    # simple parser, users fix edge cases via edit button
    
    if '|' in content:
        front, back = content.split('|', 1)
        if card_type == 'basic':
            return front.strip(), back.strip()
        elif card_type == 'reverse':
            return [[front.strip(), back.strip()], [back.strip(), front.strip()]]
        

    if '\n' in content:
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        if len(lines) >= 2:
            if card_type == 'basic':
                return lines[0], '\n'.join(lines[1:])
            elif card_type == 'reverse':
                return [[lines[0], '\n'.join(lines[1:])], ['\n'.join(lines[1:]), lines[0]]]
        
    #if close.. need to cloose by yourself? or just put this word .. give the user  to 
    # can't find a pattern
    return content, ""


def get_buttons(list, context):
    buttons = []
    for but in list:
        buttons.append([
            InlineKeyboardButton(but, callback_data=f'{context}_{but}')#it would be like deck_5, deck and id
        ])
    return buttons

# TEXT TEMPLATES
# A - stmhg
# A, B, C - smthg
# A - smthg. B, C, D - smthg