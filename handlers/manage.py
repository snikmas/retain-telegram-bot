import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from telegram.ext import (
    ContextTypes, ConversationHandler,
    MessageHandler, CommandHandler, CallbackQueryHandler, filters,
)

import database.database as db
from utils.constants import ManageState
from utils.telegram_helpers import safe_edit_text, safe_send_text
from utils.utils import parse_text

CARDS_PER_PAGE = 5
FRONT_MAX = 30


def _truncate(text: str, max_len: int) -> str:
    return text if len(text) <= max_len else text[:max_len - 1] + '\u2026'


async def _show_deck_detail(
    query: CallbackQuery,
    context: ContextTypes.DEFAULT_TYPE,
    deck_id: int,
    page: int = 0,
) -> None:
    """Render the deck detail view (card list with edit/delete buttons)."""
    user_id = query.from_user.id

    deck_name = db.get_deck_name(deck_id)
    if not deck_name:
        await safe_edit_text(
            query,
            "Deck not found.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton('\U0001f4da My Decks', callback_data='my_decks')]
            ]),
        )
        return

    cards = db.get_cards_in_deck(deck_id, user_id)
    total = len(cards)
    total_pages = max(1, (total + CARDS_PER_PAGE - 1) // CARDS_PER_PAGE)
    page = max(0, min(page, total_pages - 1))

    context.user_data['manage_deck_id'] = deck_id
    context.user_data['manage_deck_page'] = page

    start = page * CARDS_PER_PAGE
    page_cards = cards[start:start + CARDS_PER_PAGE]

    if total_pages > 1:
        header = f"\U0001f4da {deck_name} \u00b7 {total} cards  ({page + 1}/{total_pages})"
    else:
        header = f"\U0001f4da {deck_name} \u00b7 {total} cards"

    buttons: list[list[InlineKeyboardButton]] = []

    for card in page_cards:
        cid = card['card_id']
        label = _truncate(card['front'], FRONT_MAX)
        buttons.append([
            InlineKeyboardButton(label, callback_data=f'card_info_{cid}'),
            InlineKeyboardButton('\u270f\ufe0f', callback_data=f'card_edit_{cid}'),
            InlineKeyboardButton('\U0001f5d1\ufe0f', callback_data=f'card_delete_{cid}'),
        ])

    if total_pages > 1:
        nav: list[InlineKeyboardButton] = []
        if page > 0:
            nav.append(InlineKeyboardButton('\u2190', callback_data=f'deck_page_{deck_id}_{page - 1}'))
        if page < total_pages - 1:
            nav.append(InlineKeyboardButton('\u2192', callback_data=f'deck_page_{deck_id}_{page + 1}'))
        if nav:
            buttons.append(nav)

    buttons.append([
        InlineKeyboardButton('\u270f\ufe0f Rename', callback_data=f'deck_rename_{deck_id}'),
        InlineKeyboardButton('\U0001f5d1\ufe0f Delete deck', callback_data=f'deck_delete_{deck_id}'),
    ])
    buttons.append([InlineKeyboardButton('\U0001f4da My Decks', callback_data='my_decks')])

    await safe_edit_text(query, header, reply_markup=InlineKeyboardMarkup(buttons))


# ── Standalone callbacks ──────────────────────────────────────

async def deck_open(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    deck_id = int(query.data.split('_')[2])  # deck_open_<id>
    await _show_deck_detail(query, context, deck_id)


async def deck_cards_page(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    parts = query.data.split('_')  # deck_page_<deck_id>_<page>
    deck_id = int(parts[2])
    page = int(parts[3])
    await _show_deck_detail(query, context, deck_id, page)


async def card_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show full card content as a popup alert."""
    query = update.callback_query
    card_id = int(query.data.split('_')[2])  # card_info_<id>
    user_id = update.effective_user.id

    card = db.get_card(card_id, user_id)
    if not card:
        await query.answer("Card not found.", show_alert=True)
        return

    front = card['front']
    back = card['back'] or '(empty)'
    await query.answer(f"Front:\n{front}\n\nBack:\n{back}", show_alert=True)


async def card_delete_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    card_id = int(query.data.split('_')[2])  # card_delete_<id>
    deck_id = context.user_data.get('manage_deck_id', 0)

    await safe_edit_text(
        query,
        "\U0001f5d1\ufe0f Delete this card? This cannot be undone.",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton('Yes, delete', callback_data=f'card_delete_yes_{card_id}'),
                InlineKeyboardButton('Cancel', callback_data=f'deck_open_{deck_id}'),
            ]
        ]),
    )


async def card_delete_yes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    card_id = int(query.data.split('_')[3])  # card_delete_yes_<id>
    user_id = update.effective_user.id

    db.delete_card(card_id, user_id)

    deck_id = context.user_data.get('manage_deck_id', 0)
    page = context.user_data.get('manage_deck_page', 0)
    await _show_deck_detail(query, context, deck_id, page)


async def deck_delete_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    deck_id = int(query.data.split('_')[2])  # deck_delete_<id>

    deck_name = db.get_deck_name(deck_id) or 'this deck'
    await safe_edit_text(
        query,
        f"\U0001f5d1\ufe0f Delete deck \"{deck_name}\" and all its cards?\nThis cannot be undone.",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton('Yes, delete', callback_data=f'deck_delete_yes_{deck_id}'),
                InlineKeyboardButton('Cancel', callback_data=f'deck_open_{deck_id}'),
            ]
        ]),
    )


async def deck_delete_yes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    deck_id = int(query.data.split('_')[3])  # deck_delete_yes_<id>
    user_id = update.effective_user.id

    db.delete_deck(deck_id, user_id)
    context.user_data.pop('manage_deck_id', None)
    context.user_data.pop('manage_deck_page', None)

    await safe_edit_text(
        query,
        "\U0001f5d1\ufe0f Deck deleted.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton('\U0001f4da My Decks', callback_data='my_decks')]
        ]),
    )


# ── Edit card conversation ────────────────────────────────────

async def start_edit_card(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    card_id = int(query.data.split('_')[2])  # card_edit_<id>
    user_id = update.effective_user.id

    card = db.get_card(card_id, user_id)
    if not card:
        await safe_edit_text(query, "Card not found.")
        return ConversationHandler.END

    context.user_data['editing_card_id'] = card_id

    front = card['front']
    back = card['back'] or ''

    await safe_edit_text(
        query,
        f"\u270f\ufe0f Edit card\n\n"
        f"Front: {front}\n"
        f"Back: {back or '(empty)'}\n\n"
        "Send new content (front | back or two lines):\n/cancel to abort",
    )
    return ManageState.EDIT_CARD_CONTENT


async def receive_edit_content(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    parsed = parse_text(text)
    context.user_data['edit_card_parsed'] = parsed

    front = parsed['front']
    back = parsed['back'] or '(empty)'

    await safe_send_text(
        update.message,
        f"\U0001f4cb Preview\n\nFront: {front}\nBack: {back}",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton('\u2714 Save', callback_data='save_edit'),
                InlineKeyboardButton('\u2716 Cancel', callback_data='cancel_edit'),
            ]
        ]),
    )
    return ManageState.EDIT_CARD_PREVIEW


async def save_edit_card(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    card_id = context.user_data.pop('editing_card_id', None)
    parsed = context.user_data.pop('edit_card_parsed', {})
    user_id = update.effective_user.id

    if card_id and parsed:
        db.update_card_content(card_id, user_id, parsed['front'], parsed.get('back', ''))

    deck_id = context.user_data.get('manage_deck_id', 0)
    page = context.user_data.get('manage_deck_page', 0)
    await _show_deck_detail(query, context, deck_id, page)
    return ConversationHandler.END


async def cancel_edit_card(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    context.user_data.pop('editing_card_id', None)
    context.user_data.pop('edit_card_parsed', None)

    deck_id = context.user_data.get('manage_deck_id', 0)
    page = context.user_data.get('manage_deck_page', 0)
    await _show_deck_detail(query, context, deck_id, page)
    return ConversationHandler.END


# ── Rename deck conversation ──────────────────────────────────

async def start_rename_deck(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    deck_id = int(query.data.split('_')[2])  # deck_rename_<id>

    deck_name = db.get_deck_name(deck_id) or 'this deck'
    context.user_data['renaming_deck_id'] = deck_id

    await safe_edit_text(
        query,
        f"\u270f\ufe0f Rename \"{deck_name}\"\n\nSend the new name:\n/cancel to abort",
    )
    return ManageState.RENAME_DECK


async def receive_rename(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    new_name = update.message.text.strip()
    user_id = update.effective_user.id
    deck_id = context.user_data.get('renaming_deck_id')

    if not new_name:
        await safe_send_text(update.message, "Name can't be empty. Try again:")
        return ManageState.RENAME_DECK

    if len(new_name) > 100:
        await safe_send_text(update.message, "Name too long (max 100 chars). Try again:")
        return ManageState.RENAME_DECK

    if deck_id:
        db.rename_deck(deck_id, user_id, new_name)
        context.user_data.pop('renaming_deck_id', None)

    await safe_send_text(
        update.message,
        f"\u2714\ufe0f Renamed to \"{new_name}\"",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton('\U0001f4da My Decks', callback_data='my_decks')]
        ]),
    )
    return ConversationHandler.END


async def cancel_manage(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop('editing_card_id', None)
    context.user_data.pop('edit_card_parsed', None)
    context.user_data.pop('renaming_deck_id', None)

    if update.callback_query:
        await update.callback_query.answer()
        await safe_edit_text(update.callback_query, "\u274c Cancelled")
    else:
        await safe_send_text(update.message, "\u274c Cancelled")

    return ConversationHandler.END


# ── ConversationHandlers (imported in bot.py) ─────────────────

edit_card_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(start_edit_card, pattern=r'^card_edit_\d+$')],
    per_message=False,
    states={
        ManageState.EDIT_CARD_CONTENT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, receive_edit_content),
        ],
        ManageState.EDIT_CARD_PREVIEW: [
            CallbackQueryHandler(save_edit_card, pattern='^save_edit$'),
            CallbackQueryHandler(cancel_edit_card, pattern='^cancel_edit$'),
        ],
    },
    fallbacks=[CommandHandler('cancel', cancel_manage)],
)

rename_deck_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(start_rename_deck, pattern=r'^deck_rename_\d+$')],
    per_message=False,
    states={
        ManageState.RENAME_DECK: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, receive_rename),
        ],
    },
    fallbacks=[CommandHandler('cancel', cancel_manage)],
)
