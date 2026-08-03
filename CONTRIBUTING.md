# Contributing

Thanks for helping with Tidy! It's a small, personal-feeling project — a few
rules keep it shippable.

## Setup

```bash
git clone https://github.com/Twarga/Tidy
cd Tidy
python3 -m venv --system-site-packages .venv   # system packages: GUI needs PyGObject/webkit
source .venv/bin/activate
pip install -e ".[dev,gui,tui,mcp,scheduler]"
```

`./dev.sh` does all of this for you.

## Code style

- **Ruff enforced**: `ruff check .` and `ruff format .` must both pass.
- Keep the **core engine** (`src/tidy/`) free of GUI/MCP imports — it powers
  the CLI, TUI, daemon, GUI and MCP alike.
- Lazy-import heavy deps (webview, pystray, fastmcp, textual) inside functions,
  so headless use never pays for them.

## Testing

```bash
pytest            # 105 tests: unit + integration (real git pairs)
pytest -q -m ""   # anything new must come with tests
```

- Integration tests build a local **bare origin** (`tests/conftest.py` fixture)
  so sync is exercised against real git without the network.
- New features → new test file or extend the matching `tests/test_*.py`.

## Committing

Commits are authored as `Twarga <twarga.touzani.05@gmail.com>`:

```bash
git -c user.name="Twarga" -c user.email="twarga.touzani.05@gmail.com" commit
```

## Releasing

Bump `__version__` in `src/tidy/__init__.py`, update `CHANGELOG.md`, then:

```bash
./packaging/build-appimage.sh          # → tidy-<ver>-x86_64.AppImage
gh release create v<ver> tidy-<ver>-x86_64.AppImage install.sh --notes ...
```
