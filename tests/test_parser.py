import pytest

from conftest import section
from gruplac_json.parser import ASC, fields, iso_date, period, resolve


def test_group_profile(data):
    assert data["name"] == "Grupo Sintético de Pruebas"
    assert (data["nro"], data["col"]) == ("00000000001676", "COL0008423")
    p = data["profile"]
    assert p["formed"] == {"year": 1999, "month": 3}
    assert (p["department"], p["city"], p["leader"]) == ("ANTIOQUIA", "MEDELLÍN", "Ana María Pérez Gómez")
    assert p["certified"] == {"value": "Si", "date": "2016-01-21"}
    assert p["classification"]["category"] == "A1"
    assert p["knowledge_area"] == ["Ciencias Naturales", "Ciencias Físicas", "Física de Partículas y Campos"]
    assert data["institutions"] == [{"name": "UNIVERSIDAD DE ANTIOQUIA", "status": "Avalado"}]  # no `ror` without ROR
    assert data["strategic_plan"] == {"Plan de trabajo": "Probar el parser", "Objetivos": "Cubrir todas las secciones"}
    assert [x["name"] for x in data["research_lines"]] == ["Física de prueba", "Analítica de datos"]


def test_members(data):
    m = {x["cod_rh"]: x for x in data["members"]}
    assert len(m) == 3
    ana, carlos = m["0000000001"], m["0000000002"]
    assert (ana["linkage"], ana["hours"], ana["start"], ana["end"], ana["open_end"]) == (
        "Integrante",
        20,
        {"year": 2010, "month": 1},
        None,
        True,
    )
    assert (carlos["end"], carlos["open_end"]) == ({"year": 2018, "month": 7}, False)
    assert ana["url"].endswith("cod_rh=0000000001")


def test_article_is_an_impactu_work(data):
    w = data["works"][0]
    assert w["id"] == "gruplac:00000000001676:1"
    assert w["title"] == "A synthetic benchmark for testing GrupLAC parsers"
    assert [t["type"] for t in w["types"]] == ["Producción bibliográfica", "Artículo", "Publicado en revista especializada"]
    assert w["doi"] == "https://doi.org/10.9999/synthetic.2017.003"
    assert w["year_published"] == 2017
    assert w["source"]["name"] == "REVISTA DE PRUEBAS SINTETICAS"
    assert w["source"]["external_ids"] == [{"source": "issn", "id": "1234-5679"}]
    assert w["bibliographic_info"] == {"volume": "12", "issue": "3", "start_page": "101", "end_page": "115"}
    assert w["gruplac"]["endorsed"] is True and w["gruplac"]["country"] == "Colombia"
    assert [a["full_name"] for a in w["authors"]] == ["ANA MARIA PEREZ GOMEZ", "CARLOS ANDRES RUIZ MEJIA", "JOHN EXTERNAL DOE"]


def test_books_and_chapters(data):
    book, chapter = data["works"][3], data["works"][4]
    assert book["external_ids"] == [{"provenance": "gruplac", "source": "isbn", "id": "978-958-00000-0-1"}]
    assert book["source"]["publisher"] == {"name": "Editorial de Pruebas", "country": "Colombia"}
    assert chapter["source"]["name"] == "Libro de capítulos de prueba"
    assert chapter["bibliographic_info"]["start_page"] == "218"


def test_member_affiliation_by_year(data):
    first, old = data["works"][0], data["works"][1]
    ana, carlos, other = first["authors"]
    assert ana["id"] == "0000000001"
    assert ana["external_ids"] == [{"provenance": "gruplac", "source": "scienti", "id": "0000000001"}]
    aff = ana["affiliations"][0]
    assert (aff["id"], aff["types"]) == ("COL0008423", [{"source": "minciencias", "type": "group"}])
    assert aff["gruplac"]["provenance"] == "gruplac members"
    assert aff["gruplac"]["period"] == "2010/1 - Actual"
    assert 2017 in aff["years"]
    assert carlos["affiliations"][0]["gruplac"]["linkage"] == "Estudiante"  # 2015/2 - 2018/7 contains 2017
    assert other["id"] is None and other["affiliations"] == []
    assert old["authors"][0]["id"] == "0000000001" and old["authors"][0]["affiliations"] == []  # 2005: before 2010


def test_misspelled_member_name(data):
    a = data["works"][2]["authors"][0]
    assert a["id"] == "0000000003"
    assert a["affiliations"][0]["gruplac"]["name_match"] == "spelling"


def test_other_products_fields(data):
    soft = section(data, "Softwares")[0]
    assert (soft["type"], soft["title"], soft["availability"], soft["funder"]) == (
        "Computacional",
        "Analizador sintético",
        "Restringido",
        "UNIVERSIDAD DE ANTIOQUIA",
    )
    assert soft["links"][0]["url"] == "http://www.example.org/soft"
    assert soft["endorsed"] is True and soft["year"] == 2022
    cons = section(data, "Consultorías científico-tecnológicas")[0]
    assert (cons["start"], cons["end"], cons["institution"]) == ("2021-03", "2021-09", "EMPRESA DE PRUEBA SAS")
    assert cons["identifiers"] == [{"source": "contract", "id": "123-2021"}]
    assert cons["authors"] == []  # the page lists no authors for consultancies
    video = section(data, "Producciones de contenido digital - Audiovisual")[0]
    assert (video["date"], video["audience"], video["project"]) == ("2020-06", ["Juvenil", "Adulto"], "Ciencia para todos")


