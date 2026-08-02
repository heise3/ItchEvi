from __future__ import annotations

import json
from pathlib import Path


STAGE_REQUIRED_KEYS = {
    "phase_root",
    "data_root",
    "python",
    "rscript",
    "scripts",
    "inputs",
}


def load_config(path: Path) -> dict:
    config = json.loads(path.read_text(encoding="utf-8"))
    mode = config.get("mode", "stage")
    if mode == "stage":
        missing = sorted(STAGE_REQUIRED_KEYS - set(config))
        if missing:
            raise ValueError(f"Missing configuration keys: {missing}")
    elif mode == "frozen_contract_audit":
        if not isinstance(config.get("contracts"), dict) or not config["contracts"]:
            raise ValueError("frozen_contract_audit requires a non-empty contracts object")
    else:
        raise ValueError(f"Unsupported configuration mode: {mode}")
    return config


def validate_config(config: dict) -> list[dict[str, object]]:
    rows = []
    if config.get("mode") == "frozen_contract_audit":
        for module, contracts in config["contracts"].items():
            for index, contract in enumerate(contracts, start=1):
                path = Path(contract["path"])
                rows.append(
                    {
                        "input_id": f"{module}:{index}",
                        "absolute_path": str(path.resolve(strict=False)),
                        "exists": path.is_file(),
                    }
                )
        return rows
    for key, value in config["inputs"].items():
        path = Path(value)
        rows.append(
            {
                "input_id": key,
                "absolute_path": str(path.resolve(strict=False)),
                "exists": path.is_file(),
            }
        )
    for key, value in config["scripts"].items():
        path = Path(value)
        rows.append(
            {
                "input_id": f"script:{key}",
                "absolute_path": str(path.resolve(strict=False)),
                "exists": path.is_file(),
            }
        )
    return rows
