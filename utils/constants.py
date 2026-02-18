from enum import auto, IntEnum
from telegram import InlineKeyboardButton


class AddCardState(IntEnum):
    AWAITING_CONTENT = auto()
    AWAITING_DECK = auto()
    CREATING_DECK = auto()
    CONFIRMATION_PREVIEW = auto()


class ReviewState(IntEnum):
    SHOWING_FRONT = auto()
    RATING = auto()
    DECK_PICKER = auto()


class ManageState(IntEnum):
    EDIT_CARD_CONTENT = auto()
    EDIT_CARD_PREVIEW = auto()
    RENAME_DECK = auto()


PREVIEW_BUTTONS = [
    [
        InlineKeyboardButton("\u270f\ufe0f Edit", callback_data='edit_card'),
        InlineKeyboardButton("\U0001f4c1 Deck", callback_data='change_settings'),
        InlineKeyboardButton("\U0001f501 Type", callback_data='change_type'),
    ],
    [
        InlineKeyboardButton("\u2714 Save", callback_data='save_card'),
        InlineKeyboardButton("\u2716 Cancel", callback_data='cancel'),
    ],
]
