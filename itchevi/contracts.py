from __future__ import annotations

import csv
import gzip
import hashlib
import json
from pathlib import Path
from typing import Any


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _open_text(path: Path):
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8", newline="")
    return path.open("r", encoding="utf-8", newline="")


def _nested_get(payload: dict[str, Any], dotted_key: str) -> Any:
    current: Any = payload
    for part in dotted_key.split("."):
        if not isinstance(current, dict) or part not in current:
            raise KeyError(dotted_key)
        current = current[part]
    return current


def audit_contract(module: str, contract: dict[str, Any]) -> dict[str, Any]:
    path = Path(contract["path"])
    row: dict[str, Any] = {
        "module": module,
        "path": str(path.resolve(strict=False)),
        "format": contract["format"],
        "exists": path.is_file(),
        "status": "FAIL",
        "reason": "",
        "rows": None,
        "sha256": None,
    }
    if not path.is_file():
        row["reason"] = "FILE_MISSING"
        return row
    row["sha256"] = sha256(path)
    try:
        if contract["format"] == "json":
            payload = json.loads(path.read_text(encoding="utf-8"))
            for key, expected in contract.get("expected", {}).items():
                observed = _nested_get(payload, key)
                if observed != expected:
                    raise AssertionError(
                        f"{key}: expected {expected!r}, observed {observed!r}"
                    )
        elif contract["format"] == "tsv":
            with _open_text(path) as handle:
                reader = csv.DictReader(handle, delimiter="\t")
                columns = reader.fieldnames or []
                missing = sorted(set(contract.get("required_columns", [])) - set(columns))
                if missing:
                    raise AssertionError(f"missing columns: {missing}")
                row_count = sum(1 for _ in reader)
            row["rows"] = row_count
            minimum = int(contract.get("min_rows", 0))
            if row_count < minimum:
                raise AssertionError(f"rows {row_count} < required {minimum}")
        else:
            raise ValueError(f"unsupported format: {contract['format']}")
    except Exception as exc:
        row["reason"] = f"{type(exc).__name__}: {exc}"
        return row
    row["status"] = "PASS"
    row["reason"] = "CONTRACT_SATISFIED"
    return row


def audit_contracts(config: dict[str, Any]) -> list[dict[str, Any]]:
    results = []
    for module, contracts in config["contracts"].items():
        for contract in contracts:
            results.append(audit_contract(module, contract))
    return results
