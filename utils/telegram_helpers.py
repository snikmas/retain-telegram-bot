"""
Safe wrappers for Telegram API calls.

Every handler uses these instead of raw query.edit_message_text / bot.send_message.
If the API call fails, these recover gracefully instead of crashing the handler.
"""

import logging

from telegram.error import BadRequest, Forbidden, TimedOut, NetworkError

logger = logging.getLogger(__name__)


async def safe_edit_text(query, text, reply_markup=None):
    """Edit a callback query's message text. Falls back to reply on failure."""
    try:
        await query.edit_message_text(text, reply_markup=reply_markup)
        return True
    except BadRequest as e:
        msg = str(e).lower()
        if "message is not modified" in msg:
            return True  # same content — harmless
        if "message to edit not found" in msg:
            # message was deleted — try sending a new one
            return await _fallback_reply(query, text, reply_markup)
        logger.warning(f"safe_edit_text BadRequest: {e}")
        return await _fallback_reply(query, text, reply_markup)
    except (TimedOut, NetworkError) as e:
        logger.warning(f"safe_edit_text network error: {e}")
        return False


async def safe_edit_caption(query, caption, reply_markup=None):
    """Edit a callback query's message caption. Falls back to reply on failure."""
    try:
        await query.edit_message_caption(caption=caption, reply_markup=reply_markup)
        return True
    except BadRequest as e:
        msg = str(e).lower()
        if "message is not modified" in msg:
            return True
        logger.warning(f"safe_edit_caption BadRequest: {e}")
        return await _fallback_reply(query, caption, reply_markup)
    except (TimedOut, NetworkError) as e:
        logger.warning(f"safe_edit_caption network error: {e}")
        return False


async def safe_send_text(target, text, reply_markup=None):
    """Send a text message. target can be Message, chat_id+bot tuple, etc."""
    try:
        if hasattr(target, 'reply_text'):
            await target.reply_text(text, reply_markup=reply_markup)
        else:
            # target is (chat_id, bot)
            chat_id, bot = target
            await bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)
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


async def safe_send_photo(target, photo, caption=None, reply_markup=None):
    """Send a photo message."""
    try:
        if hasattr(target, 'reply_photo'):
            await target.reply_photo(photo=photo, caption=caption, reply_markup=reply_markup)
        else:
            chat_id, bot = target
            await bot.send_photo(chat_id=chat_id, photo=photo, caption=caption, reply_markup=reply_markup)
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


async def safe_delete(message):
    """Delete a message. Returns True if deleted, False if already gone."""
    try:
        await message.delete()
        return True
    except BadRequest:
        return False
    except (TimedOut, NetworkError):
        return False


async def _fallback_reply(query, text, reply_markup):
    """When edit fails, try sending a new message instead."""
    try:
        await query.message.reply_text(text, reply_markup=reply_markup)
        return True
    except Exception as e:
        logger.warning(f"_fallback_reply also failed: {e}")
        return False
