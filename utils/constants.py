from enum import auto, IntEnum
from telegram import InlineKeyboardButton


class AddCardState(IntEnum):
    AWAITING_CONTENT = auto()
    AWAITING_TYPE = auto()
    AWAITING_DECK = auto()
    CREATING_DECK = auto()
    CONFIRMATION_PREVIEW = auto()


class ReviewState(IntEnum):
    SHOWING_FRONT = auto()
    RATING = auto()


CARD_TYPE_BUTTONS = [
    [InlineKeyboardButton('Basic', callback_data='type_basic')],
    [InlineKeyboardButton('Reverse', callback_data='type_reverse')],
    [InlineKeyboardButton('Cloze', callback_data='type_cloze')]
]

PREVIEW_BUTTONS = [
    [InlineKeyboardButton("Save", callback_data='save_card'),
     InlineKeyboardButton("Edit", callback_data='edit_card')],
    [InlineKeyboardButton("Change Deck", callback_data='change_settings')],
    [InlineKeyboardButton("< Back", callback_data='back'),
     InlineKeyboardButton("Cancel", callback_data='cancel')],
]

MAIN_MENU_BUTTONS = [
    [InlineKeyboardButton('+ New Card', callback_data='add_card'),
     InlineKeyboardButton('Review', callback_data='review')],
    [InlineKeyboardButton('My Decks', callback_data='my_decks'),
     InlineKeyboardButton('Stats', callback_data='stats')],
]
