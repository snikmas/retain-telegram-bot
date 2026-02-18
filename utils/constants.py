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
    [InlineKeyboardButton("\u2714 Save", callback_data='save_card'),
     InlineKeyboardButton("\u270f Edit", callback_data='edit_card')],
    [InlineKeyboardButton("\U0001f4c1 Change Deck", callback_data='change_settings')],
    [InlineKeyboardButton("\u2190 Back", callback_data='back'),
     InlineKeyboardButton("Cancel", callback_data='cancel')],
]

MAIN_MENU_BUTTONS = [
    [InlineKeyboardButton('\U0001f4dd New Card', callback_data='add_card'),
     InlineKeyboardButton('\U0001f9e0 Review', callback_data='review')],
    [InlineKeyboardButton('\U0001f4da My Decks', callback_data='my_decks'),
     InlineKeyboardButton('\U0001f4ca Stats', callback_data='stats')],
    [InlineKeyboardButton('\u2753 How it works', callback_data='help')],
]
