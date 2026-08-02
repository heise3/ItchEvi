# Contributing to ItchEvi

Contributions should preserve deterministic evidence qualification and the
distinction between missing, failed, not-applicable, and observed evidence.

## Development checks

1. Create a Python 3.11 or 3.12 environment.
2. Install the package with `python -m pip install ".[test]"`.
3. Run `python -m unittest discover -s tests -v`.
4. Run `itchevi demo --workdir synthetic_demo`.
5. Run the normalized-JSON smoke test documented in `docs/quickstart.md`.

Changes to schemas, qualification classes, missing-value semantics, threshold
interpretation, or terminal-ledger behavior require versioned tests and an
explicit migration note. Biological results and participant-level data must
not be committed to this software repository.
