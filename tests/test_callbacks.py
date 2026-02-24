"""Tests for utils/callbacks.py — callback data building and parsing."""

import re
import pytest
import utils.callbacks as cb


# ── make() ───────────────────────────────────────────────────

class TestMake:
    def test_no_args(self):
        assert cb.make("main_menu") == "main_menu"

    def test_single_int(self):
        assert cb.make("deck_open", 42) == "deck_open_42"

    def test_multiple_args(self):
        assert cb.make("deck_page", 5, 2) == "deck_page_5_2"

    def test_string_arg(self):
        assert cb.make("set_type", "basic") == "set_type_basic"


# ── parse_args() ─────────────────────────────────────────────

class TestParseArgs:
    def test_single_arg(self):
        assert cb.parse_args("deck_open_123", "deck_open") == ["123"]

    def test_multiple_args(self):
        assert cb.parse_args("deck_page_5_2", "deck_page") == ["5", "2"]

    def test_string_arg(self):
        assert cb.parse_args("set_type_basic", "set_type") == ["basic"]


# ── parse_int() ──────────────────────────────────────────────

class TestParseInt:
    def test_default_index(self):
        assert cb.parse_int("deck_open_42", "deck_open") == 42

    def test_explicit_index(self):
        assert cb.parse_int("deck_page_5_2", "deck_page", 1) == 2

    def test_first_of_multiple(self):
        assert cb.parse_int("deck_page_5_2", "deck_page", 0) == 5

    def test_non_int_raises(self):
        with pytest.raises(ValueError):
            cb.parse_int("set_type_basic", "set_type")


# ── pattern() ────────────────────────────────────────────────

class TestPattern:
    def test_no_args(self):
        assert cb.pattern("main_menu") == "^main_menu$"

    def test_single_arg(self):
        p = cb.pattern("deck_open", r'\d+')
        assert p == r'^deck_open_\d+$'
        assert re.match(p, "deck_open_42")
        assert not re.match(p, "deck_open_")
        assert not re.match(p, "deck_open_abc")

    def test_multi_arg(self):
        p = cb.pattern("deck_page", r'\d+', r'\d+')
        assert re.match(p, "deck_page_5_2")
        assert not re.match(p, "deck_page_5")


# ── Roundtrip: make → parse ──────────────────────────────────

class TestRoundtrip:
    @pytest.mark.parametrize("prefix,args,expected", [
        (cb.DECK_OPEN, (7,), 7),
        (cb.RATE, (3,), 3),
        (cb.CARD_DELETE_YES, (99,), 99),
        (cb.REVIEW_DECK, (1,), 1),
    ])
    def test_make_then_parse_int(self, prefix, args, expected):
        data = cb.make(prefix, *args)
        assert cb.parse_int(data, prefix) == expected

    def test_make_then_parse_two_ints(self):
        data = cb.make(cb.DECK_PAGE, 10, 3)
        assert cb.parse_int(data, cb.DECK_PAGE, 0) == 10
        assert cb.parse_int(data, cb.DECK_PAGE, 1) == 3

    def test_make_then_pattern_matches(self):
        data = cb.make(cb.DECK_OPEN, 42)
        p = cb.pattern(cb.DECK_OPEN, r'\d+')
        assert re.fullmatch(p.strip('^$'), data)


# ── All parametric prefixes have consistent make/parse ────────

class TestAllPrefixes:
    """Verify every parametric prefix produces a valid make/parse round-trip."""

    _INT_PREFIXES = [
        cb.DECK, cb.DECK_OPEN, cb.DECK_DELETE, cb.DECK_DELETE_YES,
        cb.DECK_RENAME, cb.DECKS_PAGE, cb.PICK_EDIT, cb.PICK_DELETE,
        cb.CARD_EDIT, cb.CARD_DELETE_YES, cb.RATE, cb.REVIEW_DECK,
        cb.EDIT_REVIEW,
    ]

    @pytest.mark.parametrize("prefix", _INT_PREFIXES)
    def test_int_roundtrip(self, prefix):
        data = cb.make(prefix, 123)
        assert cb.parse_int(data, prefix) == 123

    def test_deck_page_two_args(self):
        data = cb.make(cb.DECK_PAGE, 7, 3)
        assert cb.parse_int(data, cb.DECK_PAGE, 0) == 7
        assert cb.parse_int(data, cb.DECK_PAGE, 1) == 3

    def test_set_type_string(self):
        for t in ("basic", "reverse"):
            data = cb.make(cb.SET_TYPE, t)
            assert cb.parse_args(data, cb.SET_TYPE) == [t]
