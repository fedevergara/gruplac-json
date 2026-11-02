"""Scienti identifiers (apis.colav.co) for the items of a GrupLAC JSON, from the Scienti records of the group.

The records come from /scienti/product|project|event|network?group_id=COL...; each one is a member's CvLAC entry,
so one GrupLAC product can match several records (one per member who registered it). The best match goes to
`scienti` with the rules of cvlac-json (DOI; exact title plus year, ISSN, ISBN or venue; truncated title plus the
same year; projects, events and networks by exact name and year), and the other records of the same product
(same DOI, or same title and year) to `scienti.also`. Items that list no authors on the page (consultancies,
technical concepts, ASC processes...) get as authors the members whose COD_RH registered the matching records.
"""

import re

from cvlac_json.scienti import (
    INSTITUTIONS,
    MIN_PREFIX,
    MIN_TITLE,
    MIN_WORDS,
    apikey,
    digits,
    get,
    index_products,
    match_entry,
    norm,
)
from cvlac_json.scienti import year_of as syear

from .members import records


def same_product(c, r):
    if r is c:
        return False
    if c["doi"] and r["doi"]:
        return c["doi"] == r["doi"]
    return bool(c["title"]) and r["title"] == c["title"] and (not r["year"] or not c["year"] or int(r["year"]) == int(c["year"]))


def tag_all(entries, key_of, recs, rec_id, rec_title, rec_year, min_title=MIN_TITLE):
    """Projects / events / networks: exact normalized name and the same year; all matching records are kept."""
    n = 0
    for e in entries:
        t, y = norm(key_of(e)[0]), key_of(e)[1]
        if not t:
            continue
        hits = [r for r in recs if norm(rec_title(r)) == t and (y is None or rec_year(r) is None or int(rec_year(r)) == int(y))]
        if len(t) < min_title:  # short names need the year as extra evidence
            hits = [r for r in hits if y and rec_year(r) and int(rec_year(r)) == int(y)]
        if not hits:
            continue
        r = hits[0]
        e["scienti"] = {
            "id": rec_id(r),
            "by": "title",
            "evidence": ["year"] if y and rec_year(r) else [],
            "scienti_title": rec_title(r),
            "scienti_year": rec_year(r),
            "also": sorted({rec_id(x) for x in hits[1:]} - {rec_id(r)}),
        }
        n += 1
    return n


def add_authors_from_scienti(it, data):
    """Items with no author on the page: the members whose COD_RH has one of the matching Scienti records."""
    if it.get("authors") or not it.get("scienti"):
        return 0
    by_cod = {m["cod_rh"]: m for m in data["members"] if m.get("cod_rh")}
    cods = []
    for pid in [it["scienti"]["id"], *it["scienti"].get("also", [])]:
        cod = pid.split("-")[0]
        if cod in by_cod and cod not in cods:
            cods.append(cod)
    it["authors"] = [{"full_name": by_cod[c]["full_name"], "id": c, "external_ids": [], "affiliations": []} for c in cods]
    if cods:
        it["authors_inferred"] = True
    return len(cods)


