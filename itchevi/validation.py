from __future__ import annotations

import csv
import json
import math
import re
from pathlib import Path
from typing import Any

from .models import ALLOWED_GATE_STATUS, ALLOWED_REQUIREMENTS, ALLOWED_TERMINAL_STATES


EVIDENCE_REQUIRED = {
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
}
ENTITY_REQUIRED = {
    "entity_id",
    "claim_id",
    "claim_text",
    "construction_layer_id",
    "target_direction",
}
LAYER_REQUIRED = {"layer_id", "requirement", "weight", "conditional_rule"}
CONFIG_REQUIRED = {
    "run_id",
    "V_min",
    "S_min",
    "K_max",
    "min_independent_units",
    "discovery_fdr_max",
    "stability_layer_ids",
    "boundary_on_optional_missing",
    "condition_flags",
}
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
CONDITION_FLAG_RE = re.compile(r"^flag:([A-Za-z][A-Za-z0-9_]*)$")


def condition_is_active(rule: str, config: dict[str, Any]) -> bool:
    """Evaluate an outcome-independent layer condition from frozen config."""
    normalized = rule.strip()
    if normalized in {"always", "when_available"}:
        return True
    match = CONDITION_FLAG_RE.fullmatch(normalized)
    if match:
        return bool(config["condition_flags"][match.group(1)])
    raise ValueError(f"unsupported conditional_rule {rule!r}")


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if not reader.fieldnames:
            raise ValueError(f"TSV has no header: {path}")
        return [dict(row) for row in reader]


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def _float(value: str, field: str, allow_blank: bool = True) -> float | None:
    if value in {"", None}:  # type: ignore[comparison-overlap]
        if allow_blank:
            return None
        raise ValueError(f"{field} is required")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{field} must be finite")
    return number


def _int(value: str, field: str, allow_blank: bool = True) -> int | None:
    number = _float(value, field, allow_blank=allow_blank)
    if number is None:
        return None
    if not number.is_integer():
        raise ValueError(f"{field} must be an integer")
    return int(number)


def _check_columns(rows: list[dict[str, str]], required: set[str], name: str) -> list[str]:
    if not rows:
        return [f"{name}: no data rows"]
    missing = sorted(required - set(rows[0]))
    return [f"{name}: missing columns {missing}"] if missing else []


