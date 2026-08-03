from tidy.tui.themes import ACCENTS, accent_for, cycle_theme


def test_all_themes_have_accent():
    for theme in ("neon", "crt", "gameboy", "watermelon", "paper"):
        assert theme in ACCENTS
        assert accent_for(theme).startswith("#")


def test_unknown_theme_falls_back():
    assert accent_for("does-not-exist") == ACCENTS["neon"]


def test_cycle_theme_wraps():
    assert cycle_theme("neon") == "crt"
    assert cycle_theme("paper") == "neon"  # wraps around
    assert cycle_theme("bogus") == "neon"  # resets to start
