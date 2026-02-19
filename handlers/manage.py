import html
import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from telegram.ext import (
    ContextTypes, ConversationHandler,
    MessageHandler, CommandHandler, CallbackQueryHandler, filters,
)

import database.database as db
from handlers.start import force_start
from utils.constants import ManageState, DECK_NAME_MAX
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
    user_id = query.from_user.id

    deck_name = db.get_deck_name(deck_id)
    if not deck_name:
        await safe_edit_text(
            query,
            "Deck not found.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton('My Decks', callback_data='my_decks')]
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
    context.user_data['manage_page_cards'] = page_cards

    # Build numbered text list
    lines = []
    for i, card in enumerate(page_cards, start=1):
        if card.get('content_type') == 'photo':
            label = '\U0001f4f7 Photo card'
        else:
            label = _truncate(card['front'], FRONT_MAX)
        lines.append(f"{i}. {html.escape(label)}")

    card_list = '\n'.join(lines) if lines else '<i>No cards yet</i>'

    if total_pages > 1:
        header = f"<b>\U0001f4da {html.escape(deck_name)}</b> \u00b7 {total} cards  ({page + 1}/{total_pages})"
    else:
        header = f"<b>\U0001f4da {html.escape(deck_name)}</b> \u00b7 {total} cards"

    text = f"{header}\n\n{card_list}"

    buttons: list[list[InlineKeyboardButton]] = []

    if total_pages > 1:
        nav: list[InlineKeyboardButton] = []
        if page > 0:
            nav.append(InlineKeyboardButton('\u2190', callback_data=f'deck_page_{deck_id}_{page - 1}'))
        if page < total_pages - 1:
            nav.append(InlineKeyboardButton('\u2192', callback_data=f'deck_page_{deck_id}_{page + 1}'))
        if nav:
            buttons.append(nav)

    if total > 0:
        buttons.append([
            InlineKeyboardButton('\u270f\ufe0f Edit card', callback_data=f'pick_edit_{deck_id}'),
            InlineKeyboardButton('\U0001f5d1\ufe0f Delete card', callback_data=f'pick_delete_{deck_id}'),
        ])

    buttons.append([
        InlineKeyboardButton('\u270f\ufe0f Rename', callback_data=f'deck_rename_{deck_id}'),
        InlineKeyboardButton('\U0001f5d1\ufe0f Delete deck', callback_data=f'deck_delete_{deck_id}'),
    ])
    buttons.append([InlineKeyboardButton('My Decks', callback_data='my_decks')])

    await safe_edit_text(query, text, reply_markup=InlineKeyboardMarkup(buttons))


# ── Standalone callbacks ──────────────────────────────────────

async def deck_open(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    deck_id = int(query.data.split('_')[2])
    await _show_deck_detail(query, context, deck_id)


async def deck_cards_page(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    parts = query.data.split('_')
    deck_id = int(parts[2])
    page = int(parts[3])
    await _show_deck_detail(query, context, deck_id, page)


async def card_delete_yes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    card_id = int(query.data.split('_')[3])
    user_id = update.effective_user.id

    deck_id = context.user_data.get('manage_deck_id', 0)
    db.delete_card(card_id, user_id)

    remaining = db.get_cards_in_deck(deck_id, user_id)
    if not remaining:
        db.delete_deck(deck_id, user_id)
        context.user_data.pop('manage_deck_id', None)
        context.user_data.pop('manage_deck_page', None)
        context.user_data.pop('manage_page_cards', None)
        await safe_edit_text(
            query,
            "\U0001f5d1\ufe0f Card deleted. Deck is now empty and was removed too.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('\U0001f4da My Decks', callback_data='my_decks')]])
        )
    else:
        page = context.user_data.get('manage_deck_page', 0)
        await _show_deck_detail(query, context, deck_id, page)


async def deck_delete_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    deck_id = int(query.data.split('_')[2])

    deck_name = db.get_deck_name(deck_id) or 'this deck'
    await safe_edit_text(
        query,
        f"\U0001f5d1\ufe0f Delete deck <b>{html.escape(deck_name)}</b> and all its cards?\n<i>This cannot be undone.</i>",
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
    deck_id = int(query.data.split('_')[3])
    user_id = update.effective_user.id

    db.delete_deck(deck_id, user_id)
    context.user_data.pop('manage_deck_id', None)
    context.user_data.pop('manage_deck_page', None)
    context.user_data.pop('manage_page_cards', None)

    # Go directly to My Decks — no intermediate "Deck deleted" message
    from handlers.decks_menu import _build_decks_markup, DECKS_PER_PAGE
    decks = db.get_decks_with_stats(user_id)
    if not decks:
        await safe_edit_text(
            query,
            "\U0001f4da No decks yet\n\nCreate your first card and a deck will appear here.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("New Card", callback_data='add_card')],
                [InlineKeyboardButton("Menu", callback_data='main_menu')],
            ])
        )
        return

    context.user_data['_decks_cache'] = decks
    total_pages = max(1, (len(decks) + DECKS_PER_PAGE - 1) // DECKS_PER_PAGE)
    header, markup = _build_decks_markup(decks, 0, total_pages)
    await safe_edit_text(query, header, reply_markup=markup)


# ── Pick card to edit conversation ───────────────────────────

async def pick_card_to_edit_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    deck_id = int(query.data.split('_')[2])
    context.user_data['manage_deck_id'] = deck_id

    page_cards = context.user_data.get('manage_page_cards', [])
    count = len(page_cards)

    await safe_edit_text(
        query,
        f"\u270f\ufe0f <b>Edit which card?</b>\n\nSend a number 1\u2013{count}.\n<i>/cancel to abort</i>",
    )
    return ManageState.PICK_CARD_TO_EDIT


async def receive_pick_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    page_cards = context.user_data.get('manage_page_cards', [])

    try:
        n = int(text)
    except ValueError:
        await safe_send_text(update.message, f"\u274c Not a number. Send 1\u2013{len(page_cards)}:")
        return ManageState.PICK_CARD_TO_EDIT

    if not (1 <= n <= len(page_cards)):
        await safe_send_text(update.message, f"\u274c Enter a number between 1 and {len(page_cards)}:")
        return ManageState.PICK_CARD_TO_EDIT

    card = page_cards[n - 1]
    context.user_data['editing_card_id'] = card['card_id']

    if card.get('content_type') == 'photo':
        context.user_data['editing_card_photo'] = True
        current_caption = html.escape(card['back']) if card['back'] else '<i>(empty)</i>'
        await safe_send_text(
            update.message,
            f"\u270f\ufe0f <b>Edit caption</b>\n\n{current_caption}\n\n"
            f"<i>Send the new caption.\n/cancel to abort</i>",
        )
    else:
        context.user_data.pop('editing_card_photo', None)
        raw_front = card['front']
        raw_back = card['back'] or ''
        copyable = f"{raw_front} | {raw_back}" if raw_back else raw_front
        await safe_send_text(
            update.message,
            f"\u270f\ufe0f <b>Edit card</b>\n\n"
            f"<code>{html.escape(copyable)}</code>\n\n"
            f"<i>Tap the text above to copy, edit and send.\n/cancel to abort</i>",
        )
    return ManageState.EDIT_CARD_CONTENT


# ── Pick card to delete conversation ─────────────────────────

async def pick_card_to_delete_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    deck_id = int(query.data.split('_')[2])
    context.user_data['manage_deck_id'] = deck_id

    page_cards = context.user_data.get('manage_page_cards', [])
    count = len(page_cards)

    await safe_edit_text(
        query,
        f"\U0001f5d1\ufe0f <b>Delete which card?</b>\n\nSend a number 1\u2013{count}.\n<i>/cancel to abort</i>",
    )
    return ManageState.PICK_CARD_TO_DELETE


async def receive_pick_delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    page_cards = context.user_data.get('manage_page_cards', [])
    deck_id = context.user_data.get('manage_deck_id', 0)

    try:
        n = int(text)
    except ValueError:
        await safe_send_text(update.message, f"\u274c Not a number. Send 1\u2013{len(page_cards)}:")
        return ManageState.PICK_CARD_TO_DELETE

    if not (1 <= n <= len(page_cards)):
        await safe_send_text(update.message, f"\u274c Enter a number between 1 and {len(page_cards)}:")
        return ManageState.PICK_CARD_TO_DELETE

    card = page_cards[n - 1]
    card_id = card['card_id']
    if card.get('content_type') == 'photo':
        label = '\U0001f4f7 Photo card'
    else:
        label = _truncate(card['front'], FRONT_MAX)

    await safe_send_text(
        update.message,
        f"\U0001f5d1\ufe0f Delete <b>{html.escape(label)}</b>? This cannot be undone.",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton('Yes, delete', callback_data=f'card_delete_yes_{card_id}'),
                InlineKeyboardButton('Cancel', callback_data=f'deck_open_{deck_id}'),
            ]
        ]),
    )
    return ConversationHandler.END


