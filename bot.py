import logging

from telegram import Update
from telegram.error import BadRequest, Forbidden, TimedOut, NetworkError
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

from config import TG_BOT_TOKEN, PROXY_URL
from database.database import init_db
import handlers.cards as hand_card
import handlers.start as hand_start
import handlers.flow_handlers as hand_flow
import handlers.decks as hand_deck
import handlers.review as hand_review
import handlers.stats as hand_stats
import handlers.decks_menu as hand_decks_menu
import handlers.help as hand_help
from utils.constants import AddCardState, ReviewState


def main() -> None:
    logging.info("Running main")

    builder = ApplicationBuilder().token(TG_BOT_TOKEN)
    if PROXY_URL:
        builder = builder.proxy(PROXY_URL).get_updates_proxy(PROXY_URL)
    application = builder.build()

    # Add Card conversation
    add_card_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(hand_card.add_card_entry, pattern='^add_card$')
        ],
        per_message=False,

        states={
            AddCardState.AWAITING_CONTENT: [
                CallbackQueryHandler(hand_flow.menu_exit, pattern='^main_menu$'),
                CallbackQueryHandler(hand_card.change_settings, pattern='^change_settings$'),
                MessageHandler(filters.PHOTO, hand_flow.get_content),
                MessageHandler(filters.TEXT & ~filters.COMMAND, hand_flow.get_content),
            ],

            AddCardState.AWAITING_DECK: [
                CallbackQueryHandler(hand_deck.selected_deck, pattern='^deck_\\d+$'),
                CallbackQueryHandler(hand_deck.create_new_deck, pattern='^new_deck$'),
                CallbackQueryHandler(hand_flow.back_to_content, pattern='^back$'),
                CallbackQueryHandler(hand_flow.cancel, pattern='^cancel$'),
            ],

            AddCardState.CREATING_DECK: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, hand_deck.create_deck)
            ],

            AddCardState.CONFIRMATION_PREVIEW: [
                CallbackQueryHandler(hand_card.save_card, pattern='^save_card$'),
                CallbackQueryHandler(hand_card.edit_card, pattern='^edit_card$'),
                CallbackQueryHandler(hand_card.change_settings, pattern='^change_settings$'),
                CallbackQueryHandler(hand_flow.back_to_content, pattern='^back$'),
                CallbackQueryHandler(hand_flow.cancel, pattern='^cancel$'),
            ]
        },

        fallbacks=[CommandHandler('cancel', hand_flow.cancel)]
    )

    # Review conversation
    review_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(hand_review.review_entry, pattern='^review$')
        ],
        per_message=False,

        states={
            ReviewState.SHOWING_FRONT: [
                CallbackQueryHandler(hand_review.show_answer, pattern='^show_answer$'),
                CallbackQueryHandler(hand_review.cancel_review, pattern='^cancel_review$'),
            ],

            ReviewState.RATING: [
                CallbackQueryHandler(hand_review.rate_card, pattern='^rate_\\d$'),
                CallbackQueryHandler(hand_review.cancel_review, pattern='^cancel_review$'),
            ],
        },

        fallbacks=[CommandHandler('cancel', hand_review.cancel_review)]
    )

    application.add_handler(CommandHandler('start', hand_start.start))
    application.add_handler(add_card_handler)
    application.add_handler(review_handler)

    # Standalone handlers (outside conversations)
    application.add_handler(CallbackQueryHandler(hand_start.main_menu, pattern='^main_menu$'))
    application.add_handler(CallbackQueryHandler(hand_stats.stats_entry, pattern='^stats$'))
    application.add_handler(CallbackQueryHandler(hand_help.help_entry, pattern='^help$'))
    application.add_handler(CommandHandler('help', hand_help.help_command))

    # My Decks handlers
    application.add_handler(CallbackQueryHandler(hand_decks_menu.my_decks_entry, pattern='^my_decks$'))
    application.add_handler(CallbackQueryHandler(hand_decks_menu.decks_page, pattern='^decks_page_\\d+$'))

    application.add_error_handler(error_handler)
    application.run_polling()


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Global error handler — logs the error and tries to notify the user."""
    error = context.error
    logging.error(f"Update {update} caused error: {error}", exc_info=error)

    if isinstance(error, Forbidden):
        # User blocked the bot — nothing we can do
        logging.warning(f"Bot was blocked by user: {error}")
        return

    if isinstance(error, (TimedOut, NetworkError)):
        logging.warning(f"Network issue: {error}")
        return

    if isinstance(error, BadRequest):
        msg = str(error).lower()
        if "message is not modified" in msg:
            # User tapped the same button twice — harmless, ignore
            return
        if "message to edit not found" in msg or "message to delete not found" in msg:
            # Message was already deleted — ignore
            return
        logging.warning(f"Bad request: {error}")

    # Try to notify the user something went wrong
    if isinstance(update, Update) and update.effective_chat:
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="\u26a0\ufe0f Something went wrong. Try /start to reset."
            )
        except Exception:
            pass


if __name__ == '__main__':
    logging.info("Init db...")
    init_db()

    logging.info("Starting app")
    main()
