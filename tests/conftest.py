import pathlib

import pytest

from gruplac_json.parser import decode, extract

FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "gruplac_sintetico.html"


@pytest.fixture
def page():
    return decode(FIXTURE.read_bytes())


@pytest.fixture
def data(page):
    """The synthetic group, without network calls (no Scienti, no ROR)."""
    return extract("COL0008423", html=page, scienti="off", ror=False, log=lambda *a: None)


def section(data, title):
    return data["other_products"][title]
