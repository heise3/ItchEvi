from __future__ import annotations

from collections import Counter
import hashlib
from typing import Any

from .models import QualificationRun
from .validation import assert_valid, condition_is_active, validate_objects


def _as_float(value: str) -> float | None:
    return None if value in {"", None} else float(value)  # type: ignore[comparison-overlap]


def _as_int(value: str) -> int | None:
    number = _as_float(value)
    return None if number is None else int(number)


def _aggregate_sha(values: list[str], fallback: str) -> str:
    eligible = sorted({value for value in values if value})
    payload = "|".join(eligible).encode("utf-8") if eligible else fallback.encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _synthetic_record(
    entity_id: str,
    layer_id: str,
    state: str,
    input_sha256: str,
    config_sha256: str,
) -> dict[str, str]:
    missing = state == "MISSING"
    return {
        "record_id": f"SYNTH_{state}::{entity_id}::{layer_id}",
        "entity_id": entity_id,
        "layer_id": layer_id,
        "dataset_id": "UNAVAILABLE",
        "evidence_role": "evaluation",
        "statistical_unit": "not available",
        "paired_or_descriptive": "descriptive",
        "effect": "",
        "SE": "",
        "P": "",
        "FDR": "",
        "direction": "",
        "n_independent_units": "0",
        "quality_multiplier": "0",
        "terminal_state": state,
        "failure_code": "UNSCHEDULED_RECORD" if missing else "CONDITION_NOT_ACTIVE",
        "source_confidence": "unresolved",
        "input_sha256": input_sha256,
        "config_sha256": config_sha256,
        "software_version": "itchevi-core",
        "gate_status": "NOT_TESTED",
    }


