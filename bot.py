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
# later put them to one folder and just folder import *
import handlers.cards as hand_card
import handlers.start as hand_start
import handlers.flow_handlers as hand_flow
import handlers.decks as hand_deck

from utils.constants import AddCardState

# ========================================================

load_dotenv()
TG_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

logger = logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


def main() -> None:

    logging.info("Running main")

    application = ApplicationBuilder().token(TG_BOT_TOKEN).build()


    conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(hand_card.add_card_entry, pattern='^add_card$')
        ],
        
        states={
            AddCardState.AWAITING_CONTENT: [
                MessageHandler(filters.PHOTO, hand_flow.get_content),
                MessageHandler(filters.TEXT & ~filters.COMMAND, hand_flow.get_content),
            ],
            
            AddCardState.AWAITING_DECK: [
                CallbackQueryHandler(hand_deck.selected_deck, pattern='^deck_\\d+$'),
                CallbackQueryHandler(hand_deck.create_new_deck, pattern='^new_deck$')
            ],
            
            AddCardState.CREATING_DECK: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, hand_deck.create_deck)
            ],
            
            AddCardState.CONFIRMATION_PREVIEW: [
                CallbackQueryHandler(hand_card.save_card, pattern='^save_card$'),
                CallbackQueryHandler(hand_card.edit_card, pattern='^edit_card$'),
                CallbackQueryHandler(hand_card.change_settings, pattern='^change_settings$'),
                CallbackQueryHandler(hand_flow.cancel, pattern='^cancel$')
            ]
        },
        
        fallbacks=[CommandHandler('cancel', hand_flow.cancel)]
    )
    
    application.add_handler(CommandHandler('start', hand_start.start))
    application.add_handler(conv_handler)

    application.run_polling()

if __name__ == '__main__':
    logging.info("Init db...")
    init_db()

    logging.info("Starting app")
    main()