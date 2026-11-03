import hashlib
import json
import pathlib

import pytest

from conftest import section
from gruplac_json import product_hash
from gruplac_json.product_hash import hash_key

VECTORS = json.loads((pathlib.Path(__file__).parent / "product_hash_vectors.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("v", VECTORS, ids=[v["key"][:40] for v in VECTORS])
def test_vectors(v):
    """The same vectors are in cvlac-json: both packages must give these keys and hashes."""
    assert hash_key(v["title"], v["cod_rh"], v["kind"], v["year"], v.get("n", 1)) == v["key"]
    assert product_hash(v["title"], v["cod_rh"], v["kind"], v["year"], v.get("n", 1)) == v["hash"]
    assert v["hash"] == hashlib.sha1(v["key"].encode("ascii")).hexdigest()


def test_each_member_gets_its_own_hash(data):
    w = data["works"][0]  # signed by two members and one external author
    ana, carlos, other = w["authors"]
    assert ana["product_hash"] == product_hash(w["title"], "0000000001", "work", 2017)
    assert carlos["product_hash"] == product_hash(w["title"], "0000000002", "work", 2017)
    assert other["product_hash"] is None  # not a member: no COD_RH


def test_other_products_and_theses(data):
    soft = section(data, "Softwares")[0]
    assert soft["authors"][0]["product_hash"] == product_hash("Analizador sintético", "0000000001", "other", 2022)
    t = section(data, "Trabajos dirigidos/turorías")[0]
    student = t["authors"][1]  # the student is a member too
    assert student["product_hash"] == product_hash(t["title"], "0000000002", "other", 2017)
    assert data["counts"]["product_hash_repeated"] == 0


def test_unique_per_member(page):
    from gruplac_json.parser import extract

    page = page.replace("Old article before the group", "A synthetic benchmark for testing GrupLAC parsers").replace(
        "2005 vol:71", "2017 vol:71"
    )
    d = extract("COL0008423", html=page, scienti="off", ror=False, log=lambda *a: None)
    h = [w["authors"][0]["product_hash"] for w in d["works"][:2]]
    title = "A synthetic benchmark for testing GrupLAC parsers"
    assert h == [product_hash(title, "1", "work", 2017), product_hash(title, "1", "work", 2017, n=2)]
    assert d["counts"]["product_hash_repeated"] == 1


def test_untitled_items_are_hashed_with_their_text():
    """As in cvlac-json: an item with no letter or digit in the title is hashed with its text."""
    from gruplac_json.members import add_product_hashes

    def item(text):
        return {"title": "", "text": text, "year": 2020, "authors": [{"full_name": "ANA", "id": "0000000001"}]}

    texts = ["Revisión de la revista Uno, 2020", "Revisión de la revista Dos, 2020", "Revisión de la revista Uno, 2020"]
    its = [item(t) for t in texts]
    data = {"works": [], "other_products": {"Demás trabajos": its}, "counts": {}}
    add_product_hashes(data)
    h = [it["authors"][0]["product_hash"] for it in its]
    assert h[0] == product_hash(its[0]["text"], "1", "other", 2020) and h[1] == product_hash(its[1]["text"], "1", "other", 2020)
    assert h[2] == product_hash(its[0]["text"], "1", "other", 2020, n=2)
    assert data["counts"] == {"product_hash_repeated": 1, "product_hash_from_text": 3}
