# Contributing

MouseRuler welcomes bug reports, usability improvements, and measurement research.

Use Python 3.13 on Windows 11. Create a virtual environment and install
`requirements-dev.txt`, then run:

```powershell
python -m ruff check .
python -m ruff format --check .
python -m pytest -q
```

The `desktop` test temporarily hides/confines the pointer, restores it in a
`finally` block, and requires interactive desktop access. For a headless runner,
use `python -m pytest -q -m "not desktop"`.

Keep acquisition separate from rendering. Never use cursor coordinates, display
DPI, or polling rate as physical displacement or hardware DPI. Preserve raw
counts and label estimates honestly. New heading sources must fail explicitly
when data is stale. Cursor acquisition must always have a matching release path.

Describe the problem and resulting behaviour in pull requests. Include the
relevant tests and screenshots for interface changes. Avoid unrelated rewrites.
Comments should explain hardware assumptions, API constraints, or non-obvious
decisions; names and structure should explain routine operations.

For physical accuracy reports include the mouse, hardware DPI, reference ruler,
surface, speed, heading constraints, repeated results, and whether data is
physical or synthetic. Do not post device identifiers or private diagnostic files
without reviewing them first. Decimal places do not establish measurement accuracy.
