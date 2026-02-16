# ==================== TELEGRAM IMPORTS ====================
from telegram import InlineKeyboardButton

# ==================== SYSTEM IMPORTS ====================

# ===================== UTILS IMPORT =====================
import logging
from enum import auto, IntEnum

# ==================== FOLDERS IMPORT ====================

# ==================== ============== ====================


class AddCardState(IntEnum):
    AWAITING_CONTENT = auto()
    AWAITING_TYPE = auto()
    AWAITING_DECK = auto()
    CREATING_DECK = auto()
    CONFIRMATION_PREVIEW = auto()
    EDITING = auto()
    # PARSE_CONTENT = auto() no need

CARD_TYPE_BUTTONS = [
    [InlineKeyboardButton('Basic', callback_data='type_basic')],
    [InlineKeyboardButton('Reverse', callback_data='type_reverse')],
    [InlineKeyboardButton('Cloze', callback_data='type_cloze')]
]

PREVIEW_BUTTONS = [
    [InlineKeyboardButton("✅ Save Card", callback_data='save_card')],
    [InlineKeyboardButton("✏️ Edit Content", callback_data='edit_card')],
    [InlineKeyboardButton("⚙️ Change Settings", callback_data='change_settings')],
    [InlineKeyboardButton("❌ Cancel", callback_data='cancel')]
]