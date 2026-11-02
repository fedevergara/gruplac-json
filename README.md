# gruplac-json

Build a JSON from a research group's public GrupLAC page (Minciencias, Colombia)

## Install

```bash
pip install gruplac-json
gruplac-json --version
```

## Development

```bash
python -m pip install -e ".[dev]"
python -m pytest
ruff check . && ruff format --check .
```

Releases are published to PyPI from GitHub Actions when a `v*` tag is pushed; see [PUBLISHING.md](PUBLISHING.md) and [CHANGELOG.md](CHANGELOG.md).
