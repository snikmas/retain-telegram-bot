import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

import database.database as db
from utils.constants import ReviewState, MAIN_MENU_BUTTONS
from utils.srs import schedule, next_interval_label, AGAIN, HARD, GOOD, EASY


async def review_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry point: user clicks 'Review'."""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    cards = db.get_due_cards(user_id)

    if not cards:
        await query.edit_message_text(
            "Nothing due — you're all caught up.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Menu", callback_data='main_menu')]
            ])
        )
        return ConversationHandler.END

    context.user_data['review_cards'] = cards
    context.user_data['review_index'] = 0
    context.user_data['review_correct'] = 0
    context.user_data['review_total'] = len(cards)

    count = len(cards)
    await query.edit_message_text(
        f"{count} card{'s' if count != 1 else ''} to review. Let's go."
    )

    return await _show_front(query.message, context)


async def show_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

    deck_name = db.get_deck_name(card['deck_id']) or "—"
    progress = f"{index + 1} / {len(cards)}"

    rating_buttons = _build_rating_buttons(card)

    if is_photo:
        text = (
            f"{back if back else '(no back)'}\n\n"
            f"{deck_name}  ·  {progress}"
        )
        try:
            await query.edit_message_caption(
                caption=text,
                reply_markup=InlineKeyboardMarkup(rating_buttons)
            )
        except Exception:
            await query.message.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(rating_buttons)
            )
    else:
        text = (
            f"{front}\n"
            f"{'—' * min(len(front), 20)}\n"
            f"{back}\n\n"
            f"{deck_name}  ·  {progress}"
        )
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(rating_buttons)
        )

    return ReviewState.RATING


async def rate_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

    chat_id = query.message.chat_id
    try:
        await query.message.delete()
    except Exception:
        pass

    return await _show_front_in_chat(chat_id, context)


async def cancel_review(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User cancels mid-review. Works for both callback button and /cancel command."""
    reviewed = context.user_data.get('review_index', 0)
    _cleanup_review_data(context)

    text = f"Stopped after {reviewed} card{'s' if reviewed != 1 else ''}."
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("Menu", callback_data='main_menu')]
    ])

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, reply_markup=markup)
    else:
        await update.message.reply_text(text, reply_markup=markup)

    return ConversationHandler.END


# ============================================================
# Private helpers
# ============================================================

async def _show_front(message, context):
    """Show the front of the current card."""
    cards = context.user_data.get('review_cards', [])
    index = context.user_data.get('review_index', 0)

    if index >= len(cards):
        return ConversationHandler.END

    card = cards[index]
    is_photo = card.get('content_type') == 'photo'
    progress = f"{index + 1} / {len(cards)}"

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("Show answer", callback_data='show_answer')],
        [InlineKeyboardButton("Stop", callback_data='cancel_review')]
    ])

    if is_photo:
        await message.reply_photo(
            photo=card['front'], caption=progress, reply_markup=buttons
        )
    else:
        text = f"{card['front']}\n\n{progress}"
        await message.reply_text(text, reply_markup=buttons)

    return ReviewState.SHOWING_FRONT


async def _show_front_in_chat(chat_id, context):
    """Show front of current card by sending a new message to the chat."""
    cards = context.user_data.get('review_cards', [])
    index = context.user_data.get('review_index', 0)

    if index >= len(cards):
        return ConversationHandler.END

    card = cards[index]
    is_photo = card.get('content_type') == 'photo'
    progress = f"{index + 1} / {len(cards)}"
    bot = context.bot

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("Show answer", callback_data='show_answer')],
        [InlineKeyboardButton("Stop", callback_data='cancel_review')]
    ])

    if is_photo:
        await bot.send_photo(
            chat_id=chat_id, photo=card['front'],
            caption=progress, reply_markup=buttons
        )
    else:
        text = f"{card['front']}\n\n{progress}"
        await bot.send_message(chat_id=chat_id, text=text, reply_markup=buttons)

    return ReviewState.SHOWING_FRONT


def _build_rating_buttons(card):
    """Build rating buttons with interval previews."""
    return [
        [
            InlineKeyboardButton(
                f"Again  {next_interval_label(card, AGAIN)}",
                callback_data=f'rate_{AGAIN}'
            ),
            InlineKeyboardButton(
                f"Hard  {next_interval_label(card, HARD)}",
                callback_data=f'rate_{HARD}'
            ),
        ],
        [
            InlineKeyboardButton(
                f"Good  {next_interval_label(card, GOOD)}",
                callback_data=f'rate_{GOOD}'
            ),
            InlineKeyboardButton(
                f"Easy  {next_interval_label(card, EASY)}",
                callback_data=f'rate_{EASY}'
            ),
        ],
    ]


async def _finish_review(query, context):
    """Show review summary and end conversation."""
    total = context.user_data.get('review_total', 0)
    correct = context.user_data.get('review_correct', 0)

    _cleanup_review_data(context)

    if total == 0:
        ratio_bar = ""
    else:
        filled = round(correct / total * 10)
        ratio_bar = f"{'|' * filled}{'.' * (10 - filled)}"

    text = (
        f"Done.\n\n"
        f"  Reviewed   {total}\n"
        f"  Recalled   {correct} / {total}    [{ratio_bar}]\n"
    )

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("+ New Card", callback_data='add_card'),
         InlineKeyboardButton("Menu", callback_data='main_menu')]
    ])

    try:
        await query.edit_message_text(text, reply_markup=markup)
    except Exception:
        await query.message.reply_text(text, reply_markup=markup)

    return ConversationHandler.END


def _cleanup_review_data(context):
    context.user_data.pop('review_cards', None)
    context.user_data.pop('review_index', None)
    context.user_data.pop('review_correct', None)
    context.user_data.pop('review_total', None)