# ── Edit card conversation ────────────────────────────────────

async def start_edit_card(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    card_id = int(query.data.split('_')[2])
    user_id = update.effective_user.id

    card = db.get_card(card_id, user_id)
    if not card:
        await safe_edit_text(query, "Card not found.")
        return ConversationHandler.END

    context.user_data['editing_card_id'] = card_id

    raw_front = card['front']
    raw_back = card['back'] or ''
    copyable = f"{raw_front} | {raw_back}" if raw_back else raw_front

    await safe_edit_text(
        query,
        f"\u270f\ufe0f <b>Edit card</b>\n\n"
        f"<code>{html.escape(copyable)}</code>\n\n"
        f"<i>Tap the text above to copy, edit and send.\n/cancel to abort</i>",
    )
    return ManageState.EDIT_CARD_CONTENT


async def receive_edit_content(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    is_photo = context.user_data.pop('editing_card_photo', False)

    if is_photo:
        context.user_data['edit_card_is_photo'] = True
        context.user_data['edit_card_parsed'] = {'front': None, 'back': text}
        back_display = html.escape(text) if text else '<i>(empty)</i>'
        await safe_send_text(
            update.message,
            f"<b>\U0001f4cb Preview</b>\n\nCaption: {back_display}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton('\u2714 Save', callback_data='save_edit'),
                InlineKeyboardButton('\u2716 Cancel', callback_data='cancel_edit'),
            ]]),
        )
        return ManageState.EDIT_CARD_PREVIEW

    parsed = parse_text(text)
    if not parsed['front']:
        await safe_send_text(update.message, "\u26a0\ufe0f Card can't be empty. Try again:")
        return ManageState.EDIT_CARD_CONTENT

    context.user_data['edit_card_is_photo'] = False
    context.user_data['edit_card_parsed'] = parsed

    front = html.escape(parsed['front'])
    back = html.escape(parsed['back']) if parsed['back'] else '<i>(empty)</i>'

    await safe_send_text(
        update.message,
        f"<b>\U0001f4cb Preview</b>\n\nFront: {front}\nBack: {back}",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton('\u2714 Save', callback_data='save_edit'),
            InlineKeyboardButton('\u2716 Cancel', callback_data='cancel_edit'),
        ]]),
    )
    return ManageState.EDIT_CARD_PREVIEW