def test_social_appropriation_sections_merged(data):
    asc = section(data, ASC)
    assert [x["title"] for x in asc] == ["Proceso sintético con la comunidad", "Cadena productiva sintética"]
    assert asc[1]["type"].startswith(ASC + " - Proceso de apropiación social del Conocimiento para el fortalecimiento de cadenas")
    assert not any(t.lower().startswith("proceso") for t in data["other_products"])


def test_art_sections_inside_one_table(data):
    obra = section(data, "Obras o productos")[0]
    assert (obra["title"], obra["date"]) == ("Obra sintética", "2019-10")  # creation date, not presentation
    ev = section(data, "Eventos Artísticos")[0]
    assert ev["title"] == "CINEMATECA: Muestra sintética"  # upper-case text before ':' is not a label
    assert ev["description"] == "Evento de cierre: con dos puntos"
    assert data["section_categories"]["Obras o productos"] == "Producción en arte, arquitectura y diseño"


def test_empty_sections_are_left_out(data):
    assert "Notas científicas" not in data["counts"]
    assert "Guias de práctica clínica" not in data["other_products"]
    assert data["section_categories"]["Softwares"] == "PRODUCCIÓN TÉCNICA Y TECNOLÓGICA"


def test_thesis(data):
    t = section(data, "Trabajos dirigidos/turorías")[0]
    assert t["title"] == "Tesis sintética de pregrado"
    assert [(a["full_name"], a["type"]) for a in t["authors"]] == [
        ("ANA MARIA PEREZ GOMEZ", "advisor"),
        ("CARLOS ANDRES RUIZ MEJIA", "student"),
    ]
    assert (t["program"], t["role"], t["pages"], t["year"]) == ("FISICA", "Tutor principal", 40, 2017)
    assert t["institution"]["name"] == "UNIVERSIDAD DE ANTIOQUIA"
    provs = [x["gruplac"]["provenance"] for x in t["authors"][0]["affiliations"]]
    assert provs == ["gruplac members", "gruplac thesis"]


def test_jury_student(data):
    j = section(data, "Jurado/Comisiones evaluadoras de trabajo de grado")[0]
    assert [(a["full_name"], a["type"]) for a in j["authors"]] == [
        ("LUISA FERNANDA GIRALDO SOTO", "jury"),
        ("Pedro Pablo Prueba", "student"),
    ]


def test_projects_events_networks(data):
    p1, p2 = data["projects"]
    assert (p1["type"], p1["title"], p1["start"], p1["ongoing"]) == (
        "Investigación y desarrollo",
        "Plataforma sintética para pruebas",
        {"year": 2018, "month": 2},
        True,
    )
    assert p2["end"] == {"year": 2012, "month": 12}
    ev = data["events"][0]
    assert (ev["type"], ev["name"], ev["scope"], ev["start"], ev["place"]) == (
        "Congreso",
        "Congreso sintético de física",
        "Internacional",
        "2014-10-20",
        "MEDELLÍN",
    )
    assert ev["institutions"] == [{"name": "UNIVERSIDAD DE ANTIOQUIA", "link": "Patrocinadora"}]
    red = section(data, "Redes de Conocimiento Especializado")[0]
    assert (red["title"], red["type"], red["city"], red["start"]) == ("Red sintética de física", "Real", "MEDELLÍN", "2014-03-17")


def test_same_keys_in_a_collection(data):
    keys = [set(w) for w in data["works"]]
    assert all(k == keys[0] for k in keys)


def test_counts(data):
    c = data["counts"]
    assert (c["members"], c["works"], c["projects"], c["events"]) == (3, 5, 2, 1)
    assert c[ASC] == 2 and c["endorsed_works"] == 1
    assert c["works_with_affiliation"] == 4


def test_helpers():
    assert fields("Idioma: Español, Ciudad: , Duración: 6,") == ([("Idioma", "Español"), ("Ciudad", ""), ("Duración", "6")], "")
    assert fields("Colombia, 2020, Disponibilidad: Restringido")[1] == "Colombia, 2020"
    assert fields("medio de verificación: https://x.org/a")[0] == [("medio de verificación", "https://x.org/a")]
    assert iso_date("2023-02-01 00:00:00.0") == "2023-02-01"
    assert iso_date("Junio-1998") == "1998-06"
    assert period("2007/2 - 2009/7") == ({"year": 2007, "month": 2}, {"year": 2009, "month": 7}, False)


def test_resolve():
    assert resolve("COL0008423") == ("00000000001676", "COL0008423")
    assert resolve("1676") == ("00000000001676", "COL0008423")
    with pytest.raises(ValueError):
        resolve("COL9999999")
    with pytest.raises(ValueError):
        resolve("abc")


def test_colon_inside_a_title():
    fl, _ = fields("Nombre del Producto: Exposición Histórica: Los inmigrantes, en Barranquilla ,,")
    assert fl == [("Nombre del Producto", "Exposición Histórica: Los inmigrantes, en Barranquilla")]
    fl, _ = fields("Fecha de presentación: Año: 2021, Mes: Febrero")
    assert [k for k, _ in fl] == ["Fecha de presentación", "Año", "Mes"]


def test_journal_with_issn_zero():
    from gruplac_json.parser import work_from_item

    frag = (
        "1.- <strong>Publicado en revista especializada:</strong> Un artículo viejo<br/>\n"
        "Colombia, Revista Ciencia de Prueba ISSN: 0, 1992 vol:8 fasc: págs: - , DOI: <br>\nAutores: ANA MARIA PEREZ GOMEZ"
    )
    w = work_from_item("Artículos publicados", False, frag, "00000000000001", 1)
    assert (w["source"]["name"], w["source"]["external_ids"], w["year_published"]) == ("Revista Ciencia de Prueba", [], 1992)
