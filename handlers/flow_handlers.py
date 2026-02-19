import html
import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

import database.database as db
import utils.utils as utils
from utils.constants import AddCardState, PREVIEW_BUTTONS
from utils.telegram_helpers import safe_edit_text, safe_send_text, safe_send_photo


CARD_SIDE_MAX = 1000


async def get_content(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logging.info("Got content")

    card_type = context.user_data.get('default_card_type')
    if update.message.photo:
        raw_content = update.message.photo[-1]
        context.user_data['cur_card'] = utils.parse_photo(raw_content, update.message.caption)
    else:
        raw_content = update.message.text
        parsed = utils.parse_text(raw_content, card_type)

        if not parsed['front']:
            await safe_send_text(update.message, "\u26a0\ufe0f Card can't be empty. Send some text:")
            return AddCardState.AWAITING_CONTENT

        if len(parsed['front']) > CARD_SIDE_MAX or len(parsed['back']) > CARD_SIDE_MAX:
            await safe_send_text(
                update.message,
                f"\u26a0\ufe0f Too long \u2014 each side can be up to {CARD_SIDE_MAX} characters. Try again:"
            )
            return AddCardState.AWAITING_CONTENT

        if not parsed['back']:
            front_hint = html.escape(parsed['front'][:20])
            await safe_send_text(
                update.message,
                f"\u26a0\ufe0f Cards need two sides.\n\n"
                f"Use <code>|</code> to separate front from back:\n"
                f"<code>{front_hint} | meaning here</code>\n\n"
                f"Or send two lines:\n"
                f"<code>{front_hint}\nmeaning here</code>"
            )
            return AddCardState.AWAITING_CONTENT

        context.user_data['cur_card'] = parsed

    if context.user_data.get('default_deck_id'):
        await preview(update.message, context)
        return AddCardState.CONFIRMATION_PREVIEW

    return await _show_deck_selection(update.message, context)


async def _show_deck_selection(message, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = message.chat.id
    decks = db.get_all_decks(user_id)

    if not decks:
        await safe_send_text(
            message,
            "No decks yet \U0001f4ad\nType a name for your first one:"
        )
        return AddCardState.CREATING_DECK

    buttons = utils.get_buttons(decks, 'deck')
    buttons.append([InlineKeyboardButton("\u2795 New deck", callback_data='new_deck')])
    buttons.append([InlineKeyboardButton("Cancel", callback_data='cancel')])

    await safe_send_text(
        message,
        "\U0001f4c1 Which deck?",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    return AddCardState.AWAITING_DECK


async def preview(message_or_query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Works with both Message and CallbackQuery. Handles photo and text cards."""
    cur_card = context.user_data.get('cur_card', {})
    is_photo = cur_card.get('is_photo', False)
    front = cur_card.get('front', '[empty]')
    back = cur_card.get('back', '')

    deck_id = context.user_data.get('cur_deck_id') or context.user_data.get('default_deck_id')
    card_type = context.user_data.get('temp_type') or context.user_data.get('default_card_type', 'basic')

    deck_name = db.get_deck_name(deck_id) if deck_id else "\u2014"
    markup = InlineKeyboardMarkup(PREVIEW_BUTTONS)

    type_note = "\n<i>Creates 2 cards (original + flipped)</i>" if card_type == 'reverse' else ""

    if is_photo:
        no_caption_warning = "\n\u26a0\ufe0f <i>No caption \u2014 the answer will be empty during review</i>" if not back else ""
        caption = (
            f"<b>\U0001f5bc Preview</b>\n\n"
            f"<b>Back:</b> {html.escape(back) if back else '<i>empty</i>'}\n\n"
            f"<i>\U0001f4c1 {html.escape(deck_name or '')} \u00b7 {card_type}</i>{type_note}"
            f"{no_caption_warning}"
        )
        if hasattr(message_or_query, 'reply_photo'):
            await safe_send_photo(message_or_query, front, caption=caption, reply_markup=markup)
        else:
            await safe_send_photo(message_or_query.message, front, caption=caption, reply_markup=markup)
            try:
                await message_or_query.delete_message()
            except Exception:
                pass
    else:
        back_display = html.escape(back) if back else '<i>empty</i>'
        preview_text = (
            f"<b>\U0001f4cb Preview</b>\n\n"
            f"<b>Front:</b> {html.escape(front)}\n"
            f"<b>Back:</b> {back_display}\n\n"
            f"<i>\U0001f4c1 {html.escape(deck_name or '')} \u00b7 {card_type}</i>{type_note}"
        )
        if hasattr(message_or_query, 'reply_text'):
            await safe_send_text(message_or_query, preview_text, reply_markup=markup)
        else:
            await safe_edit_text(message_or_query, preview_text, reply_markup=markup)


async def back_to_content(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    await safe_edit_text(query, "\u270f\ufe0f Send me new text or a photo")
    return AddCardState.AWAITING_CONTENT


async def menu_exit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    context.user_data.pop('cur_card', None)
    context.user_data.pop('cur_deck_id', None)
    context.user_data.pop('temp_type', None)

    from handlers.start import build_main_menu
    text, markup = build_main_menu(update.effective_user.id)
    await safe_edit_text(query, text, reply_markup=markup)
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop('cur_card', None)
    context.user_data.pop('cur_deck_id', None)
    context.user_data.pop('temp_type', None)

    from handlers.start import build_main_menu
    text, markup = build_main_menu(update.effective_user.id)

    if update.callback_query:
        await update.callback_query.answer()
        await safe_edit_text(update.callback_query, text, reply_markup=markup)
    else:
        await safe_send_text(update.message, text, reply_markup=markup)

    return ConversationHandler.END