async def save_edit_card(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    card_id = context.user_data.pop('editing_card_id', None)
    parsed = context.user_data.pop('edit_card_parsed', {})
    is_photo = context.user_data.pop('edit_card_is_photo', False)
    user_id = update.effective_user.id

    if card_id and parsed:
        if is_photo:
            db.update_card_caption(card_id, user_id, parsed.get('back', ''))
        else:
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
    context.user_data.pop('editing_card_photo', None)
    context.user_data.pop('edit_card_is_photo', None)

    deck_id = context.user_data.get('manage_deck_id', 0)
    page = context.user_data.get('manage_deck_page', 0)
    await _show_deck_detail(query, context, deck_id, page)
    return ConversationHandler.END


# ── Rename deck conversation ──────────────────────────────────

async def start_rename_deck(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    deck_id = int(query.data.split('_')[2])

    deck_name = db.get_deck_name(deck_id) or 'this deck'
    context.user_data['renaming_deck_id'] = deck_id

    await safe_edit_text(
        query,
        f"\u270f\ufe0f Rename <b>{html.escape(deck_name)}</b>\n\n<i>Send the new name:\n/cancel to abort</i>",
    )
    return ManageState.RENAME_DECK


async def receive_rename(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    new_name = update.message.text.strip()
    user_id = update.effective_user.id
    deck_id = context.user_data.get('renaming_deck_id')

    if not new_name:
        await safe_send_text(update.message, "Name can't be empty. Try again:")
        return ManageState.RENAME_DECK

    if len(new_name) > DECK_NAME_MAX:
        await safe_send_text(update.message, f"Name too long (max {DECK_NAME_MAX} chars). Try again:")
        return ManageState.RENAME_DECK

    if deck_id:
        db.rename_deck(deck_id, user_id, new_name)
        context.user_data.pop('renaming_deck_id', None)

    await safe_send_text(
        update.message,
        f"\u2714\ufe0f Renamed to <b>{html.escape(new_name)}</b>",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton('My Decks', callback_data='my_decks')]
        ]),
    )
    return ConversationHandler.END


