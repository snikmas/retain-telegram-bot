import logging
from collections import defaultdict
from typing import Any

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, Message
from telegram.ext import ContextTypes, ConversationHandler

import database.database as db
from utils.constants import ReviewState, MAIN_MENU_BUTTONS
from utils.srs import schedule, schedule_all_ratings, _format_interval, AGAIN, HARD, GOOD, EASY
from utils.telegram_helpers import safe_edit_text, safe_edit_caption, safe_send_text, safe_send_photo, safe_delete


async def review_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point: user clicks 'Review'."""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    cards = db.get_due_cards(user_id)

    if not cards:
        await safe_edit_text(
            query,
            "\u2728 Nothing due — you're all caught up!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("\U0001f3e0 Menu", callback_data='main_menu')]
            ])
        )
        return ConversationHandler.END

    # Group by deck to decide whether to show picker
    deck_counts: dict[int, int] = defaultdict(int)
    for card in cards:
        deck_counts[card['deck_id']] += 1

    if len(deck_counts) > 1:
        # Store all cards; picker will filter
        context.user_data['review_cards'] = cards
        context.user_data['review_index'] = 0
        context.user_data['review_correct'] = 0
        context.user_data['review_total'] = len(cards)

        picker_buttons: list[list[InlineKeyboardButton]] = []
        for deck_id, count in deck_counts.items():
            deck_name = db.get_deck_name(deck_id) or f"Deck {deck_id}"
            picker_buttons.append([InlineKeyboardButton(
                f"\U0001f4da {deck_name}  \u00b7  {count} due",
                callback_data=f'review_deck_{deck_id}',
            )])
        picker_buttons.append([InlineKeyboardButton(
            f"\u25b6 All decks \u00b7 {len(cards)} due",
            callback_data='review_deck_all',
        )])

        total = len(cards)
        await safe_edit_text(
            query,
            f"\U0001f9e0 {total} card{'s' if total != 1 else ''} due\n\nChoose a deck:",
            reply_markup=InlineKeyboardMarkup(picker_buttons),
        )
        return ReviewState.DECK_PICKER

    # Single deck (or all same deck) — start immediately
    return await _start_review(query, cards, context)


async def review_deck_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """User picked a specific deck from the picker."""
    query = update.callback_query
    await query.answer()

    deck_id = int(query.data.split('_')[2])  # review_deck_<id>
    all_cards = context.user_data.get('review_cards', [])
    filtered = [c for c in all_cards if c['deck_id'] == deck_id]

    return await _start_review(query, filtered, context)


async def review_all_decks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """User picked 'All decks' from the picker."""
    query = update.callback_query
    await query.answer()

    cards = context.user_data.get('review_cards', [])
    return await _start_review(query, cards, context)


async def review_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/review slash command — sends a message with a Review button."""
    user_id = update.effective_user.id
    cards = db.get_due_cards(user_id)
    count = len(cards)

    if count == 0:
        await safe_send_text(update.message, "\u2728 Nothing due — you're all caught up!")
        return

    await safe_send_text(
        update.message,
        f"\U0001f9e0 {count} card{'s' if count != 1 else ''} due",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton('\u25b6 Review', callback_data='review')]
        ]),
    )


async def show_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """User taps 'Show Answer' — reveal back + rating buttons."""
    query = update.callback_query
    await query.answer()

    cards = context.user_data.get('review_cards', [])
    index = context.user_data.get('review_index', 0)

    if index >= len(cards):
        return await _finish_review(query, context)

    card = cards[index]
    front = card['front']
    back = card['back']
    is_photo = card.get('content_type') == 'photo'

    deck_name = db.get_deck_name(card['deck_id']) or "\u2014"
    progress = f"{index + 1}/{len(cards)}"

    rating_buttons = InlineKeyboardMarkup(_build_rating_buttons(card))

    if is_photo:
        text = (
            f"{back if back else '(no back)'}\n\n"
            f"\U0001f4c1 {deck_name}  \u00b7  {progress}"
        )
        ok = await safe_edit_caption(query, text, reply_markup=rating_buttons)
        if not ok:
            await safe_send_text(query.message, text, reply_markup=rating_buttons)
    else:
        text = (
            f"{front}\n\n"
            f"\U0001f4a1 {back}\n\n"
            f"\U0001f4c1 {deck_name}  \u00b7  {progress}"
        )
        await safe_edit_text(query, text, reply_markup=rating_buttons)

    return ReviewState.RATING


async def rate_card(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """User rates a card — update SRS, move to next card."""
    query = update.callback_query
    await query.answer()

    rating = int(query.data.split('_')[1])

    cards = context.user_data.get('review_cards', [])
    index = context.user_data.get('review_index', 0)

    if index >= len(cards):
        return await _finish_review(query, context)

    card = cards[index]

    result = schedule(card, rating)

    db.update_card_srs(
        card['card_id'],
        result['due_date'],
        result['stability'],
        result['difficulty'],
        result['reps'],
        result['lapses'],
        result['state'],
        result['scheduled_days'],
    )

    if rating >= GOOD:
        context.user_data['review_correct'] = context.user_data.get('review_correct', 0) + 1

    logging.info(
        f"Card {card['card_id']}: rated {rating}, "
        f"next due {result['due_date']}, state={result['state']}"
    )

    context.user_data['review_index'] = index + 1

    if index + 1 >= len(cards):
        return await _finish_review(query, context)

    next_card = cards[index + 1]
    next_is_photo = next_card.get('content_type') == 'photo'
    cur_is_photo = card.get('content_type') == 'photo'

    # text→text: just edit in place (1 API call instead of 2)
    if not cur_is_photo and not next_is_photo:
        return await _show_front_edit(query, context)

    # photo↔text transition: must delete + send new message
    chat_id = query.message.chat_id
    await safe_delete(query.message)

    return await _show_front_in_chat(chat_id, context)


async def cancel_review(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """User cancels mid-review. Works for both callback button and /cancel command."""
    reviewed = context.user_data.get('review_index', 0)
    _cleanup_review_data(context)

    text = f"\u23f9 Stopped after {reviewed} card{'s' if reviewed != 1 else ''}"
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("\U0001f3e0 Menu", callback_data='main_menu')]
    ])

    if update.callback_query:
        await update.callback_query.answer()
        await safe_edit_text(update.callback_query, text, reply_markup=markup)
    else:
        await safe_send_text(update.message, text, reply_markup=markup)

    return ConversationHandler.END


