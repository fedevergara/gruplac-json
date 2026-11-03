from cvlac_json import ror as ror_api

from gruplac_json.parser import extract

UDEA = {
    "id": "03bp5hc83",
    "name": "Universidad de Antioquia",
    "match": "name",
    "types": [{"source": "ror", "type": "education"}],
    "external_ids": [{"provenance": "ror", "source": "ror", "id": "https://ror.org/03bp5hc83"}],
    "addresses": [{"city": "Medellín", "country": "Colombia", "country_code": "CO"}],
}


def test_institutions_with_ror(page, monkeypatch):
    monkeypatch.setattr(ror_api, "lookup", lambda name, cache: UDEA if "ANTIOQUIA" in name.upper() else None)
    monkeypatch.setattr(ror_api, "_load_cache", dict)
    monkeypatch.setattr(ror_api, "_save_cache", lambda c: None)
    data = extract("COL0008423", html=page, scienti="off", ror=True, log=lambda *a: None)
    assert data["institutions"][0]["ror"] == {"id": "03bp5hc83", "name": "Universidad de Antioquia", "match": "name"}
    a = data["works"][0]["authors"][0]
    inst = next(x for x in a["affiliations"] if x["gruplac"]["provenance"] == "gruplac institutions")
    assert (inst["id"], inst["name"], inst["types"], inst["addresses"]) == (
        "03bp5hc83",
        "Universidad de Antioquia",
        UDEA["types"],
        UDEA["addresses"],
    )
    assert inst["gruplac"]["names"] == ["UNIVERSIDAD DE ANTIOQUIA"] and inst["gruplac"]["ror_match"] == "name"
    old = data["works"][1]["authors"][0]  # 2005, before the member's period: neither the group nor its institutions
    assert old["affiliations"] == []
    t = data["other_products"]["Trabajos dirigidos/turorías"][0]
    assert t["institution"]["id"] == "03bp5hc83"
