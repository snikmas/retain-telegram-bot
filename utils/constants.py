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
    PREVIEW = auto()
    AWAITING_TYPE = auto()
    AWAITING_DECK = auto()
    CREATING_DECK = auto()
    # PARSE_CONTENT = auto() no need

CARD_TYPE_BUTTONS = [
    [InlineKeyboardButton('Basic', callback_data='type_basic')],
    [InlineKeyboardButton('Reverse', callback_data='type_reverse')],
    [InlineKeyboardButton('Cloze', callback_data='type_cloze')]
]
