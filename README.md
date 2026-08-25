# ItchEvi 0.5.0

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.22095993.svg)](https://doi.org/10.5281/zenodo.22095993)

ItchEvi is a failure-aware qualification engine for donor-level transcriptomic
evidence. It asks whether a prespecified gene or program claim remains
qualifiable after required evidence, stability and provenance gates. It does
not optimize candidate rank and does not convert missing or failed analyses to
zero.

## Current scope

Version 0.5.0 implements the Phase 5I qualification core and portable input
normalization:

- evidence, entity, layer and configuration validation;
- `OBSERVED / MISSING / FAILED / NOT_APPLICABLE` algebra;
- coverage, directional support and conflict summaries;
- gate-based `QUALIFIED`, `QUALIFIED_WITH_BOUNDARY`, `DESCRIPTIVE_ONLY`,
  `ABSTAIN` and `NOT_QUALIFIED` decisions;
- one terminal record per entity-layer pair;
- CLI/API-equivalent execution;
- provenance-complete success/failure manifests with hashes, timing,
  Python-memory peak, environment fingerprint and execution context;
- deterministic synthetic end-to-end demo.
- TSV-to-JSON normalization against seven shipped Draft 2020-12 schemas;
- explicit JSON `null` for missing numeric values, never numeric zero;
- deterministic normalized JSON across accepted Python versions.

The previous Cell Ranger reader, frozen-contract audit and legacy external
stage wrappers are retained. Legacy wrappers still require project-external
scripts and are not part of the portable qualification core.

## Release provenance

The biological analyses reported in the associated manuscript were executed
against frozen commit `105f4aeb13690a419fa3e9e49f4bc52907e93538`.
Release `v0.5.0` adds citation and archival metadata only; it does not modify
the qualification implementation at that commit. Panel-level source tables,
frozen program banks, figure-generation scripts and their SHA256 manifest are
attached to the GitHub release.

Repository: https://github.com/heise3/ItchEvi

Archived release: https://doi.org/10.5281/zenodo.22095993

## Install

```bash
python -m pip install .
```

## End-to-end demo

```bash
itchevi demo --workdir demo_run
```

Expected primary result:

- class: `QUALIFIED_WITH_BOUNDARY`;
- support: `0.75`;
- conflict: `0.25`;
- coverage: `1.0`;
- boundary: optional spatial input missing.

All values are synthetic contract tests, not biological results.

## CLI

```bash
itchevi validate \
  --evidence evidence.tsv \
  --entities entities.tsv \
  --layers layers.tsv \
  --config qualification_config.json

itchevi qualify \
  --evidence evidence.tsv \
  --entities entities.tsv \
  --layers layers.tsv \
  --config qualification_config.json \
  --output results

itchevi normalize \
  --evidence evidence.tsv \
  --entities entities.tsv \
  --layers layers.tsv \
  --config qualification_config.json \
  --output normalized_inputs
```

Outputs:

- `qualification.tsv`;
- `terminal_ledger.tsv`;
- `validation.tsv`;
- `qualification_report.md`;
- `run_manifest.json`.

## Python API

```python
from pathlib import Path
from itchevi import normalize_inputs, qualify

normalize_inputs(
    Path("evidence.tsv"),
    Path("entities.tsv"),
    Path("layers.tsv"),
    Path("qualification_config.json"),
    Path("normalized_inputs"),
)

run = qualify(
    Path("evidence.tsv"),
    Path("entities.tsv"),
    Path("layers.tsv"),
    Path("qualification_config.json"),
    Path("results"),
)
print(run.summary)
```

## Schemas

Versioned schemas are shipped in `itchevi/schemas/` for:

- evidence records;
- entities;
- layer manifest;
- qualification config;
- qualification output;
- terminal ledger.
- run manifest.

TSV files use the same fields; blank numeric cells represent missing values.
They are never interpreted as numeric zero.

## Tests

```bash
python -m unittest discover -s tests -v
```

The 24-test suite covers core decisions, missing/failure semantics, validation, JSON
Schema metaschema and instance checks, success/failure provenance receipts,
CLI/API equivalence, deterministic demo outputs, reporting and legacy reader
compatibility. The accepted wheel was independently tested under Python 3.11
and Python 3.12. Exact accepted dependency snapshots are provided in
`environment.py311.lock.txt` and `environment.py312.lock.txt`.

## Scientific boundaries

- Donors or donor pairs are biological statistical units.
- Cells and spots are measurement units.
- Qualification applies only to the configured claim.
- Whole-skin transfer is not cell-state replication.
- Spatial model weights are not measured proportions.
- ItchEvi does not establish itch specificity, mechanism, causality or
  treatment efficacy.
- The historical evidence-ranker added-value failure is not overwritten by
  this qualification endpoint.

## License

ItchEvi is released under the MIT License. Original public datasets are not
redistributed and remain subject to their source repositories' terms.
