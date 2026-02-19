"""
Safe wrappers for Telegram API calls.

Every handler uses these instead of raw query.edit_message_text / bot.send_message.
If the API call fails, these recover gracefully instead of crashing the handler.

DISCIPLINE RULE — all callers must:
  - Pass parse_mode='HTML' (the default here)
  - Wrap every piece of user-supplied text in html.escape() before embedding it
    in a format string. User content = anything from card['front'], card['back'],
    deck_name, username, or any field read from the DB.
  - Never pass raw f-strings with user data directly — they will silently corrupt
    or raise BadRequest if the content contains <, >, or &.

Safe pattern:
    await safe_edit_text(query, f"Deck: <b>{html.escape(deck_name)}</b>")

Unsafe (never do this):
    await safe_edit_text(query, f"Deck: <b>{deck_name}</b>")
"""

import logging
from typing import Any

from telegram import CallbackQuery, InlineKeyboardMarkup, Message
from telegram.error import BadRequest, Forbidden, TimedOut, NetworkError

logger = logging.getLogger(__name__)


async def safe_edit_text(
    query: CallbackQuery,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    parse_mode: str = 'HTML',
) -> bool:
    """Edit a callback query's message text. Falls back to reply on failure."""
    try:
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
        return True
    except BadRequest as e:
        msg = str(e).lower()
        if "message is not modified" in msg:
            return True  # same content — harmless
        if "message to edit not found" in msg:
            return await _fallback_reply(query, text, reply_markup, parse_mode)
        logger.warning(f"safe_edit_text BadRequest: {e}")
        return await _fallback_reply(query, text, reply_markup, parse_mode)
    except (TimedOut, NetworkError) as e:
        logger.warning(f"safe_edit_text network error: {e}")
        return False


async def safe_edit_caption(
    query: CallbackQuery,
    caption: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    parse_mode: str = 'HTML',
) -> bool:
    """Edit a callback query's message caption. Falls back to reply on failure."""
    try:
        await query.edit_message_caption(caption=caption, reply_markup=reply_markup, parse_mode=parse_mode)
        return True
    except BadRequest as e:
        msg = str(e).lower()
        if "message is not modified" in msg:
            return True
        logger.warning(f"safe_edit_caption BadRequest: {e}")
        return await _fallback_reply(query, caption, reply_markup, parse_mode)
    except (TimedOut, NetworkError) as e:
        logger.warning(f"safe_edit_caption network error: {e}")
        return False


async def safe_send_text(
    target: Message | tuple[int, Any],
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    parse_mode: str = 'HTML',
) -> bool:
    """Send a text message. target can be Message or (chat_id, bot) tuple."""
    try:
        if hasattr(target, 'reply_text'):
            await target.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)  # type: ignore[union-attr]
        else:
            chat_id, bot = target
            await bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode=parse_mode)
        return True
    except Forbidden:
        logger.warning("Bot was blocked by user")
        return False
    except (TimedOut, NetworkError) as e:
        logger.warning(f"safe_send_text network error: {e}")
        return False
    except BadRequest as e:
        logger.warning(f"safe_send_text BadRequest: {e}")
        return False


async def safe_send_photo(
    target: Message | tuple[int, Any],
    photo: str,
    caption: str | None = None,
    reply_markup: InlineKeyboardMarkup | None = None,
    parse_mode: str = 'HTML',
) -> bool:
    """Send a photo message."""
    try:
        if hasattr(target, 'reply_photo'):
            await target.reply_photo(photo=photo, caption=caption, reply_markup=reply_markup, parse_mode=parse_mode)  # type: ignore[union-attr]
        else:
            chat_id, bot = target
            await bot.send_photo(chat_id=chat_id, photo=photo, caption=caption, reply_markup=reply_markup, parse_mode=parse_mode)
        return True
    except Forbidden:
        logger.warning("Bot was blocked by user")
        return False
    except (TimedOut, NetworkError) as e:
        logger.warning(f"safe_send_photo network error: {e}")
        return False
    except BadRequest as e:
        logger.warning(f"safe_send_photo BadRequest: {e}")
        return False


async def safe_delete(message: Message) -> bool:
    """Delete a message. Returns True if deleted, False if already gone."""
    try:
        await message.delete()
        return True
    except BadRequest:
        return False
    except (TimedOut, NetworkError):
        return False


async def _fallback_reply(
    query: CallbackQuery,
    text: str,
    reply_markup: InlineKeyboardMarkup | None,
    parse_mode: str = 'HTML',
) -> bool:
    """When edit fails, try sending a new message instead."""
    try:
        await query.message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
        return True
    except Exception as e:
        logger.warning(f"_fallback_reply also failed: {e}")
        return False