def validate_objects(
    evidence: list[dict[str, str]],
    entities: list[dict[str, str]],
    layers: list[dict[str, str]],
    config: dict[str, Any],
) -> list[dict[str, str]]:
    errors: list[str] = []
    errors.extend(_check_columns(evidence, EVIDENCE_REQUIRED, "evidence"))
    errors.extend(_check_columns(entities, ENTITY_REQUIRED, "entities"))
    errors.extend(_check_columns(layers, LAYER_REQUIRED, "layers"))
    missing_config = sorted(CONFIG_REQUIRED - set(config))
    if missing_config:
        errors.append(f"config: missing keys {missing_config}")

    record_ids: set[str] = set()
    entity_layer: set[tuple[str, str]] = set()
    for index, row in enumerate(evidence, start=2):
        label = f"evidence row {index}"
        try:
            if not row["record_id"] or row["record_id"] in record_ids:
                raise ValueError("record_id is blank or duplicated")
            record_ids.add(row["record_id"])
            key = (row["entity_id"], row["layer_id"])
            if key in entity_layer:
                raise ValueError("entity_id/layer_id is duplicated")
            entity_layer.add(key)
            status = row["terminal_state"]
            if status not in ALLOWED_TERMINAL_STATES:
                raise ValueError(f"invalid terminal_state {status!r}")
            if row["gate_status"] not in ALLOWED_GATE_STATUS:
                raise ValueError(f"invalid gate_status {row['gate_status']!r}")
            quality = _float(row["quality_multiplier"], "quality_multiplier", False)
            if quality is None or not 0 <= quality <= 1:
                raise ValueError("quality_multiplier must be in [0,1]")
            n_units = _int(row["n_independent_units"], "n_independent_units", False)
            if n_units is None or n_units < 0:
                raise ValueError("n_independent_units must be >=0")
            if not SHA_RE.fullmatch(row["input_sha256"]):
                raise ValueError("input_sha256 is required and must be 64 lowercase hex")
            if not SHA_RE.fullmatch(row["config_sha256"]):
                raise ValueError("config_sha256 is required and must be 64 lowercase hex")
            effect = _float(row["effect"], "effect")
            direction = _int(row["direction"], "direction")
            if status == "OBSERVED":
                if effect is None or direction not in {-1, 0, 1}:
                    raise ValueError("OBSERVED requires finite effect and direction -1/0/1")
            elif effect is not None or direction is not None:
                raise ValueError("non-OBSERVED records cannot carry effect or direction")
            for field in ["P", "FDR"]:
                value = _float(row[field], field)
                if value is not None and not 0 <= value <= 1:
                    raise ValueError(f"{field} must be in [0,1]")
            _float(row["SE"], "SE")
        except (KeyError, ValueError) as exc:
            errors.append(f"{label}: {exc}")

    entity_ids: set[str] = set()
    for index, row in enumerate(entities, start=2):
        try:
            entity_id = row["entity_id"]
            if not entity_id or entity_id in entity_ids:
                raise ValueError("entity_id is blank or duplicated")
            entity_ids.add(entity_id)
            target = row["target_direction"]
            if target not in {"AUTO", "-1", "0", "1"}:
                raise ValueError("target_direction must be AUTO or -1/0/1")
        except (KeyError, ValueError) as exc:
            errors.append(f"entities row {index}: {exc}")

    layer_ids: set[str] = set()
    for index, row in enumerate(layers, start=2):
        try:
            layer = row["layer_id"]
            if not layer or layer in layer_ids:
                raise ValueError("layer_id is blank or duplicated")
            layer_ids.add(layer)
            if row["requirement"] not in ALLOWED_REQUIREMENTS:
                raise ValueError("invalid requirement")
            weight = _float(row["weight"], "weight", False)
            if weight is None or weight <= 0:
                raise ValueError("weight must be >0")
            rule = row["conditional_rule"].strip()
            if rule == "when_available" and row["requirement"] != "optional":
                raise ValueError("when_available is allowed only for optional layers")
            if rule not in {"always", "when_available"} and not CONDITION_FLAG_RE.fullmatch(rule):
                raise ValueError("conditional_rule must be always, when_available, or flag:<name>")
        except (KeyError, ValueError) as exc:
            errors.append(f"layers row {index}: {exc}")

    layer_index = {row.get("layer_id", ""): row for row in layers}

    unknown_evidence_entities = sorted({r.get("entity_id", "") for r in evidence} - entity_ids)
    unknown_evidence_layers = sorted({r.get("layer_id", "") for r in evidence} - layer_ids)
    if unknown_evidence_entities:
        errors.append(f"evidence: unknown entities {unknown_evidence_entities}")
    if unknown_evidence_layers:
        errors.append(f"evidence: unknown layers {unknown_evidence_layers}")
    for row in entities:
        if row.get("construction_layer_id") not in layer_ids:
            errors.append(
                f"entity {row.get('entity_id')}: unknown construction_layer_id "
                f"{row.get('construction_layer_id')!r}"
            )
        elif layer_index[row["construction_layer_id"]]["requirement"] == "optional":
            errors.append(
                f"entity {row.get('entity_id')}: construction_layer_id must be critical or required"
            )

    if not missing_config:
        for field in ["V_min", "S_min", "K_max", "discovery_fdr_max"]:
            value = float(config[field])
            if not 0 <= value <= 1:
                errors.append(f"config: {field} must be in [0,1]")
        if int(config["min_independent_units"]) < 1:
            errors.append("config: min_independent_units must be >=1")
        if not isinstance(config["condition_flags"], dict):
            errors.append("config: condition_flags must be an object")
        else:
            for key, value in config["condition_flags"].items():
                if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", str(key)) or not isinstance(value, bool):
                    errors.append("config: condition_flags must map valid names to booleans")
                    break
            referenced_flags = {
                match.group(1)
                for row in layers
                if (match := CONDITION_FLAG_RE.fullmatch(row.get("conditional_rule", "").strip()))
            }
            missing_flags = sorted(referenced_flags - set(config["condition_flags"]))
            if missing_flags:
                errors.append(f"config: condition_flags missing referenced names {missing_flags}")
        if not isinstance(config["stability_layer_ids"], list):
            errors.append("config: stability_layer_ids must be a list")
        else:
            unknown = sorted(set(config["stability_layer_ids"]) - layer_ids)
            if unknown:
                errors.append(f"config: unknown stability layers {unknown}")

        if isinstance(config["condition_flags"], dict):
            for row in entities:
                construction = layer_index.get(row["construction_layer_id"])
                if construction is not None:
                    try:
                        if not condition_is_active(construction["conditional_rule"], config):
                            errors.append(
                                f"entity {row['entity_id']}: construction layer condition is inactive"
                            )
                    except (KeyError, ValueError):
                        pass
            for row in evidence:
                layer = layer_index.get(row.get("layer_id", ""))
                if layer is None:
                    continue
                try:
                    active = condition_is_active(layer["conditional_rule"], config)
                except (KeyError, ValueError):
                    continue
                if not active and row.get("terminal_state") != "NOT_APPLICABLE":
                    errors.append(
                        f"evidence row {row.get('record_id')}: inactive layer must be NOT_APPLICABLE"
                    )

    if errors:
        return [{"status": "FAIL", "code": "INPUT_VALIDATION_ERROR", "detail": error} for error in errors]
    return [{"status": "PASS", "code": "INPUTS_VALID", "detail": "all contracts satisfied"}]


def assert_valid(validation_rows: list[dict[str, str]]) -> None:
    failures = [row["detail"] for row in validation_rows if row["status"] != "PASS"]
    if failures:
        raise ValueError("; ".join(failures))
