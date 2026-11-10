# Changelog

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- JSON-LD output: `to_jsonld(data, base=None)` and `--format jsonld` (with `--base` for the IRI prefix), as in
  cvlac-json and with its context: the same document plus `@context`, `@id` and `@type`; members, institutions,
  works, projects, events and other products get JSON Pointer `@id`s (`<group IRI>#/works/0`). README section and
  schema §14.

## [0.4.0] - 2026-11-03

### Changed
- `product_hash` of untitled items (no letter or digit in `title`): computed with the item's `text` (`gruplac.text` for works) instead of the empty title, as in cvlac-json 0.10. Hashes of titled items do not change. New count `product_hash_from_text`. Schema §13.

## [0.3.0] - 2026-11-02

### Added
- `product_hash` on the author entry of every member of every work and other product: the SHA-1 of
  `title|COD_RH|kind|year` (normalized title, the member's COD_RH, `work` or `other`), the same value cvlac-json puts
  on the owner of each CvLAC product, so a GrupLAC product joins each member's CvLAC entry. Unique per member
  (`|n` for repeated keys, counted in `counts.product_hash_repeated`); `product_hash.py` is a copy of cvlac-json's,
  pinned by the shared test vectors. README section and schema §13.

### Fixed
- The year of a work is the one of its citation line, not a year-like number inside the DOI, the ISSN or the pages
  (1806 for ISSN 1806-3756, 1916 for pages 1889 - 1916): 33 of 3,836 works in nine sample groups changed.

## [0.2.0] - 2026-11-02

### Added
- Authors who are members also get the group's declared institutions (`institutions`) as affiliations, with their ROR
  id, types, external ids and address, when the product's year is in the member's period, in the form of cvlac-json's
  affiliations from the experience (`gruplac.provenance: "gruplac institutions"`).

## [0.1.0] - 2026-11-02

### Added
- Parser of the public GrupLAC page: basic data, institutions, strategic plan, research lines, members
  ("Integrantes del grupo") with COD_RH and linkage period, bibliographic production as ImpactU works, projects,
  scientific events and every other section in `other_products`, with the structured fields of each item.
- Same record schema as cvlac-json for the same products (depends on cvlac-json for its helpers); the four social
  appropriation sections merged into "Apropiación social del conocimiento".
- Member affiliations: authors matched to members by name get their COD_RH and, when the product's year is in their
  linkage period, the group as affiliation with `gruplac.provenance: "gruplac members"`.
- Scienti ids from the group's records in apis.colav.co (`group_id`), with the other members' records of the same
  product in `scienti.also`; items without authors on the page get the members who registered them in Scienti.
- ROR ids of the group's institutions and of thesis institutions.
- COL code <-> GrupLAC number table (6,936 groups, 2026-10-31) shipped with the package.
- Items of Guías de práctica clínica and Proyectos de ley, which come after a blank header row.
- Command line `gruplac-json COL|NRO` with `--html`, `--save-html`, `--scienti`, `--ror`, `--apikey`.

[Unreleased]: https://github.com/restrepo/gruplac-json/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/restrepo/gruplac-json/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/restrepo/gruplac-json/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/restrepo/gruplac-json/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/restrepo/gruplac-json/releases/tag/v0.1.0
