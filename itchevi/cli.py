from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess

from . import __version__
from .api import qualify, validate_inputs
from .config import load_config, validate_config
from .contracts import audit_contracts
from .demo import run_demo
from .jsonio import normalize_inputs


def run_stage(config: dict, stage: str) -> int:
    """Legacy Phase 5F external-script runner retained for audit compatibility."""
    phase_root = Path(config["phase_root"])
    script = Path(config["scripts"][stage])
    if stage == "read":
        command = [config["python"], str(script), str(phase_root)]
    elif stage == "edger":
        command = [
            config["rscript"],
            str(script),
            str(phase_root / "05_pseudobulk/GSE328048_donor_condition_pseudobulk_counts.tsv.gz"),
            str(phase_root / "05_pseudobulk/GSE328048_donor_condition_metadata.tsv"),
            str(phase_root / "05_pseudobulk"),
        ]
    elif stage == "score":
        command = [config["python"], str(script), str(phase_root)]
    else:
        raise ValueError(f"Unsupported stage: {stage}")
    return subprocess.run(command, check=False).returncode


def _qualification_args(parser: argparse.ArgumentParser, include_output: bool) -> None:
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--entities", required=True, type=Path)
    parser.add_argument("--layers", required=True, type=Path)
    parser.add_argument("--config", required=True, type=Path)
    if include_output:
        parser.add_argument("--output", required=True, type=Path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="itchevi")
    parser.add_argument("--version", action="version", version=f"itchevi {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="validate qualification inputs")
    _qualification_args(validate, include_output=False)
    qualify_parser = subparsers.add_parser("qualify", help="run Algorithm 1")
    _qualification_args(qualify_parser, include_output=True)
    normalize_parser = subparsers.add_parser(
        "normalize", help="convert TSV inputs to schema-validated JSON"
    )
    _qualification_args(normalize_parser, include_output=True)

    demo = subparsers.add_parser("demo", help="run deterministic end-to-end demo")
    demo.add_argument("--workdir", required=True, type=Path)
    smoke = subparsers.add_parser("smoke", help="run legacy Cell Ranger reader smoke test")
    smoke.add_argument("--workdir", required=True, type=Path)

    audit = subparsers.add_parser("audit", help="audit frozen-result contracts")
    audit.add_argument("--config", required=True, type=Path)
    audit.add_argument("--output", required=False, type=Path)
    legacy_validate = subparsers.add_parser("validate-legacy", help="validate Phase 5F stage config")
    legacy_validate.add_argument("--config", required=True, type=Path)
    for command in ["read", "edger", "score"]:
        child = subparsers.add_parser(command, help=f"legacy external-script stage: {command}")
        child.add_argument("--config", required=True, type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "validate":
        rows = validate_inputs(args.evidence, args.entities, args.layers, args.config)
        print(json.dumps(rows, indent=2))
        return 0 if all(row["status"] == "PASS" for row in rows) else 2
    if args.command == "qualify":
        try:
            run = qualify(
                args.evidence,
                args.entities,
                args.layers,
                args.config,
                args.output,
                entry_point="cli:qualify",
            )
        except Exception as exc:
            print(json.dumps({"status": "FAIL", "error": f"{type(exc).__name__}: {exc}"}, indent=2))
            return 3
        print(json.dumps({"status": "PASS", "output": str(args.output.resolve()), "summary": run.summary}, indent=2))
        return 0
    if args.command == "normalize":
        try:
            manifest = normalize_inputs(
                args.evidence,
                args.entities,
                args.layers,
                args.config,
                args.output,
                entry_point="cli:normalize",
            )
        except Exception as exc:
            print(json.dumps({"status": "FAIL", "error": f"{type(exc).__name__}: {exc}"}, indent=2))
            return 8
        print(json.dumps(manifest, indent=2))
        return 0
    if args.command == "demo":
        result = run_demo(args.workdir, entry_point="cli:demo")
        print(json.dumps(result, indent=2))
        return 0 if result["status"] == "PASS" else 4
    if args.command == "smoke":
        from .smoke import run_smoke

        result = run_smoke(args.workdir)
        print(json.dumps(result, indent=2))
        return 0 if result["status"] == "PASS" else 5
    config = load_config(args.config)
    if args.command == "validate-legacy":
        rows = validate_config(config)
        print(json.dumps(rows, indent=2))
        return 0 if all(row["exists"] for row in rows) else 6
    if args.command == "audit":
        rows = audit_contracts(config)
        text = json.dumps(rows, indent=2)
        print(text)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(text + "\n", encoding="utf-8")
        return 0 if all(row["status"] == "PASS" for row in rows) else 7
    return run_stage(config, args.command)


if __name__ == "__main__":
    raise SystemExit(main())