async def cancel_manage(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop('editing_card_id', None)
    context.user_data.pop('edit_card_parsed', None)
    context.user_data.pop('editing_card_photo', None)
    context.user_data.pop('edit_card_is_photo', None)
    context.user_data.pop('renaming_deck_id', None)

    from handlers.start import build_main_menu
    text, markup = build_main_menu(update.effective_user.id)

    if update.callback_query:
        await update.callback_query.answer()
        await safe_edit_text(update.callback_query, text, reply_markup=markup)
    else:
        await safe_send_text(update.message, text, reply_markup=markup)

    return ConversationHandler.END


# ── ConversationHandlers ──────────────────────────────────────

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
    fallbacks=[CommandHandler('cancel', cancel_manage), CommandHandler('start', force_start)],
)

rename_deck_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(start_rename_deck, pattern=r'^deck_rename_\d+$')],
    per_message=False,
    states={
        ManageState.RENAME_DECK: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, receive_rename),
        ],
    },
    fallbacks=[CommandHandler('cancel', cancel_manage), CommandHandler('start', force_start)],
)

pick_edit_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(pick_card_to_edit_entry, pattern=r'^pick_edit_\d+$')],
    per_message=False,
    states={
        ManageState.PICK_CARD_TO_EDIT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, receive_pick_edit),
        ],
        ManageState.EDIT_CARD_CONTENT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, receive_edit_content),
        ],
        ManageState.EDIT_CARD_PREVIEW: [
            CallbackQueryHandler(save_edit_card, pattern='^save_edit$'),
            CallbackQueryHandler(cancel_edit_card, pattern='^cancel_edit$'),
        ],
    },
    fallbacks=[CommandHandler('cancel', cancel_manage), CommandHandler('start', force_start)],
)

pick_delete_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(pick_card_to_delete_entry, pattern=r'^pick_delete_\d+$')],
    per_message=False,
    states={
        ManageState.PICK_CARD_TO_DELETE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, receive_pick_delete),
        ],
    },
    fallbacks=[CommandHandler('cancel', cancel_manage), CommandHandler('start', force_start)],
)
