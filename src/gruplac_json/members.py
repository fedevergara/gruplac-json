"""Authors -> group members ("Integrantes del grupo") and the group affiliation of each product's authors.

An author of a product is a member when the name written in "Autores" is the member's name in the members table:
the same words (`exact`), the same words in another order or one name inside the other with at least three
words (`words`), or the same words but one that differs by one letter or two swapped letters (`spelling`), as in
GIRLADO / GIRALDO. Only a single member may match. The member gets their COD_RH as `id`, and the group as
affiliation when the product's year falls in one of their periods ("Inicio - Fin Vinculación"); the affiliation
says where it comes from in `gruplac.provenance`, as cvlac-json does for affiliations from the CV's experience.
"""

import datetime as dt
import json

from cvlac_json import ror as ror_api
from cvlac_json.parser import norm

PROVENANCE = "gruplac members"
INST_PROVENANCE = "gruplac institutions"
RANK = {"exact": 0, "words": 1, "spelling": 2}


def _osa(a, b):
    """Edit distance with adjacent transpositions (optimal string alignment)."""
    d = [[i + j if i * j == 0 else 0 for j in range(len(b) + 1)] for i in range(len(a) + 1)]
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + (a[i - 1] != b[j - 1]))
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                d[i][j] = min(d[i][j], d[i - 2][j - 2] + 1)
    return d[-1][-1]


def how_match(a, b):
    """How the words of two names (already normalized and split) match: exact, words, spelling or None."""
    if not a or not b:
        return None
    if a == b:
        return "exact"
    sa, sb = set(a), set(b)
    if sa == sb or (min(len(sa), len(sb)) >= 3 and (sa <= sb or sb <= sa)):
        return "words"
    if len(a) == len(b) >= 2:
        diff = [(x, y) for x, y in zip(a, b, strict=True) if x != y]
        if len(diff) == 1 and min(len(diff[0][0]), len(diff[0][1])) >= 4 and _osa(*diff[0]) <= 1:
            return "spelling"
    return None


class Finder:
    """(member, how) of the single member whose name matches an author's name, else (None, None)."""

    def __init__(self, members):
        self.members = [(m, norm(m["full_name"]).split()) for m in members]
        self.cache = {}

    def __call__(self, name):
        a = tuple(norm(name).split())
        if a not in self.cache:
            hits = [(m, h) for m, b in self.members if (h := how_match(list(a), b))]
            res = (None, None)
            if hits:
                best = min(RANK[h] for _, h in hits)
                hits = [x for x in hits if RANK[x[1]] == best]
                if len({m["cod_rh"] for m, _ in hits}) == 1:
                    res = hits[0]
            self.cache[a] = res
        return self.cache[a]


def member_years(m, now=None):
    now = now or dt.date.today().year
    s = (m.get("start") or {}).get("year")
    e = (m.get("end") or {}).get("year") or (now if m.get("open_end") else s)
    return list(range(s, e + 1)) if s and e and e >= s else []


def group_affiliation(data, m, how):
    return {
        "id": data.get("col") or "",
        "name": data.get("name"),
        "types": [{"source": "minciencias", "type": "group"}],
        "external_ids": [
            *([{"provenance": "gruplac", "source": "minciencias", "id": data["col"]}] if data.get("col") else []),
            {"provenance": "gruplac", "source": "gruplac", "id": data["nro"]},
        ],
        "years": member_years(m),
        "gruplac": {
            "provenance": PROVENANCE,
            "member": m["full_name"],
            "linkage": m.get("linkage"),
            "hours": m.get("hours"),
            "period": m.get("period"),
            "name_match": how,
        },
    }


def institution_affiliation(inst, r, m):
    """A group's institution as affiliation of a member, in the form of cvlac-json's affiliations from the experience."""
    return {
        "id": r["id"] if r else "",
        "name": r["name"] if r else inst["name"],
        "types": r["types"] if r else [],
        "external_ids": r["external_ids"] if r else [],
        "addresses": r["addresses"] if r else [],
        "years": member_years(m),
        "gruplac": {
            "provenance": INST_PROVENANCE,
            "names": [inst["name"]],
            "status": inst.get("status"),
            "member": m["full_name"],
            "period": m.get("period"),
            "ror_match": r["match"] if r else None,
        },
    }


def item_year(it):
    y = it.get("year_published") or it.get("year")
    if not y:
        for k in ("date", "start", "end"):
            if str(it.get(k) or "")[:4].isdigit():
                return int(str(it[k])[:4])
    return int(y) if str(y or "").isdigit() else None


def records(data):
    """(kind, record) for every work and other product (theses included)."""
    for w in data["works"]:
        yield "works", w
    for _, its in (data.get("other_products") or {}).items():
        for it in its:
            yield "products", it