def qualify_records(
    evidence: list[dict[str, str]],
    entities: list[dict[str, str]],
    layers: list[dict[str, str]],
    config: dict[str, Any],
) -> QualificationRun:
    validation = validate_objects(evidence, entities, layers, config)
    assert_valid(validation)
    evidence_index = {(row["entity_id"], row["layer_id"]): dict(row) for row in evidence}
    evidence_by_entity: dict[str, list[dict[str, str]]] = {}
    for row in evidence:
        evidence_by_entity.setdefault(row["entity_id"], []).append(row)
    ledger: list[dict[str, Any]] = []
    outputs: list[dict[str, Any]] = []

    for entity in entities:
        entity_id = entity["entity_id"]
        entity_records = evidence_by_entity.get(entity_id, [])
        synthetic_input_sha = _aggregate_sha(
            [row["input_sha256"] for row in entity_records], f"{entity_id}:input"
        )
        synthetic_config_sha = _aggregate_sha(
            [row["config_sha256"] for row in entity_records], f"{entity_id}:config"
        )
        resolved: dict[str, dict[str, str]] = {}
        active_by_layer: dict[str, bool] = {}
        for layer in layers:
            layer_id = layer["layer_id"]
            condition_active = condition_is_active(layer["conditional_rule"], config)
            active_by_layer[layer_id] = condition_active
            fallback_state = "MISSING" if condition_active else "NOT_APPLICABLE"
            record = evidence_index.get(
                (entity_id, layer_id),
                _synthetic_record(
                    entity_id,
                    layer_id,
                    fallback_state,
                    synthetic_input_sha,
                    synthetic_config_sha,
                ),
            )
            resolved[layer_id] = record
            ledger.append(
                {
                    "entity_id": entity_id,
                    "layer_id": layer_id,
                    "requirement": layer["requirement"],
                    "conditional_rule": layer["conditional_rule"],
                    "condition_active": condition_active,
                    "layer_weight": float(layer["weight"]),
                    "record_id": record["record_id"],
                    "dataset_id": record["dataset_id"],
                    "evidence_role": record["evidence_role"],
                    "statistical_unit": record["statistical_unit"],
                    "paired_or_descriptive": record["paired_or_descriptive"],
                    "n_independent_units": _as_int(record["n_independent_units"]) or 0,
                    "quality_multiplier": float(record["quality_multiplier"]),
                    "terminal_state": record["terminal_state"],
                    "failure_code": record["failure_code"],
                    "gate_status": record["gate_status"],
                    "source_confidence": record["source_confidence"],
                    "input_sha256": record["input_sha256"],
                    "config_sha256": record["config_sha256"],
                    "software_version": record["software_version"],
                    "synthetic_missing_receipt": record["record_id"].startswith("SYNTH_MISSING::"),
                    "synthetic_not_applicable_receipt": record["record_id"].startswith(
                        "SYNTH_NOT_APPLICABLE::"
                    ),
                }
            )

        construction = resolved[entity["construction_layer_id"]]
        target_direction = (
            _as_int(construction["direction"])
            if entity["target_direction"] == "AUTO"
            else int(entity["target_direction"])
        )
        required_layers = [
            row
            for row in layers
            if row["requirement"] in {"critical", "required"}
            and active_by_layer[row["layer_id"]]
        ]
        critical_layers = [
            row
            for row in layers
            if row["requirement"] == "critical" and active_by_layer[row["layer_id"]]
        ]
        optional_layers = [
            row
            for row in layers
            if row["requirement"] == "optional" and active_by_layer[row["layer_id"]]
        ]
        boundaries: list[str] = []

        total_required_weight = sum(float(row["weight"]) for row in required_layers)
        observed_required_weight = sum(
            float(row["weight"])
            for row in required_layers
            if resolved[row["layer_id"]]["terminal_state"] == "OBSERVED"
        )
        coverage = observed_required_weight / total_required_weight if total_required_weight else 1.0

        observed = [
            (row, resolved[row["layer_id"]])
            for row in required_layers
            if resolved[row["layer_id"]]["terminal_state"] == "OBSERVED"
        ]
        denominator = sum(float(layer["weight"]) * float(record["quality_multiplier"]) for layer, record in observed)
        concordant = sum(
            float(layer["weight"]) * float(record["quality_multiplier"])
            for layer, record in observed
            if target_direction is not None and _as_int(record["direction"]) == target_direction
        )
        discordant = sum(
            float(layer["weight"]) * float(record["quality_multiplier"])
            for layer, record in observed
            if target_direction is not None
            and _as_int(record["direction"]) == -target_direction
            and target_direction != 0
        )
        support = concordant / denominator if denominator else None
        conflict = discordant / denominator if denominator else None

        critical_failed = [
            row["layer_id"]
            for row in critical_layers
            if resolved[row["layer_id"]]["terminal_state"] == "FAILED"
        ]
        critical_missing = [
            row["layer_id"]
            for row in critical_layers
            if resolved[row["layer_id"]]["terminal_state"] == "MISSING"
        ]
        critical_na = [
            row["layer_id"]
            for row in critical_layers
            if resolved[row["layer_id"]]["terminal_state"] == "NOT_APPLICABLE"
        ]
        discovery_fdr = _as_float(construction["FDR"])
        discovery_units = _as_int(construction["n_independent_units"])
        discovery_pass = bool(
            construction["terminal_state"] == "OBSERVED"
            and discovery_units is not None
            and discovery_units >= int(config["min_independent_units"])
            and discovery_fdr is not None
            and discovery_fdr <= float(config["discovery_fdr_max"])
        )
        insufficient_required_units = [
            row["layer_id"]
            for row in required_layers
            if row["layer_id"] != entity["construction_layer_id"]
            and resolved[row["layer_id"]]["terminal_state"] == "OBSERVED"
            and (_as_int(resolved[row["layer_id"]]["n_independent_units"]) or 0)
            < int(config["min_independent_units"])
        ]
        stability_failures = [
            layer_id
            for layer_id in config["stability_layer_ids"]
            if resolved[layer_id]["terminal_state"] == "OBSERVED"
            and resolved[layer_id]["gate_status"] == "FAIL"
        ]
        stability_weak = [
            layer_id
            for layer_id in config["stability_layer_ids"]
            if resolved[layer_id]["terminal_state"] == "OBSERVED"
            and resolved[layer_id]["gate_status"] in {"WEAK", "NOT_TESTED", ""}
        ]
        if stability_weak:
            boundaries.append("WEAK_STABILITY:" + "|".join(stability_weak))
        if bool(config["boundary_on_optional_missing"]):
            for layer in optional_layers:
                state = resolved[layer["layer_id"]]["terminal_state"]
                if state != "OBSERVED":
                    boundaries.append(f"OPTIONAL_{state}:{layer['layer_id']}")
                elif resolved[layer["layer_id"]]["gate_status"] in {"WEAK", "FAIL", "NOT_TESTED", ""}:
                    boundaries.append(f"OPTIONAL_WEAK:{layer['layer_id']}")

        if critical_failed:
            final_class, terminal_code = "NOT_QUALIFIED", "NOT_QUALIFIED_EXECUTION_FAILURE"
            boundaries.append("CRITICAL_FAILED:" + "|".join(critical_failed))
        elif critical_missing:
            final_class, terminal_code = "ABSTAIN", "ABSTAIN_INSUFFICIENT_EVIDENCE"
            boundaries.append("CRITICAL_MISSING:" + "|".join(critical_missing))
        elif critical_na:
            final_class, terminal_code = "NOT_QUALIFIED", "NOT_QUALIFIED_CONFIGURATION_ERROR"
            boundaries.append("CRITICAL_NOT_APPLICABLE:" + "|".join(critical_na))
        elif target_direction is None:
            final_class, terminal_code = "ABSTAIN", "ABSTAIN_DIRECTION_UNDEFINED"
        elif not discovery_pass:
            final_class, terminal_code = "NOT_QUALIFIED", "NOT_QUALIFIED_DISCOVERY_GATE"
        elif insufficient_required_units:
            final_class, terminal_code = "ABSTAIN", "ABSTAIN_INSUFFICIENT_EVIDENCE"
            boundaries.append("INSUFFICIENT_INDEPENDENT_UNITS:" + "|".join(insufficient_required_units))
        elif coverage < float(config["V_min"]):
            final_class, terminal_code = "ABSTAIN", "ABSTAIN_INSUFFICIENT_EVIDENCE"
        elif stability_failures:
            final_class, terminal_code = "DESCRIPTIVE_ONLY", "DESCRIPTIVE_ONLY_UNSTABLE"
            boundaries.append("STABILITY_FAILED:" + "|".join(stability_failures))
        elif support is None or conflict is None:
            final_class, terminal_code = "ABSTAIN", "ABSTAIN_DIRECTION_UNDEFINED"
        elif support < float(config["S_min"]) or conflict > float(config["K_max"]):
            final_class, terminal_code = "DESCRIPTIVE_ONLY", "DESCRIPTIVE_ONLY_CONFLICTED"
        elif boundaries:
            final_class, terminal_code = "QUALIFIED_WITH_BOUNDARY", "QUALIFIED_WITH_BOUNDARY"
        else:
            final_class, terminal_code = "QUALIFIED", "QUALIFIED"

        outputs.append(
            {
                "entity_id": entity_id,
                "claim_id": entity["claim_id"],
                "claim_text": entity["claim_text"],
                "target_direction": target_direction if target_direction is not None else "",
                "support": support if support is not None else "",
                "conflict": conflict if conflict is not None else "",
                "coverage": coverage,
                "discovery_gate_pass": discovery_pass,
                "final_class": final_class,
                "terminal_code": terminal_code,
                "boundary_codes": ";".join(boundaries),
            }
        )

    summary = {
        "run_id": config["run_id"],
        "entity_count": len(outputs),
        "terminal_record_count": len(ledger),
        "class_counts": dict(Counter(row["final_class"] for row in outputs)),
        "synthesized_missing_records": sum(bool(row["synthetic_missing_receipt"]) for row in ledger),
    }
    return QualificationRun(outputs, ledger, validation, summary)
