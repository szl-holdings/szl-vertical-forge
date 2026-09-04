# szl-vertical-forge

Audited vertical configs in, killinchu-pattern shells out. The forge is how
every SZL vertical gets the flagship treatment: a landing page with the
application demoed inside, probed against real data at request time, wired
to the estate's repos, kernels, models, and datasets — with a build receipt
per shell and one deterministic master hash for the whole fleet.

## The pattern (distilled from killinchu)

Landing hero → doctrine chips → live-status pill (PROBING / MEASURED /
UNAVAILABLE / DECLARED) → the live demo panel → estate wiring grid →
receipt footer. No fabricated data anywhere: the shell's own JS probes its
endpoint and says UNAVAILABLE rather than fake it.

## The eight audited verticals

killinchu · sentra · puriq · terra · lyte · counsel · finance · david-leads
— configs in `src/szl_vertical_forge/verticals.json`, taken from the
2026-09-04 estate audit (owner-amended: aegis→sentra, vessels→killinchu).

## Usage

```bash
pip install -e . pytest
python -m pytest tests/ -q
python -m szl_vertical_forge.forge   # prints the master hash of the fleet
```

Same configs, same bytes, same master hash — on any machine. Regenerate and
compare hashes instead of trusting presented files.

## Doctrine

- Configs are the audited estate map, not invention.
- Fail-closed validation: a bad config stops the run and names every error.
- Deterministic output — the receipt is regenerable, not just presented.
- Python 3.11+, standard library only.

## License

Apache-2.0 — canonical org text (see LICENSE pointer).
