import logging

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

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
import handlers.manage as hand_manage
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
                CallbackQueryHandler(hand_card.change_type_entry, pattern='^change_type$'),
                CallbackQueryHandler(hand_card.set_card_type, pattern=r'^set_type_(basic|reverse)$'),
                CallbackQueryHandler(hand_card.type_back, pattern='^type_back$'),
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
            ReviewState.DECK_PICKER: [
                CallbackQueryHandler(hand_review.review_deck_selected, pattern=r'^review_deck_\d+$'),
                CallbackQueryHandler(hand_review.review_all_decks, pattern='^review_deck_all$'),
            ],

            ReviewState.SHOWING_FRONT: [
                CallbackQueryHandler(hand_review.show_answer, pattern='^show_answer$'),
                CallbackQueryHandler(hand_review.cancel_review, pattern='^cancel_review$'),
            ],

            ReviewState.RATING: [
                CallbackQueryHandler(hand_review.rate_card, pattern='^rate_\\d$'),
                CallbackQueryHandler(hand_review.cancel_review, pattern='^cancel_review$'),
                CallbackQueryHandler(hand_review.edit_card_in_review, pattern=r'^edit_review_\d+$'),
            ],
        },

        fallbacks=[CommandHandler('cancel', hand_review.cancel_review)]
    )

    # Manage: edit card conversation
    # Manage: rename deck conversation
    application.add_handler(CommandHandler('start', hand_start.start))
    application.add_handler(add_card_handler)
    application.add_handler(review_handler)
    application.add_handler(hand_manage.edit_card_handler)
    application.add_handler(hand_manage.rename_deck_handler)

    # Slash commands
    application.add_handler(CommandHandler('review', hand_review.review_command))
    application.add_handler(CommandHandler('stats', hand_stats.stats_command))
    application.add_handler(CommandHandler('decks', hand_decks_menu.decks_command))
    application.add_handler(CommandHandler('help', hand_help.help_command))

    # Standalone callback handlers
    application.add_handler(CallbackQueryHandler(hand_start.main_menu, pattern='^main_menu$'))
    application.add_handler(CallbackQueryHandler(hand_stats.stats_entry, pattern='^stats$'))
    application.add_handler(CallbackQueryHandler(hand_help.help_entry, pattern='^help$'))

    # My Decks
    application.add_handler(CallbackQueryHandler(hand_decks_menu.my_decks_entry, pattern='^my_decks$'))
    application.add_handler(CallbackQueryHandler(hand_decks_menu.decks_page, pattern=r'^decks_page_\d+$'))

    # Manage: deck detail & card actions
    application.add_handler(CallbackQueryHandler(hand_manage.deck_open, pattern=r'^deck_open_\d+$'))
    application.add_handler(CallbackQueryHandler(hand_manage.deck_cards_page, pattern=r'^deck_page_\d+_\d+$'))
    application.add_handler(CallbackQueryHandler(hand_manage.card_info, pattern=r'^card_info_\d+$'))
    application.add_handler(CallbackQueryHandler(hand_manage.card_delete_confirm, pattern=r'^card_delete_\d+$'))
    application.add_handler(CallbackQueryHandler(hand_manage.card_delete_yes, pattern=r'^card_delete_yes_\d+$'))
    application.add_handler(CallbackQueryHandler(hand_manage.deck_delete_confirm, pattern=r'^deck_delete_\d+$'))
    application.add_handler(CallbackQueryHandler(hand_manage.deck_delete_yes, pattern=r'^deck_delete_yes_\d+$'))

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
