from conftest import section
from gruplac_json import members, scienti
from gruplac_json.parser import build, tidy

PRODUCTS = [
    {
        "COD_RH": "0000000001",
        "COD_PRODUCTO": 10,
        "TXT_NME_PROD": "A synthetic benchmark for testing GrupLAC parsers",
        "NRO_ANO_PRESENTA": 2017,
        "TXT_DOI": "10.9999/synthetic.2017.003",
    },
    {
        "COD_RH": "0000000002",
        "COD_PRODUCTO": 7,
        "TXT_NME_PROD": "A synthetic benchmark for testing GrupLAC parsers",
        "NRO_ANO_PRESENTA": 2017,
        "TXT_DOI": "10.9999/synthetic.2017.003",
    },
    {"COD_RH": "0000000003", "COD_PRODUCTO": 4, "TXT_NME_PROD": "Asesoría sintética a una empresa", "NRO_ANO_PRESENTA": 2021},
    {"COD_RH": "0000000003", "COD_PRODUCTO": 5, "TXT_NME_PROD": "Not on the page at all", "NRO_ANO_PRESENTA": 2020},
]
PROJECTS = [
    {"COD_RH": "0000000001", "COD_PROYECTO": 1, "TXT_NME_PROYECTO": "Plataforma sintética para pruebas", "NRO_ANO_INICIO": 2018}
]


def fake_get(path, key, **params):
    assert params.get("group_id") in (None, "COL0008423")
    return {
        "/scienti/info": [{"institution": "udea", "model_year": "2024"}],
        "/scienti/product": PRODUCTS,
        "/scienti/project": PROJECTS,
        "/scienti/event": [],
        "/scienti/network": [],
    }[path]


def test_group_records(page, monkeypatch):
    monkeypatch.setattr(scienti, "get", fake_get)
    data = build(page, "00000000001676", "COL0008423")
    members.enrich(data)
    assert scienti.enrich(data, "COL0008423", key="test", log=lambda *a: None)
    members.enrich(data)
    tidy(data)
    w = data["works"][0]
    s = w["gruplac"]["scienti"]
    assert (s["id"], s["by"], s["also"]) == ("0000000001-10", "doi", ["0000000002-7"])  # one record per member
    assert [x["id"] for x in w["external_ids"] if x["source"] == "scienti"] == ["0000000001-10", "0000000002-7"]
    assert data["projects"][0]["scienti"]["id"] == "0000000001-1"
    assert data["scienti"]["not_on_page"] == 1
    # the consultancy lists no authors on the page: its author comes from the matching Scienti record
    cons = section(data, "Consultorías científico-tecnológicas")[0]
    assert cons["scienti"]["id"] == "0000000003-4"
    assert cons["authors_inferred"] is True
    a = cons["authors"][0]
    assert (a["full_name"], a["id"]) == ("Luisa Fernanda Giraldo Soto", "0000000003")
    assert a["external_ids"][0]["provenance"] == "gruplac"  # her name is in the members table
    assert a["affiliations"][0]["gruplac"]["provenance"] == "gruplac members"


def test_no_key(page, monkeypatch):
    monkeypatch.delenv("COLAV_APIKEY", raising=False)
    monkeypatch.setattr(scienti, "apikey", lambda key=None: None)
    data = build(page, "00000000001676", "COL0008423")
    assert scienti.enrich(data, "COL0008423", log=lambda *a: None) is False
