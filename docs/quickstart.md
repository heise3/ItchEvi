# Quickstart

Install from a local source checkout:

```bash
python -m pip install .
itchevi demo --workdir synthetic_demo
```

Normalize the demo inputs:

```bash
itchevi normalize \
  --evidence synthetic_demo/inputs/evidence.tsv \
  --entities synthetic_demo/inputs/entities.tsv \
  --layers synthetic_demo/inputs/layers.tsv \
  --config synthetic_demo/inputs/qualification_config.json \
  --output normalized_demo
```

Then run qualification:

```bash
itchevi qualify \
  --evidence synthetic_demo/inputs/evidence.tsv \
  --entities synthetic_demo/inputs/entities.tsv \
  --layers synthetic_demo/inputs/layers.tsv \
  --config synthetic_demo/inputs/qualification_config.json \
  --output qualified_demo
```

The demo is a software contract test. It is not a biological result or a
performance benchmark for a disease dataset.
