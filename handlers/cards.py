import html
import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

import database.database as db
import handlers.flow_handlers as hand_flow
import utils.utils as utils
from utils.constants import AddCardState
from utils.telegram_helpers import safe_edit_text


async def add_card_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    deck_id = context.user_data.get('default_deck_id')
    card_type = context.user_data.get('default_card_type')

    if deck_id and card_type:
        deck_name = db.get_deck_name(deck_id)

        if deck_name is None:
            logging.info("Can't get a deck name from the db")
            await safe_edit_text(
                query,
                "\u26a0\ufe0f Your saved deck was deleted.\n"
                "Send a card and pick a new one."
            )
            context.user_data.pop('default_deck_id', None)
            db.clear_default_deck(update.effective_user.id)

        else:
            await safe_edit_text(
                query,
                f"\U0001f4dd Send me text or a photo\n\n"
                f"<i>\U0001f4c1 {html.escape(deck_name)}  \u00b7  {card_type}</i>",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("Change", callback_data='change_settings')
                ]])
            )
    else:
        await safe_edit_text(
            query,
            "\U0001f4dd Send me text or a photo\n\n"
            "<i>Text: use <code>front | back</code> or two lines\n"
            "Photo: add a caption \u2014 it becomes the back side</i>"
        )

    return AddCardState.AWAITING_CONTENT


async def save_card(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    cur_card = context.user_data.get('cur_card')
    deck_id = context.user_data.get('cur_deck_id') or context.user_data.get('default_deck_id')

    if not cur_card or not deck_id:
        await safe_edit_text(
            query,
            "\u26a0\ufe0f Session expired \u2014 please start over.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('Menu', callback_data='main_menu')]])
        )
        return ConversationHandler.END

    # temp_type (explicit choice this session) takes priority over stored default
    card_type = context.user_data.get('temp_type') or context.user_data.get('default_card_type', 'basic')

    logging.info("Saving card...")
    db.save_card(cur_card, card_type, deck_id, update.effective_user.id)

    user_id = update.effective_user.id

    # Persist deck choice as new default
    if context.user_data.get('cur_deck_id'):
        new_deck_id = context.user_data['cur_deck_id']
        context.user_data['default_deck_id'] = new_deck_id
        db.update_user_defaults(user_id, deck_id=new_deck_id)

    # Persist type choice as new default
    context.user_data['default_card_type'] = card_type
    db.update_user_defaults(user_id, card_type=card_type)

    context.user_data.pop('cur_card', None)
    context.user_data.pop('cur_deck_id', None)
    context.user_data.pop('temp_type', None)

    await safe_edit_text(
        query,
        "\u2714\ufe0f Saved! Send me another one",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Menu", callback_data='main_menu')]
        ])
    )

    return AddCardState.AWAITING_CONTENT


async def change_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    decks = db.get_all_decks(user_id)

    buttons = utils.get_buttons(decks, 'deck')
    buttons.append([InlineKeyboardButton("\u2795 New deck", callback_data='new_deck')])
    buttons.append([InlineKeyboardButton("\u2190 Back", callback_data='back')])

    await safe_edit_text(
        query,
        "\U0001f4c1 Pick a deck",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

    return AddCardState.AWAITING_DECK


async def edit_card(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    await safe_edit_text(query, "\u270f\ufe0f Send the new content")

    return AddCardState.AWAITING_CONTENT


async def change_type_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show card type picker."""
    query = update.callback_query
    await query.answer()

    current = context.user_data.get('temp_type') or context.user_data.get('default_card_type', 'basic')

    _EMOJIS = {'basic': '\U0001f4c4', 'reverse': '\U0001f501'}

    def _label(name: str) -> str:
        base = f"{_EMOJIS[name]} {name.capitalize()}"
        return f"\u2714 {base}" if current == name else base

    await safe_edit_text(
        query,
        "<b>Card type</b>\n\n"
        "\U0001f4c4 Basic \u2014 one card (front \u2192 back)\n"
        "\U0001f501 Reverse \u2014 two cards (front \u2192 back <b>+</b> back \u2192 front)",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(_label("basic"), callback_data='set_type_basic'),
                InlineKeyboardButton(_label("reverse"), callback_data='set_type_reverse'),
            ],
            [InlineKeyboardButton("\u2190 Back", callback_data='type_back')],
        ])
    )

    return AddCardState.CONFIRMATION_PREVIEW


async def set_card_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """User picked a type — store it and return to preview."""
    query = update.callback_query
    await query.answer()

    card_type = query.data.split('_')[2]  # set_type_basic → 'basic', set_type_reverse → 'reverse'
    context.user_data['temp_type'] = card_type

    await hand_flow.preview(query, context)
    return AddCardState.CONFIRMATION_PREVIEW


async def type_back(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Back from type picker — re-show preview without changing anything."""
    query = update.callback_query
    await query.answer()

    await hand_flow.preview(query, context)
    return AddCardState.CONFIRMATION_PREVIEW
