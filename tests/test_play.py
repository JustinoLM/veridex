"""Tests for play.py's input parsing and re-prompt loop (no terminal needed)."""

import play


def test_knight_or_knave_parsing_is_case_and_space_insensitive():
    assert play.parse_knight_or_knave(" Knight ") is True
    assert play.parse_knight_or_knave("K") is True
    assert play.parse_knight_or_knave("KNAVE") is False
    assert play.parse_knight_or_knave("n") is False
    assert play.parse_knight_or_knave("maybe") is None
    assert play.parse_knight_or_knave("") is None


def test_guilty_or_innocent_parsing():
    assert play.parse_guilty_or_innocent("guilty") is True
    assert play.parse_guilty_or_innocent("G") is True
    assert play.parse_guilty_or_innocent("Innocent") is False
    assert play.parse_guilty_or_innocent("i") is False
    assert play.parse_guilty_or_innocent("x") is None


def test_ask_until_valid_reprompts_on_bad_input(monkeypatch):
    answers = iter(["???", "", "knave"])
    monkeypatch.setattr(play.Prompt, "ask", lambda *a, **k: next(answers))
    assert play.ask_until_valid("q?", play.parse_knight_or_knave) is False


def test_menu_reprompts_then_returns_the_chosen_puzzle(monkeypatch):
    answers = iter(["nope", "2"])
    monkeypatch.setattr(play.Prompt, "ask", lambda *a, **k: next(answers))
    puzzle, _ = play.show_menu_and_get_choice()
    assert puzzle is play.PUZZLE_2


def test_menu_quit(monkeypatch):
    monkeypatch.setattr(play.Prompt, "ask", lambda *a, **k: "Q")
    assert play.show_menu_and_get_choice() is None


def test_main_exits_cleanly_on_ctrl_d(monkeypatch):
    def raise_eof(*a, **k):
        raise EOFError

    monkeypatch.setattr(play.Prompt, "ask", raise_eof)
    play.main()  # must not raise
