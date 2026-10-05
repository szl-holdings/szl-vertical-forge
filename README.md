# szl-vertical-forge

`szl-vertical-forge` turns the eight audited vertical configurations into
deployable landing-page artifacts and recomputable build receipts. It is a
build tool, not a runtime or provider controller.

Each generated vertical contains:

- `index.html`, with a read-only runtime probe and a link to the governed
  workbench at `/panels`;
- `build-receipt.json`, binding that index to its audited configuration and
  the fleet receipt chain;
- fleet-level `RECEIPT.json`, a canonical-JSON SHA-256 chain starting from
  64 zeroes and ending at `chain_tip`; the deterministic `master_hash` binds
  that tip to the canonical receipt header (generator, algorithm, genesis,
  config digest and vertical count), so a mutated header does not verify.

The browser reports `REACHABLE` only for a validated upstream response,
`PARTIAL` when some sources are unavailable, `STALE` for cached or aged
observations, `SAMPLE` or `MODELED` for non-live evidence, and `UNAVAILABLE`
for failed or malformed responses. The badge and detail panel come from the
same response. Reachability is never represented as a domain measurement,
authorization, deployment, or provider state.

## Audited verticals

killinchu · sentra · puriq · terra · lyte · counsel · finance · david-leads

The source configuration is
`src/szl_vertical_forge/verticals.json`. Every row includes explicit lineage:
the public field leader, the job that leader demonstrates, and the original
SZL adaptation. The forge copies no proprietary implementation.

Primary lineage sources are rendered into every generated shell and included
in its configuration digest:

- Killinchu: [Anduril's JIATF-401 Lattice announcement](https://www.anduril.com/news/jiatf-401-selects-lattice-as-enterprise-tactical-command-and-control-platform-for-c-uas)
- Sentra: [Credo AI Agent Registry](https://www.credo.ai/ai-agent-registry) and [Arthur observability documentation](https://docs.arthur.ai/docs/platform-ui)
- Terra: [Regrid MCP documentation](https://support.regrid.com/docs/mcp-server)
- Lyte: [Grafana's OpenTelemetry Collector documentation](https://grafana.com/docs/loki/latest/send-data/otel/otel-collector-getting-started/)
- Counsel: [Harvey](https://www.harvey.ai/) and [Thomson Reuters CoCounsel Legal](https://legal.thomsonreuters.com/en/products/cocounsel-legal)
- Finance: [QuantConnect LEAN](https://www.quantconnect.com/docs/v2/writing-algorithms/key-concepts/algorithm-engine) and [Riskfolio-Lib](https://riskfolio-lib.readthedocs.io/en/latest/)
- PURIQ and David Leads: their canonical SZL source repositories, because the
  category claim is explicitly internal rather than attributed externally.

## Install, test, and generate

The test suite also requires Node.js on PATH to parse every generated browser script.

```bash
python -m pip install --no-build-isolation -e . "pytest==8.4.2"
python -m pytest tests/ -q
python -m szl_vertical_forge.forge generate --output-dir dist
python -m szl_vertical_forge.forge verify --output-dir dist
```

Generate and verify only Terra when preparing its deployment payload:

```bash
python -m szl_vertical_forge.forge generate --vertical terra --output-dir build/terra
python -m szl_vertical_forge.forge verify --vertical terra --output-dir build/terra
```

`generate` exits nonzero unless every expected file is written and then
verified byte-for-byte. `verify` never repairs mismatches; missing or changed
bytes produce `INVALID` and a nonzero exit status.

## Operational boundary

The forge proves local deterministic generation and receipt-chain integrity.
It does not prove that a Space is deployed, healthy, source-aligned, or backed
by a real data provider. Deployment must preserve the vertical's existing
workbench at `/panels`, land through its protected source workflow, and then
verify the immutable provider revision plus live routes independently.

## License

Apache-2.0 — canonical organization text is referenced by `LICENSE`.
