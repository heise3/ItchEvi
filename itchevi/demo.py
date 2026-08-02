from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

from .api import qualify


ZERO_SHA = hashlib.sha256(b"synthetic-itchevi-demo").hexdigest()


def _write_tsv(path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def write_demo_inputs(root: Path) -> dict[str, Path]:
    root.mkdir(parents=True, exist_ok=True)
    evidence_fields = [
        "record_id", "entity_id", "layer_id", "dataset_id", "evidence_role",
        "statistical_unit", "paired_or_descriptive", "effect", "SE", "P", "FDR",
        "direction", "n_independent_units", "quality_multiplier", "terminal_state",
        "failure_code", "source_confidence", "input_sha256", "config_sha256",
        "software_version", "gate_status",
    ]
    evidence = [
        {"record_id": "R1", "entity_id": "P_SYN", "layer_id": "discovery_paired", "dataset_id": "SYN_D1", "evidence_role": "construction", "statistical_unit": "paired donor", "paired_or_descriptive": "paired_inferential", "effect": 1.2, "SE": 0.2, "P": 0.001, "FDR": 0.01, "direction": 1, "n_independent_units": 10, "quality_multiplier": 1.0, "terminal_state": "OBSERVED", "failure_code": "", "source_confidence": "high", "input_sha256": ZERO_SHA, "config_sha256": ZERO_SHA, "software_version": "synthetic", "gate_status": "PASS"},
        {"record_id": "R2", "entity_id": "P_SYN", "layer_id": "external_direction", "dataset_id": "SYN_D2", "evidence_role": "evaluation", "statistical_unit": "paired donor", "paired_or_descriptive": "paired_inferential", "effect": 0.8, "SE": 0.3, "P": 0.02, "FDR": 0.04, "direction": 1, "n_independent_units": 12, "quality_multiplier": 0.8, "terminal_state": "OBSERVED", "failure_code": "", "source_confidence": "high", "input_sha256": ZERO_SHA, "config_sha256": ZERO_SHA, "software_version": "synthetic", "gate_status": "PASS"},
        {"record_id": "R3", "entity_id": "P_SYN", "layer_id": "operator_stability", "dataset_id": "SYN_D1", "evidence_role": "evaluation", "statistical_unit": "donor holdout", "paired_or_descriptive": "paired_inferential", "effect": -0.2, "SE": 0.1, "P": 0.2, "FDR": 0.3, "direction": -1, "n_independent_units": 10, "quality_multiplier": 0.6, "terminal_state": "OBSERVED", "failure_code": "", "source_confidence": "high", "input_sha256": ZERO_SHA, "config_sha256": ZERO_SHA, "software_version": "synthetic", "gate_status": "PASS"},
        {"record_id": "R4", "entity_id": "P_SYN", "layer_id": "spatial_context", "dataset_id": "SYN_SPATIAL", "evidence_role": "optional_context", "statistical_unit": "section", "paired_or_descriptive": "descriptive", "effect": "", "SE": "", "P": "", "FDR": "", "direction": "", "n_independent_units": 0, "quality_multiplier": 0.0, "terminal_state": "MISSING", "failure_code": "INPUT_NOT_AVAILABLE", "source_confidence": "unresolved", "input_sha256": ZERO_SHA, "config_sha256": ZERO_SHA, "software_version": "synthetic", "gate_status": "NOT_TESTED"},
    ]
    layers = [
        {"layer_id": "discovery_paired", "requirement": "critical", "weight": 1.0, "conditional_rule": "always"},
        {"layer_id": "external_direction", "requirement": "required", "weight": 1.0, "conditional_rule": "always"},
        {"layer_id": "operator_stability", "requirement": "required", "weight": 1.0, "conditional_rule": "always"},
        {"layer_id": "spatial_context", "requirement": "optional", "weight": 1.0, "conditional_rule": "when_available"},
    ]
    entities = [{"entity_id": "P_SYN", "claim_id": "C_SYN", "claim_text": "Synthetic directional program", "construction_layer_id": "discovery_paired", "target_direction": "AUTO"}]
    config = {"run_id": "synthetic_worked_example", "V_min": 0.8, "S_min": 0.7, "K_max": 0.3, "min_independent_units": 6, "discovery_fdr_max": 0.05, "stability_layer_ids": ["operator_stability"], "boundary_on_optional_missing": True}
    evidence_path = root / "evidence.tsv"
    entities_path = root / "entities.tsv"
    layers_path = root / "layers.tsv"
    config_path = root / "qualification_config.json"
    _write_tsv(evidence_path, evidence_fields, evidence)
    _write_tsv(entities_path, list(entities[0]), entities)
    _write_tsv(layers_path, list(layers[0]), layers)
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    return {"evidence": evidence_path, "entities": entities_path, "layers": layers_path, "config": config_path}


def run_demo(workdir: Path, *, entry_point: str = "python_api:demo") -> dict[str, object]:
    inputs = write_demo_inputs(workdir / "inputs")
    output = workdir / "results"
    run = qualify(
        inputs["evidence"],
        inputs["entities"],
        inputs["layers"],
        inputs["config"],
        output,
        entry_point=entry_point,
    )
    row = run.qualification_rows[0]
    passed = (
        row["final_class"] == "QUALIFIED_WITH_BOUNDARY"
        and abs(float(row["support"]) - 0.75) < 1e-12
        and abs(float(row["conflict"]) - 0.25) < 1e-12
        and abs(float(row["coverage"]) - 1.0) < 1e-12
    )
    return {"status": "PASS" if passed else "FAIL", "workdir": str(workdir.resolve()), "qualification": row, "summary": run.summary}
