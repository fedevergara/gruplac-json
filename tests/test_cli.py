import json

import pytest

from conftest import FIXTURE
from gruplac_json import __version__
from gruplac_json.cli import main


def test_version(capsys):
    with pytest.raises(SystemExit) as e:
        main(["--version"])
    assert e.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_saved_page(tmp_path):
    out = tmp_path / "g.json"
    assert main(["COL0008423", "--html", str(FIXTURE), "--scienti", "off", "--ror", "off", "-o", str(out)]) == 0
    d = json.loads(out.read_text(encoding="utf-8"))
    assert d["col"] == "COL0008423" and len(d["works"]) == 5


def test_bad_group(capsys):
    with pytest.raises(SystemExit):
        main(["COL9999999", "--html", str(FIXTURE)])
    assert "not in the table" in capsys.readouterr().err
