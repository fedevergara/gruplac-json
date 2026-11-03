"""JSON-LD view of the GrupLAC JSON, as cvlac-json's for the CvLAC JSON.

``to_jsonld(data)`` returns the same document plus ``@context``, ``@id`` and ``@type``: every key keeps its
name and value. The context is cvlac-json's (the records have the same schema) with this package's vocabulary
and a few terms of its own:

- Page labels with spaces or accents (in ``profile.raw`` and ``strategic_plan``) get their own terms, with the
  label percent-encoded in the IRI. Open dictionaries (``counts``, ``section_categories``,
  ``affiliations_from_members``, ``scienti``) stay JSON literals.
- ``other_products`` is an index map: each item gets a ``section`` property with its section title.
- Members, institutions, works, projects, events and other products get an ``@id`` made of the group IRI and a
  JSON Pointer to their place in the document: ``<group IRI>#/works/0``.
"""

import copy

from cvlac_json.jsonld import context as cvlac_context
from cvlac_json.jsonld import pointer

VOCAB = "https://github.com/restrepo/gruplac-json/blob/main/docs/gruplac_json_esquema.md#"
GRUPLAC_URL = "https://scienti.minciencias.gov.co/gruplac/jsp/visualiza/visualizagr.jsp?nro="

_TERMS = {
    "col": "schema:identifier",
    "website": {"@id": "schema:url", "@type": "@id"},
    "email": "schema:email",
    "section_categories": {"@type": "@json"},
    "affiliations_from_members": {"@type": "@json"},
    "scienti": {"@type": "@json"},
}
_ITEMS = (
    ("members", "schema:OrganizationRole"),
    ("institutions", "schema:Organization"),
    ("works", "schema:CreativeWork"),
    ("projects", "schema:ResearchProject"),
    ("events", "schema:Event"),
)


def context(vocab=VOCAB, labels=()):
    """The @context; ``labels`` are extra keys (page labels) that need their own term."""
    ctx = cvlac_context(vocab, labels)
    ctx.update(_TERMS)
    return ctx


def to_jsonld(data, base=None, vocab=VOCAB):
    """JSON-LD document for the output of ``extract()``; ``data`` is not modified.

    The group IRI is ``base`` followed by the COL code (the GrupLAC number when the code is unknown) when
    ``base`` is given (e.g. the URL of a service that serves the groups), otherwise the URL of the GrupLAC page.
    """
    doc = copy.deepcopy(data)
    key = doc.get("col") or doc.get("nro") or ""
    iri = f"{base}{key}" if base else doc.get("url") or GRUPLAC_URL + str(doc.get("nro") or "")
    for name, typ in _ITEMS:
        for i, item in enumerate(doc.get(name) or []):
            if isinstance(item, dict):
                item["@id"], item["@type"] = iri + pointer(name, i), typ
    for title, items in (doc.get("other_products") or {}).items():
        for i, item in enumerate(items or []):
            if isinstance(item, dict):
                item["@id"] = iri + pointer("other_products", title, i)
    labels = [*((doc.get("profile") or {}).get("raw") or {}), *(doc.get("strategic_plan") or {})]
    return {
        "@context": context(vocab, labels=labels),
        "@id": iri,
        "@type": ["schema:ProfilePage", "GruplacProfile"],
        **doc,
    }