def enrich(data, ror_records=None):
    """Set id, external_ids and the affiliations of every author that is a member: the group and the group's institutions
    (with the ROR records of lookup_institutions), when the product's year is in the member's period. Safe to call again."""
    ror_records = ror_records or {}
    by_cod = {m["cod_rh"]: m for m in data["members"] if m.get("cod_rh")}
    find = Finder(data["members"])
    stats = {"authors": 0, "authors_matched": 0, "name_match": {}, "works_with_affiliation": 0, "products_with_affiliation": 0}
    for kind, it in records(data):
        year = item_year(it)
        got = False
        for a in it.get("authors") or []:
            stats["authors"] += 1
            m, how = find(a["full_name"])
            if not m and a.get("id") in by_cod:  # added from a Scienti record of this member
                m, how = by_cod[a["id"]], "scienti"
            if not m:
                a.update({"id": a.get("id") or None, "external_ids": a.get("external_ids") or []})
                a.setdefault("affiliations", [])
                continue
            stats["authors_matched"] += 1
            stats["name_match"][how] = stats["name_match"].get(how, 0) + 1
            a["id"] = m["cod_rh"]
            prov = "scienti" if how == "scienti" else "gruplac"
            a["external_ids"] = [{"provenance": prov, "source": "scienti", "id": m["cod_rh"]}]
            others = [
                x
                for x in a.get("affiliations") or []
                if (x.get("gruplac") or {}).get("provenance") not in (PROVENANCE, INST_PROVENANCE)
            ]
            aff = group_affiliation(data, m, how)
            if year and year in aff["years"]:
                insts = [institution_affiliation(i, ror_records.get(i["name"]), m) for i in data["institutions"]]
                a["affiliations"] = [aff, *insts, *others]
                got = True
            else:
                a["affiliations"] = others
        stats[f"{kind}_with_affiliation"] += got
    data["counts"]["works_with_affiliation"] = stats["works_with_affiliation"]
    data["counts"]["products_with_affiliation"] = stats["products_with_affiliation"]
    errors = (data.get("affiliations_from_members") or {}).get("ror_lookup_errors", 0)
    data["affiliations_from_members"] = {
        "ror_lookup_errors": errors,
        "members": len(data["members"]),
        "members_with_cod_rh": len(by_cod),
        **stats,
        "rule": "an author is a member when the name matches one member of 'Integrantes del grupo' (exact, same words "
        "or one name inside the other with >= 3 words, or one word misspelled by one letter); the group is the "
        "affiliation when the product's year is in the member's period 'Inicio - Fin Vinculación', and so are the group's "
        "institutions (with their ROR id)",
    }


def _looker(ror):
    cache = ror_api._load_cache() if ror else {}
    errors = [0]

    def look(name):
        if not ror:
            return None
        try:
            return ror_api.lookup(name, cache)
        except OSError:
            errors[0] += 1
            return None

    return cache, errors, look


def lookup_institutions(data, ror=True):
    """ROR of the group's institutions: sets institutions[].ror and returns {name: ROR record or None} for enrich()."""
    cache, errors, look = _looker(ror)
    out = {}
    for inst in data["institutions"]:
        r = out[inst["name"]] = look(inst["name"])
        inst["ror"] = {"id": r["id"], "name": r["name"], "match": r["match"]} if r else None
    if ror:
        ror_api._save_cache(cache)
    data.setdefault("affiliations_from_members", {})["ror_lookup_errors"] = errors[0]
    return out


def thesis_institutions(data, ror=True):
    """ROR of the thesis institutions, which also go to advisors and students."""
    cache, errors, look = _looker(ror)
    for it in (data.get("other_products") or {}).get("Trabajos dirigidos/turorías", []):
        inst = it.get("institution")
        if not (isinstance(inst, dict) and inst.get("name")):
            continue
        r = look(inst["name"])
        inst.update({"id": r["id"] if r else None, "ror_name": r["name"] if r else None, "ror_match": r["match"] if r else None})
        aff = {
            "id": r["id"] if r else "",
            "name": r["name"] if r else inst["name"],
            "types": r["types"] if r else [],
            "external_ids": r["external_ids"] if r else [],
            "addresses": r["addresses"] if r else [],
            "years": [it["year"]] if it.get("year") else [],
            "gruplac": {"provenance": "gruplac thesis", "names": [inst["name"]], "ror_match": r["match"] if r else None},
        }
        for a in it["authors"]:
            if a.get("type") in ("advisor", "student"):
                keep = [x for x in a.get("affiliations") or [] if (x.get("gruplac") or {}).get("provenance") != "gruplac thesis"]
                a["affiliations"] = [*keep, json.loads(json.dumps(aff))]
    if ror:
        ror_api._save_cache(cache)
    s = data.setdefault("affiliations_from_members", {})
    s["ror_lookup_errors"] = s.get("ror_lookup_errors", 0) + errors[0]


def add_product_hashes(data):
    """`product_hash` (product_hash.py, the same as cvlac-json's) on every member's author entry of every work and other
    product, computed with that member's COD_RH: a product signed by two members has two hashes, each the one of that
    member's CvLAC. Unique per member over their records in page order (works, then other_products); non-member
    authors get null. counts.product_hash_repeated: records that needed an occurrence number (n > 1). Projects are
    left out: GrupLAC lists no authors for them."""
    from .product_hash import hash_key, product_hashes

    per = {}  # cod_rh -> [(author entry, title, kind, year)]
    for w in data["works"]:
        for a in w.get("authors") or []:
            if a.get("id"):
                per.setdefault(a["id"], []).append((a, w.get("title"), "work", w.get("year_published")))
    for title, its in (data.get("other_products") or {}).items():
        kind = "patent" if title == "Patentes" else "other"
        for it in its:
            year = it.get("year") or (str(it.get("date") or "")[:4] if str(it.get("date") or "")[:4].isdigit() else None)
            for a in it.get("authors") or []:
                if a.get("id"):
                    per.setdefault(a["id"], []).append((a, it.get("title"), kind, year))
    for _, rec in records(data):
        for a in rec.get("authors") or []:
            a["product_hash"] = None
    repeated = 0
    for cod, entries in per.items():
        keys = [(t, k, y) for _, t, k, y in entries]
        for (a, *_), h in zip(entries, product_hashes(keys, cod), strict=True):
            a["product_hash"] = h
        repeated += len(keys) - len({hash_key(t, cod, k, y) for t, k, y in keys})
    data["counts"]["product_hash_repeated"] = repeated
