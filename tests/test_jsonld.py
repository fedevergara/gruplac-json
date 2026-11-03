import json
import re

import pytest
from cvlac_json.jsonld import pointer

from conftest import FIXTURE
from gruplac_json import to_jsonld
from gruplac_json.cli import main
from gruplac_json.jsonld import GRUPLAC_URL, VOCAB, context

COL = "COL0008423"
BASE = "https://example.org/dam/scraped/gruplac/"


def strip_ld(v):
    """The document without the JSON-LD keys: it must be the input again."""
    if isinstance(v, dict):
        return {k: strip_ld(x) for k, x in v.items() if not k.startswith("@")}
    if isinstance(v, list):
        return [strip_ld(x) for x in v]
    return v


def test_same_document_plus_ld_keys(data):
    before = json.dumps(data, sort_keys=True)
    doc = to_jsonld(data)
    assert json.dumps(data, sort_keys=True) == before  # input not modified
    assert strip_ld(doc) == data
    assert doc["@id"] == data["url"] and "GruplacProfile" in doc["@type"]


def test_base_and_fallback_iri(data):
    assert to_jsonld(data, base=BASE)["@id"] == BASE + COL
    assert to_jsonld({k: v for k, v in data.items() if k != "url"})["@id"] == GRUPLAC_URL + data["nro"]
    assert to_jsonld({**data, "col": None}, base=BASE)["@id"] == BASE + data["nro"]


def test_items_are_json_pointers(data):
    doc = to_jsonld(data, base=BASE)
    assert doc["works"][0]["@id"] == f"{BASE}{COL}#/works/0"
    assert doc["members"][1]["@id"] == f"{BASE}{COL}#/members/1"
    assert doc["members"][1]["@type"] == "schema:OrganizationRole"
    assert doc["institutions"][0]["@type"] == "schema:Organization"
    title, items = next(iter(doc["other_products"].items()))
    assert items[0]["@id"] == BASE + COL + pointer("other_products", title, 0)


def test_page_labels_get_terms(data):
    ctx = to_jsonld(data)["@context"]
    assert ctx["@vocab"] == VOCAB
    assert ctx["Plan de trabajo"] == VOCAB + "Plan%20de%20trabajo"  # strategic_plan
    assert ctx["Líder"] == VOCAB + "L%C3%ADder"  # profile.raw
    assert ctx["authors"]["@container"] == "@list"  # cvlac-json's terms
    assert context()["section_categories"] == {"@type": "@json"}


def test_rdf(data):
    jsonld = pytest.importorskip("pyld.jsonld")
    nq = jsonld.to_rdf(to_jsonld(data, base=BASE), {"format": "application/n-quads"})
    iris = re.findall(r"^<([^>]*)> <([^>]*)>", nq, re.M)
    assert iris and not [i for pair in iris for i in pair if re.search(r'[\s<>"{}|\\^`]', i)]
    assert f"<{BASE}{COL}#/works/0> <https://schema.org/author>" in nq  # ordered list of authors
    assert f"<{VOCAB}section>" in nq  # section title kept in RDF
    assert "http://www.w3.org/1999/02/22-rdf-syntax-ns#JSON" in nq  # counts, section_categories


def test_cli_jsonld(tmp_path):
    out = tmp_path / "g.jsonld"
    rc = main(
        [COL, "--html", str(FIXTURE), "--scienti", "off", "--ror", "off", "--format", "jsonld", "--base", BASE, "-o", str(out)]
    )
    assert rc == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["@id"] == BASE + COL and "@context" in doc
