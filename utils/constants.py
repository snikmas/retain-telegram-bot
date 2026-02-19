from enum import auto, IntEnum
from telegram import InlineKeyboardButton

DECK_NAME_MAX = 50


class AddCardState(IntEnum):
    AWAITING_CONTENT = auto()
    AWAITING_DECK = auto()
    CREATING_DECK = auto()
    CONFIRMATION_PREVIEW = auto()


class ReviewState(IntEnum):
    SHOWING_FRONT = auto()
    RATING = auto()
    DECK_PICKER = auto()
    EDITING_CARD = auto()
    EDITING_CARD_PREVIEW = auto()


class ManageState(IntEnum):
    EDIT_CARD_CONTENT = auto()
    EDIT_CARD_PREVIEW = auto()
    RENAME_DECK = auto()
    PICK_CARD_TO_EDIT = auto()
    PICK_CARD_TO_DELETE = auto()


PREVIEW_BUTTONS = [
    [InlineKeyboardButton("\u2705 Save", callback_data='save_card')],
    [
        InlineKeyboardButton("\u270f\ufe0f Edit", callback_data='edit_card'),
        InlineKeyboardButton("\U0001f4c1 Deck", callback_data='change_settings'),
        InlineKeyboardButton("\U0001f501 Type", callback_data='change_type'),
    ],
    [InlineKeyboardButton("\u2716 Cancel", callback_data='cancel')],
]
