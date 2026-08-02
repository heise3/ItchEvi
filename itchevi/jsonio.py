from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from importlib.resources import files
from pathlib import Path
from typing import Any

from jsonschema.validators import validator_for

from . import __version__
from .validation import (
    CONFIG_REQUIRED,
    ENTITY_REQUIRED,
    EVIDENCE_REQUIRED,
    LAYER_REQUIRED,
    assert_valid,
    read_json,
    read_tsv,
    validate_objects,
)


EVIDENCE_FLOAT_FIELDS = {"effect", "SE", "P", "FDR", "quality_multiplier"}
EVIDENCE_INT_FIELDS = {"direction", "n_independent_units"}
EVIDENCE_FIELDS = (
    "record_id",
    "entity_id",
    "layer_id",
    "dataset_id",
    "evidence_role",
    "statistical_unit",
    "paired_or_descriptive",
    "effect",
    "SE",
    "P",
    "FDR",
    "direction",
    "n_independent_units",
    "quality_multiplier",
    "terminal_state",
    "failure_code",
    "source_confidence",
    "input_sha256",
    "config_sha256",
    "software_version",
    "gate_status",
)
ENTITY_FIELDS = (
    "entity_id",
    "claim_id",
    "claim_text",
    "construction_layer_id",
    "target_direction",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _nullable_float(value: str) -> float | None:
    return None if value == "" else float(value)


def _nullable_int(value: str) -> int | None:
    return None if value == "" else int(float(value))


def _assert_exact_fields(rows: list[dict[str, str]], expected: set[str], label: str) -> None:
    extras = sorted(set(rows[0]) - expected)
    if extras:
        raise ValueError(f"{label} contains columns outside its JSON Schema: {extras}")


def normalize_evidence(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    _assert_exact_fields(rows, EVIDENCE_REQUIRED, "evidence")
    normalized: list[dict[str, Any]] = []
    for row in rows:
        item: dict[str, Any] = {}
        for field in EVIDENCE_FIELDS:
            if field in EVIDENCE_FLOAT_FIELDS:
                item[field] = _nullable_float(row[field])
            elif field in EVIDENCE_INT_FIELDS:
                item[field] = _nullable_int(row[field])
            else:
                item[field] = row[field]
        normalized.append(item)
    return normalized


def normalize_entities(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    _assert_exact_fields(rows, ENTITY_REQUIRED, "entities")
    normalized: list[dict[str, Any]] = []
    for row in rows:
        item: dict[str, Any] = {field: row[field] for field in ENTITY_FIELDS}
        if item["target_direction"] != "AUTO":
            item["target_direction"] = int(item["target_direction"])
        normalized.append(item)
    return normalized


def normalize_layers(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    _assert_exact_fields(rows, LAYER_REQUIRED, "layers")
    return [
        {
            "layer_id": row["layer_id"],
            "requirement": row["requirement"],
            "weight": float(row["weight"]),
            "conditional_rule": row["conditional_rule"],
        }
        for row in rows
    ]


def _validate_schema(schema_name: str, payload: Any) -> None:
    schema = json.loads(files("itchevi").joinpath("schemas", schema_name).read_text(encoding="utf-8"))
    validator = validator_for(schema)
    validator.check_schema(schema)
    validator(schema).validate(payload)


def normalize_inputs(
    evidence_path: Path,
    entities_path: Path,
    layers_path: Path,
    config_path: Path,
    output_dir: Path,
    *,
    entry_point: str = "python_api:normalize",
) -> dict[str, Any]:
    evidence_rows = read_tsv(evidence_path)
    entity_rows = read_tsv(entities_path)
    layer_rows = read_tsv(layers_path)
    config = read_json(config_path)
    assert_valid(validate_objects(evidence_rows, entity_rows, layer_rows, config))
    extra_config = sorted(set(config) - CONFIG_REQUIRED)
    if extra_config:
        raise ValueError(f"config contains keys outside its JSON Schema: {extra_config}")

    payloads = {
        "evidence.json": normalize_evidence(evidence_rows),
        "entities.json": normalize_entities(entity_rows),
        "layers.json": normalize_layers(layer_rows),
        "qualification_config.json": config,
    }
    schemas = {
        "evidence.json": "evidence.schema.json",
        "entities.json": "entities.schema.json",
        "layers.json": "layers.schema.json",
        "qualification_config.json": "qualification_config.schema.json",
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, payload in payloads.items():
        _validate_schema(schemas[name], payload)
        (output_dir / name).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    manifest = {
        "status": "PASS",
        "itchevi_version": __version__,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "entry_point": entry_point,
        "input_hashes": {
            path.name: _sha256(path)
            for path in [evidence_path, entities_path, layers_path, config_path]
        },
        "output_hashes": {name: _sha256(output_dir / name) for name in payloads},
        "row_counts": {
            "evidence": len(evidence_rows),
            "entities": len(entity_rows),
            "layers": len(layer_rows),
        },
        "missing_numeric_semantics": "blank TSV numeric cells are JSON null, never zero",
        "schemas": schemas,
    }
    (output_dir / "normalization_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return manifest
