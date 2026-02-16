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
from handlers.cards import add_card_entry
from handlers.start import start
from handlers.flow_handlers import get_content
from handlers.decks import create_deck

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


    conv_hander = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_card_entry, pattern='add_card')],
        states={
            AddCardState.AWAITING_CONTENT: [
                MessageHandler(filters.PHOTO, get_content),
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_content),
            ],
            AddCardState.CREATING_DECK: [filters.TEXT & ~filters.COMMAND, create_deck],
            AddCardState.PREVIEW: []# no actually. just call it from somewhere.. no triggers.
        },
        fallbacks=[MessageHandler(filters.PHOTO, get_content),]
    )
    
    application.add_handler(CommandHandler('start', start))
    application.add_handler(conv_hander)

    application.run_polling()

if __name__ == '__main__':
    logging.info("Init db...")
    init_db()

    logging.info("Starting app")
    main()