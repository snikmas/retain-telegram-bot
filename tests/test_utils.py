"""
Tests for utils/utils.py — parse_text and parse_photo (pure Python, no Telegram objects).
"""
from unittest.mock import MagicMock
from utils.utils import parse_text, parse_photo


class TestParseText:
    # ── Pipe separator ────────────────────────────────────────

    def test_pipe_basic(self):
        r = parse_text("Tokyo | Capital of Japan")
        assert r['front'] == 'Tokyo'
        assert r['back'] == 'Capital of Japan'

    def test_pipe_strips_whitespace(self):
        r = parse_text("  Tokyo  |  Capital  ")
        assert r['front'] == 'Tokyo'
        assert r['back'] == 'Capital'

    def test_pipe_splits_on_first_only(self):
        r = parse_text("a | b | c")
        assert r['front'] == 'a'
        assert r['back'] == 'b | c'

    def test_pipe_empty_back(self):
        r = parse_text("front |")
        assert r['front'] == 'front'
        assert r['back'] == ''

    def test_pipe_empty_front(self):
        r = parse_text("| back")
        assert r['front'] == ''
        assert r['back'] == 'back'

    # ── Newline separator ─────────────────────────────────────

    def test_newline_two_lines(self):
        r = parse_text("Tokyo\nCapital of Japan")
        assert r['front'] == 'Tokyo'
        assert r['back'] == 'Capital of Japan'

    def test_newline_multiple_back_lines_joined(self):
        r = parse_text("Tokyo\nLine 2\nLine 3")
        assert r['front'] == 'Tokyo'
        assert r['back'] == 'Line 2\nLine 3'

    def test_newline_ignores_blank_lines(self):
        r = parse_text("\n\nTokyo\n\nCapital\n\n")
        assert r['front'] == 'Tokyo'
        assert r['back'] == 'Capital'

    # ── Single line (no back) ─────────────────────────────────

    def test_single_line_gives_empty_back(self):
        r = parse_text("Just a front")
        assert r['front'] == 'Just a front'
        assert r['back'] == ''

    def test_single_line_strips_outer_whitespace(self):
        r = parse_text("  Tokyo  ")
        assert r['front'] == 'Tokyo'
        assert r['back'] == ''

    def test_empty_string(self):
        r = parse_text("")
        assert r['front'] == ''
        assert r['back'] == ''

    # ── Priority: pipe beats newline ──────────────────────────

    def test_pipe_takes_priority_over_newline(self):
        # has both | and \n — pipe wins
        r = parse_text("a | b\nc")
        assert r['front'] == 'a'
        assert r['back'] == 'b\nc'

    # ── Return keys ───────────────────────────────────────────

    def test_always_returns_front_and_back_keys(self):
        for text in ["a | b", "a\nb", "single"]:
            r = parse_text(text)
            assert 'front' in r
            assert 'back' in r


class TestParsePhoto:
    def _photo(self, file_id='fid_abc'):
        photo = MagicMock()
        photo.file_id = file_id
        return photo

    def test_front_is_file_id(self):
        r = parse_photo(self._photo('xyz123'))
        assert r['front'] == 'xyz123'

    def test_back_is_caption(self):
        r = parse_photo(self._photo(), caption='a dog')
        assert r['back'] == 'a dog'

    def test_caption_stripped(self):
        r = parse_photo(self._photo(), caption='  trimmed  ')
        assert r['back'] == 'trimmed'

    def test_no_caption_gives_empty_back(self):
        r = parse_photo(self._photo())
        assert r['back'] == ''

    def test_none_caption_gives_empty_back(self):
        r = parse_photo(self._photo(), caption=None)
        assert r['back'] == ''

    def test_is_photo_flag_true(self):
        assert parse_photo(self._photo())['is_photo'] is True

    def test_returns_all_keys(self):
        r = parse_photo(self._photo(), caption='c')
        assert 'front' in r and 'back' in r and 'is_photo' in r
