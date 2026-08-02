from __future__ import annotations

import csv
import hashlib
import importlib.metadata
import json
import platform
import time
import tracemalloc
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import __version__
from .core import qualify_records
from .models import QualificationRun
from .report import render_report, write_report
from .validation import read_json, read_tsv, validate_objects


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_inputs(
    evidence_path: Path,
    entities_path: Path,
    layers_path: Path,
    config_path: Path,
) -> list[dict[str, str]]:
    return validate_objects(
        read_tsv(evidence_path),
        read_tsv(entities_path),
        read_tsv(layers_path),
        read_json(config_path),
    )


def _write_tsv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError(f"Refusing to write empty table without schema: {path}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def _environment_snapshot() -> tuple[dict[str, Any], str]:
    packages: dict[str, str] = {}
    for name in ["itchevi", "numpy", "pandas", "scipy", "jsonschema"]:
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = "NOT_INSTALLED"
    snapshot = {
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "packages": packages,
    }
    payload = json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return snapshot, hashlib.sha256(payload).hexdigest()


def _safe_input_hashes(paths: list[Path]) -> dict[str, str]:
    return {str(path.name): sha256(path) if path.is_file() else "MISSING" for path in paths}


def qualify(
    evidence_path: Path,
    entities_path: Path,
    layers_path: Path,
    config_path: Path,
    output_dir: Path | None = None,
    *,
    entry_point: str = "python_api",
    random_seed: int | None = None,
    parallelism: int = 1,
    retry_count: int = 0,
    checkpoint_id: str = "",
) -> QualificationRun:
    started_utc = datetime.now(timezone.utc)
    started_perf = time.perf_counter()
    tracemalloc.start()
    config: dict[str, Any] = {}
    input_paths = [evidence_path, entities_path, layers_path, config_path]
    environment, environment_hash = _environment_snapshot()
    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
    try:
        config = read_json(config_path)
        run = qualify_records(
            read_tsv(evidence_path),
            read_tsv(entities_path),
            read_tsv(layers_path),
            config,
        )
        if output_dir is None:
            return run
        qualification_path = output_dir / "qualification.tsv"
        ledger_path = output_dir / "terminal_ledger.tsv"
        validation_path = output_dir / "validation.tsv"
        report_path = output_dir / "qualification_report.md"
        _write_tsv(qualification_path, run.qualification_rows)
        _write_tsv(ledger_path, run.terminal_ledger)
        _write_tsv(validation_path, run.validation_rows)
        write_report(
            report_path,
            render_report(run.qualification_rows, run.terminal_ledger, str(config["run_id"])),
        )
        _, peak_bytes = tracemalloc.get_traced_memory()
        finished_utc = datetime.now(timezone.utc)
        manifest = {
            "run_id": config["run_id"],
            "status": "PASS",
            "exit_status": 0,
            "failure_code": "",
            "itchevi_version": __version__,
            "started_utc": started_utc.isoformat(),
            "finished_utc": finished_utc.isoformat(),
            "wall_time_seconds": time.perf_counter() - started_perf,
            "python_tracemalloc_peak_bytes": peak_bytes,
            "entry_point": entry_point,
            "random_seed": random_seed,
            "parallelism": parallelism,
            "retry_count": retry_count,
            "checkpoint_id": checkpoint_id,
            "environment": environment,
            "environment_fingerprint_sha256": environment_hash,
            "inputs": _safe_input_hashes(input_paths),
            "outputs": {
                str(path.name): sha256(path)
                for path in [qualification_path, ledger_path, validation_path, report_path]
            },
            "summary": run.summary,
        }
        (output_dir / "run_manifest.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
        return run
    except Exception as exc:
        if output_dir is not None:
            _, peak_bytes = tracemalloc.get_traced_memory()
            failure_manifest = {
                "run_id": config.get("run_id", "UNRESOLVED"),
                "status": "FAILED",
                "exit_status": 1,
                "failure_code": type(exc).__name__,
                "failure_detail": str(exc),
                "itchevi_version": __version__,
                "started_utc": started_utc.isoformat(),
                "finished_utc": datetime.now(timezone.utc).isoformat(),
                "wall_time_seconds": time.perf_counter() - started_perf,
                "python_tracemalloc_peak_bytes": peak_bytes,
                "entry_point": entry_point,
                "random_seed": random_seed,
                "parallelism": parallelism,
                "retry_count": retry_count,
                "checkpoint_id": checkpoint_id,
                "environment": environment,
                "environment_fingerprint_sha256": environment_hash,
                "inputs": _safe_input_hashes(input_paths),
                "outputs": {},
            }
            (output_dir / "run_manifest.json").write_text(
                json.dumps(failure_manifest, indent=2) + "\n", encoding="utf-8"
            )
        raise
    finally:
        tracemalloc.stop()
