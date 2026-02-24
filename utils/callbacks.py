"""Centralized callback data building and parsing.

Every parametric callback string has a known prefix defined here.
Use make() to build callback_data, parse_int()/parse_args() to extract values,
and pattern() to generate regex patterns for handler routing.

Renaming a prefix constant now causes an ImportError instead of a silent runtime break.
"""

# ── Parametric prefixes (carry an ID or value after the prefix) ──

DECK = "deck"                       # deck_<deck_id>
DECK_OPEN = "deck_open"             # deck_open_<deck_id>
DECK_PAGE = "deck_page"             # deck_page_<deck_id>_<page>
DECK_DELETE = "deck_delete"         # deck_delete_<deck_id>
DECK_DELETE_YES = "deck_delete_yes" # deck_delete_yes_<deck_id>
DECK_RENAME = "deck_rename"         # deck_rename_<deck_id>
DECKS_PAGE = "decks_page"           # decks_page_<page>
PICK_EDIT = "pick_edit"             # pick_edit_<deck_id>
PICK_DELETE = "pick_delete"         # pick_delete_<deck_id>
CARD_EDIT = "card_edit"             # card_edit_<card_id>
CARD_DELETE_YES = "card_delete_yes" # card_delete_yes_<card_id>
RATE = "rate"                       # rate_<rating>
REVIEW_DECK = "review_deck"         # review_deck_<deck_id>
EDIT_REVIEW = "edit_review"         # edit_review_<card_id>
SET_TYPE = "set_type"               # set_type_<basic|reverse>


def make(prefix: str, *args: object) -> str:
    """Build a callback data string.

    >>> make("deck_open", 123)
    'deck_open_123'
    >>> make("deck_page", 5, 2)
    'deck_page_5_2'
    """
    if args:
        return prefix + '_' + '_'.join(str(a) for a in args)
    return prefix


def parse_args(data: str, prefix: str) -> list[str]:
    """Extract args after a known prefix.

    >>> parse_args("deck_open_123", "deck_open")
    ['123']
    >>> parse_args("deck_page_5_2", "deck_page")
    ['5', '2']
    """
    suffix = data[len(prefix) + 1:]
    return suffix.split('_') if suffix else []


def parse_int(data: str, prefix: str, index: int = 0) -> int:
    """Extract a single integer arg.

    >>> parse_int("deck_open_123", "deck_open")
    123
    >>> parse_int("deck_page_5_2", "deck_page", 1)
    2
    """
    return int(parse_args(data, prefix)[index])


def pattern(prefix: str, *arg_patterns: str) -> str:
    r"""Build a regex pattern for CallbackQueryHandler.

    >>> pattern("deck_open", r'\d+')
    '^deck_open_\\d+$'
    >>> pattern("deck_page", r'\d+', r'\d+')
    '^deck_page_\\d+_\\d+$'
    """
    if arg_patterns:
        return f'^{prefix}_{"_".join(arg_patterns)}$'
    return f'^{prefix}$'
