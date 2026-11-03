"""Product hash: one id for a product of one person, the same in cvlac-json and gruplac-json.

    product_hash("Singlet Dirac dark matter streamlined", "0000707619", "work", 2024)

is the SHA-1 (40 hex digits) of the key

    <title> | <cod_rh> | <kind> | <year>

- title: lowercased, accents and other marks dropped (Unicode NFKD, then ASCII only: "Física" -> "fisica",
  the math letter "𝐽" -> "j"), and then only the letters a-z and digits 0-9 kept, so spaces and punctuation do not
  count ("Bleomicina: Una revisión" and "bleomicina:una revision" give the same key).
- cod_rh: the person's COD_RH, 10 digits ("707619" -> "0000707619").
- kind: "work" (bibliographic production), "project", "patent" or "other" (any other product).
- year: the product's year as digits (works: year_published; projects: start year; patents and other products: year,
  else the year of date), or "" when there is none.

Example key: "singletdiracdarkmatterstreamlined|0000707619|work|2024".

Unique within a person's records: when several of them give the same key (the same product entered twice, a course
given twice in a year, untitled items such as Par evaluador reviews of the same year), the first keeps the key and
the n-th, in page order, gets "|n" appended ("…|work|2024|2"). The first occurrence is the one another source
reproduces; a later one matches only if that source lists the same repeats in the same order.

A CvLAC lists a product once for its owner, and a GrupLAC once for the group with every member who authored it,
so the hash goes on the person's author entry: in a CvLAC the owner's, in a GrupLAC each member's (with that
member's COD_RH). Equal hashes mean the same title, person, kind and year (and occurrence).

This file is standard library only and is meant to be copied unchanged between the two packages; the test vectors in
tests/product_hash_vectors.json pin its output.
"""

import hashlib
import re
import unicodedata

KINDS = ("work", "project", "patent", "other")


def title_key(title):
    """'Bleomicina: Una revisión' -> 'bleomicinaunarevision'."""
    t = unicodedata.normalize("NFKD", title or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "", t)


def hash_key(title, cod_rh, kind, year=None, n=1):
    """The string that is hashed: 'title|cod_rh|kind|year', plus '|n' for the n-th record (n > 1) with that key."""
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {KINDS}")
    cod = str(cod_rh).strip().zfill(10)
    y = str(year).strip() if year not in (None, "") else ""
    key = f"{title_key(title)}|{cod}|{kind}|{y}"
    return key if n == 1 else f"{key}|{n}"


def product_hash(title, cod_rh, kind, year=None, n=1):
    """SHA-1 hex digest of hash_key(title, cod_rh, kind, year, n)."""
    return hashlib.sha1(hash_key(title, cod_rh, kind, year, n).encode("ascii")).hexdigest()


def product_hashes(records, cod_rh):
    """Unique hashes for one person's records, in order: records is a list of (title, kind, year); the n-th record
    with an already used key gets n. Returns the hashes in the same order."""
    seen, out = {}, []
    for title, kind, year in records:
        k = hash_key(title, cod_rh, kind, year)
        seen[k] = seen.get(k, 0) + 1
        out.append(product_hash(title, cod_rh, kind, year, seen[k]))
    return out