# ============================================================
# Private helpers
# ============================================================

async def _start_review(
    query: CallbackQuery,
    cards: list[dict[str, Any]],
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    """Set up review state and show the first card."""
    context.user_data['review_cards'] = cards
    context.user_data['review_index'] = 0
    context.user_data['review_correct'] = 0
    context.user_data['review_total'] = len(cards)

    count = len(cards)
    await safe_edit_text(
        query,
        f"\U0001f9e0 {count} card{'s' if count != 1 else ''} to review"
    )

    return await _show_front(query.message, context)


def _progress_label(index: int, total: int) -> str:
    return f"{index + 1}/{total}"


async def _show_front(message: Message, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show the front of the current card."""
    cards = context.user_data.get('review_cards', [])
    index = context.user_data.get('review_index', 0)

    if index >= len(cards):
        return ConversationHandler.END

    card = cards[index]
    is_photo = card.get('content_type') == 'photo'
    progress = _progress_label(index, len(cards))

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("\U0001f440 Show answer", callback_data='show_answer')],
        [InlineKeyboardButton("\u23f9 Stop", callback_data='cancel_review')]
    ])

    if is_photo:
        await safe_send_photo(message, card['front'], caption=progress, reply_markup=buttons)
    else:
        text = f"{card['front']}\n\n{progress}"
        await safe_send_text(message, text, reply_markup=buttons)

    return ReviewState.SHOWING_FRONT


async def _show_front_edit(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Edit the current message to show the next card's front (text→text only)."""
    cards = context.user_data.get('review_cards', [])
    index = context.user_data.get('review_index', 0)

    if index >= len(cards):
        return ConversationHandler.END

    card = cards[index]
    progress = _progress_label(index, len(cards))

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("\U0001f440 Show answer", callback_data='show_answer')],
        [InlineKeyboardButton("\u23f9 Stop", callback_data='cancel_review')]
    ])

    text = f"{card['front']}\n\n{progress}"
    await safe_edit_text(query, text, reply_markup=buttons)

    return ReviewState.SHOWING_FRONT


async def _show_front_in_chat(chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show front of current card by sending a new message to the chat."""
    cards = context.user_data.get('review_cards', [])
    index = context.user_data.get('review_index', 0)

    if index >= len(cards):
        return ConversationHandler.END

    card = cards[index]
    is_photo = card.get('content_type') == 'photo'
    progress = _progress_label(index, len(cards))
    target = (chat_id, context.bot)

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("\U0001f440 Show answer", callback_data='show_answer')],
        [InlineKeyboardButton("\u23f9 Stop", callback_data='cancel_review')]
    ])

    if is_photo:
        await safe_send_photo(target, card['front'], caption=progress, reply_markup=buttons)
    else:
        text = f"{card['front']}\n\n{progress}"
        await safe_send_text(target, text, reply_markup=buttons)

    return ReviewState.SHOWING_FRONT


def _build_rating_buttons(card: dict[str, Any]) -> list[list[InlineKeyboardButton]]:
    """Build rating buttons with interval previews (single schedule pass)."""
    results = schedule_all_ratings(card)
    return [
        [
            InlineKeyboardButton(
                f"\U0001f534 Again {_format_interval(results[AGAIN])}",
                callback_data=f'rate_{AGAIN}'
            ),
            InlineKeyboardButton(
                f"\U0001f7e0 Hard {_format_interval(results[HARD])}",
                callback_data=f'rate_{HARD}'
            ),
        ],
        [
            InlineKeyboardButton(
                f"\U0001f7e2 Good {_format_interval(results[GOOD])}",
                callback_data=f'rate_{GOOD}'
            ),
            InlineKeyboardButton(
                f"\U0001f535 Easy {_format_interval(results[EASY])}",
                callback_data=f'rate_{EASY}'
            ),
        ],
    ]


async def _finish_review(query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show review summary and end conversation."""
    total = context.user_data.get('review_total', 0)
    correct = context.user_data.get('review_correct', 0)

    _cleanup_review_data(context)

    text = f"\U0001f389 Done! {correct}/{total} recalled"

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("\U0001f4dd New Card", callback_data='add_card'),
         InlineKeyboardButton("\U0001f3e0 Menu", callback_data='main_menu')]
    ])

    await safe_edit_text(query, text, reply_markup=markup)

    return ConversationHandler.END


def _cleanup_review_data(context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.pop('review_cards', None)
    context.user_data.pop('review_index', None)
    context.user_data.pop('review_correct', None)
    context.user_data.pop('review_total', None)
