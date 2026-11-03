# Changelog

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

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

[Unreleased]: https://github.com/restrepo/gruplac-json/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/restrepo/gruplac-json/releases/tag/v0.1.0