def enrich(data, col, institution=None, model_year=None, key=None, log=print):
    key = apikey(key)
    if not key:
        log("scienti: no API key ($COLAV_APIKEY or ~/.config/colav/apikey); skipped")
        return False
    info = {x["institution"]: x["model_year"] for x in get("/scienti/info", key, get="resume")}
    order = [institution] if institution else [i for i in INSTITUTIONS if i in info] + [i for i in info if i not in INSTITUTIONS]
    products, inst = [], None
    for i in order:
        my = model_year or info.get(i)
        try:
            products = get("/scienti/product", key, group_id=col, model_year=my, institution=i)
        except RuntimeError as e:
            log(f"scienti: {i} {my}: {e}")
            continue
        if isinstance(products, list) and products:
            inst = i
            break
    if not inst:
        log(f"scienti: no products for {col} in {', '.join(order)}")
        data["scienti"] = {"institution": None, "model_year": None, "products": 0, "note": "group not found in the Scienti dumps"}
        return False
    my = model_year or info[inst]

    def fetch(ep):
        d = get(f"/scienti/{ep}", key, group_id=col, model_year=my, institution=inst)
        return d if isinstance(d, list) else []

    projects, events, networks = fetch("project"), fetch("event"), fetch("network")
    index = index_products(products, [])
    used, n = set(), {"works": 0, "other_products": 0}
    for kind, it in records(data):
        if kind == "works":
            ids = [x["id"] for x in it["source"].get("external_ids", [])] + [
                x["id"] for x in it["external_ids"] if x["source"] == "isbn"
            ]
            res = match_entry(
                index,
                used,
                title=it["title"],
                text=it["gruplac"]["text"],
                year=it["year_published"],
                doi=it["doi"],
                issn=[i for i in ids if len(digits(i)) == 8],
                isbn=[i for i in ids if len(digits(i)) >= 10],
                venue=it["source"].get("name"),
            )
        else:
            txt = it.get("text", "")
            res = match_entry(
                index,
                used,
                title=it.get("title"),
                text=txt,
                year=it.get("year"),
                isbn=re.findall(r"ISBN:?\s*([\dXx-]{10,17})", txt),
                issn=re.findall(r"ISSN:?\s*([\dXx-]{8,9})", txt),
            )
        c, by, ev = res
        if not c:
            continue
        also = [r["id"] for r in index if same_product(c, r)]
        holder = it["gruplac"] if kind == "works" else it
        holder["scienti"] = {
            "id": c["id"],
            "by": by,
            "evidence": ev,
            "shared": c["id"] in used,
            "scienti_title": c["raw_title"],
            "scienti_year": c["year"],
            "also": also,
        }
        used.update([c["id"], *also])
        n["works" if kind == "works" else "other_products"] += 1
        if kind == "works":
            it["external_ids"] += [{"provenance": "scienti", "source": "scienti", "id": x} for x in [c["id"], *also]]
    n_proj = tag_all(
        data["projects"],
        lambda p: (p.get("title"), (p.get("start") or {}).get("year")),
        projects,
        lambda r: f"{r['COD_RH']}-{r['COD_PROYECTO']}",
        lambda r: r.get("TXT_NME_PROYECTO"),
        lambda r: syear(r.get("NRO_ANO_INICIO")),
    )
    n_ev = tag_all(
        data["events"],
        lambda e: (e.get("name"), syear(e.get("start"))),
        events,
        lambda r: f"{r['COD_RH']}-{r['COD_EVENTO']}",
        lambda r: r.get("TXT_NME_EVENTO"),
        lambda r: r.get("NRO_ANO_REALIZACION") or syear(r.get("DTA_INICIO")),
    )
    nets = (data.get("other_products") or {}).get("Redes de Conocimiento Especializado", [])
    n_net = tag_all(
        nets,
        lambda it: (it.get("title"), it.get("year")),
        networks,
        lambda r: f"{r['COD_RH']}-{r['COD_RED']}",
        lambda r: r.get("TXT_NME_RED"),
        lambda r: syear(r.get("DTA_FECHA_INI")),
        min_title=5,
    )
    for p in data["projects"]:
        s = p.get("scienti")
        if s:
            p["external_ids"] = [{"provenance": "scienti", "source": "scienti", "id": x} for x in [s["id"], *s["also"]]]
    added = sum(add_authors_from_scienti(it, data) > 0 for kind, it in records(data) if kind == "products")
    data["scienti"] = {
        "institution": inst,
        "model_year": my,
        "source": "apis.colav.co",
        "group_id": col,
        "products": len(index),
        "products_matched": len(used),
        "matched": {**n, "projects": n_proj, "events": n_ev, "networks": n_net},
        "records": {"projects": len(projects), "events": len(events), "networks": len(networks)},
        "items_with_authors_from_scienti": added,
        "rules": f"DOI, or exact normalized title (>= {MIN_TITLE} chars and {MIN_WORDS} words) plus year, ISSN, ISBN or venue, "
        f"or a truncated title (prefix, >= {MIN_PREFIX} chars) plus the same year; projects/events/networks: exact "
        "normalized name plus the same year. `also`: the other members' records of the same product (same DOI, or "
        "same title and year)",
        "not_on_page": len(index) - len({x for x in used if x in {c["id"] for c in index}}),
        "not_on_page_note": "Scienti product records of the group that no GrupLAC item matched (they may repeat a "
        "matched product with a different title, or be products the GrupLAC page does not show)",
    }
    log(
        f"scienti ({inst} {my}): product records {len(used)}/{len(index)} matched (works {n['works']}, other items "
        f"{n['other_products']}); projects {n_proj}/{len(data['projects'])}, events {n_ev}/{len(data['events'])}, "
        f"networks {n_net}/{len(nets)}; items with authors from Scienti {added}"
    )
    return True
