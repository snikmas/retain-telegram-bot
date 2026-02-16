import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

import database.database as db
import utils.utils as utils
from utils.constants import AddCardState, PREVIEW_BUTTONS


async def get_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.info("Got content")

    card_type = context.user_data.get('default_card_type')
    if update.message.photo:
        raw_content = update.message.photo[-1]
        context.user_data['cur_card'] = utils.parse_photo(raw_content, card_type)
    else:
        raw_content = update.message.text
        context.user_data['cur_card'] = utils.parse_text(raw_content, card_type)

    if context.user_data.get('default_deck_id'):
        await preview(update.message, context)
        return AddCardState.CONFIRMATION_PREVIEW

    return await _show_deck_selection(update.message, context)


async def _show_deck_selection(message, context):
    """Show deck selection buttons. Used by get_content and back_to_decks."""
    user_id = message.chat.id
    decks = db.get_all_decks(user_id)

    if not decks:
        await message.reply_text(
            "You don't have any decks yet.\n"
            "Type a name for your first one:"
        )
        return AddCardState.CREATING_DECK

    buttons = utils.get_buttons(decks, 'deck')
    buttons.append([InlineKeyboardButton("+ New deck", callback_data='new_deck')])
    buttons.append([InlineKeyboardButton("Cancel", callback_data='cancel')])

    await message.reply_text(
        "Where should this card go?",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    return AddCardState.AWAITING_DECK


async def preview(message_or_query, context):
    """Works with both Message and CallbackQuery. Handles photo and text cards."""

    cur_card = context.user_data.get('cur_card', {})
    is_photo = cur_card.get('is_photo', False)
    front = cur_card.get('front', '[empty]')
    back = cur_card.get('back', '')

    deck_id = context.user_data.get('cur_deck_id') or context.user_data.get('default_deck_id')
    card_type = context.user_data.get('temp_type') or context.user_data.get('default_card_type', 'basic')

    deck_name = db.get_deck_name(deck_id) if deck_id else "—"
    markup = InlineKeyboardMarkup(PREVIEW_BUTTONS)

    if is_photo:
        caption = (
            f"--- card preview ---\n\n"
            f"Back:  {back if back else '(empty)'}\n\n"
            f"{deck_name}  /  {card_type}"
        )

        if hasattr(message_or_query, 'reply_photo'):
            await message_or_query.reply_photo(
                photo=front, caption=caption, reply_markup=markup
            )
        else:
            chat_id = message_or_query.message.chat_id
            await message_or_query.message.reply_photo(
                photo=front, caption=caption, reply_markup=markup
            )
            await message_or_query.delete_message()
    else:
        back_display = back if back else "(empty)"
        preview_text = (
            f"--- card preview ---\n\n"
            f"Front\n"
            f"{front}\n\n"
            f"Back\n"
            f"{back_display}\n\n"
            f"{deck_name}  /  {card_type}"
        )

        if hasattr(message_or_query, 'reply_text'):
            await message_or_query.reply_text(preview_text, reply_markup=markup)
        else:
            await message_or_query.edit_message_text(preview_text, reply_markup=markup)


async def back_to_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Back button from preview — ask user to re-send content."""
    query = update.callback_query
    await query.answer()

    await query.edit_message_text("Send me new text or a photo:")
    return AddCardState.AWAITING_CONTENT


async def back_to_decks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Back button from preview when user has no default deck — re-show deck list."""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    decks = db.get_all_decks(user_id)

    if not decks:
        await query.edit_message_text(
            "You don't have any decks yet.\n"
            "Type a name for your first one:"
        )
        return AddCardState.CREATING_DECK

    buttons = utils.get_buttons(decks, 'deck')
    buttons.append([InlineKeyboardButton("+ New deck", callback_data='new_deck')])
    buttons.append([InlineKeyboardButton("Cancel", callback_data='cancel')])

    await query.edit_message_text(
        "Where should this card go?",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    return AddCardState.AWAITING_DECK


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Works for both /cancel command (Message) and cancel button (CallbackQuery)."""
    context.user_data.pop('cur_card', None)
    context.user_data.pop('cur_deck_id', None)
    context.user_data.pop('temp_type', None)

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("Cancelled.")
    else:
        await update.message.reply_text("Cancelled.")

    return ConversationHandler.END
