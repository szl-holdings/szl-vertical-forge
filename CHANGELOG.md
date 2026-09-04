"""# Changelog

## v0.2.0 — 2026-09-04 (lineage instill)

- Every vertical config gains `lineage`: field leader, the job they own, and
  the SZL tweak — researched from public sources (Anduril Lattice, Credo/Arthur,
  Regrid/ATTOM, Grafana+OpenTelemetry, Harvey/CoCounsel, QuantConnect LEAN/
  Riskfolio-Lib). Doctrine on every shell: take the JOB from the leader,
  never the code.
- Validation now requires lineage (leader + job + tweak) — fail closed.
- New fleet master hash `096eb2c2b1eddf32` (was `dfe76283112249f7` at v0.1.0);
  dist/RECEIPT.json updated. Verified deterministic pre-push.

## v0.1.0 — 2026-09-04

Initial forge: 8 audited vertical configs → killinchu-pattern shells,
deterministic, fail-closed. 5/5 tests green pre-push.
"""