# Changelog

## v0.2.2 — 2026-09-05 (browser template repair)

- Render the format template in one pass so CSS and JavaScript brace escapes
  become browser syntax while substituted text remains literal data.
- Parse each generated browser script with Node.js in the regression suite and
  verify CSS template escapes are removed.
- Regenerate the eight artifacts and their receipt chain from the repaired source.

## v0.2.1 — 2026-09-04 (operational artifact pipeline)

- The CLI now writes and byte-verifies generated artifacts instead of printing
  a hash for bytes that were never persisted.
- Every index is bound into a canonical-JSON SHA-256 chain from an all-zero
  genesis; per-vertical and fleet receipts are emitted together.
- Added read-only verification, one-vertical generation, HTML/URL hardening,
  explicit `OBSERVED` versus `UNAVAILABLE` labels, and tamper tests.
- Package metadata now matches the generator version.
- CI actions are immutable-SHA pinned and test both supported Python versions.

## v0.2.0 — 2026-09-04 (lineage instill)

- Every vertical config gained explicit field-leader lineage and the original
  SZL adaptation.
- Validation began requiring lineage and failed closed when it was absent.
- The fleet's then-current abbreviated master hash was recorded as
  `096eb2c2b1eddf32`.

## v0.1.0 — 2026-09-04

Initial deterministic shell renderer for eight audited vertical configs.
