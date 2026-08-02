import csv
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from itchevi.api import qualify
from itchevi.demo import run_demo, write_demo_inputs
import itchevi
from jsonschema.validators import validator_for


def _validate_json_schema(name, payload):
    schema_path = Path(itchevi.__file__).resolve().parent / "schemas" / name
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator_for(schema)(schema).validate(payload)


class CliApiTest(unittest.TestCase):
    def test_api_writes_complete_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = write_demo_inputs(root / "inputs")
            output = root / "api_output"
            run = qualify(paths["evidence"], paths["entities"], paths["layers"], paths["config"], output)
            self.assertEqual(run.qualification_rows[0]["final_class"], "QUALIFIED_WITH_BOUNDARY")
            for name in ["qualification.tsv", "terminal_ledger.tsv", "validation.tsv", "qualification_report.md", "run_manifest.json"]:
                self.assertTrue((output / name).is_file(), name)
            manifest = json.loads((output / "run_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["status"], "PASS")
            self.assertEqual(len(manifest["outputs"]), 4)
            self.assertEqual(manifest["entry_point"], "python_api")
            self.assertGreaterEqual(manifest["wall_time_seconds"], 0)
            self.assertGreater(manifest["python_tracemalloc_peak_bytes"], 0)
            self.assertEqual(len(manifest["environment_fingerprint_sha256"]), 64)
            self.assertEqual(manifest["retry_count"], 0)
            _validate_json_schema("qualification_output.schema.json", run.qualification_rows)
            _validate_json_schema("terminal_ledger.schema.json", run.terminal_ledger)
            _validate_json_schema("run_manifest.schema.json", manifest)

    def test_failed_validation_writes_failure_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = write_demo_inputs(root / "inputs")
            with paths["evidence"].open("r", encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle, delimiter="\t"))
            rows[-1]["effect"] = "1.0"
            with paths["evidence"].open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0]), delimiter="\t")
                writer.writeheader()
                writer.writerows(rows)
            output = root / "failed_output"
            with self.assertRaises(ValueError):
                qualify(paths["evidence"], paths["entities"], paths["layers"], paths["config"], output)
            manifest = json.loads((output / "run_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["status"], "FAILED")
            self.assertEqual(manifest["exit_status"], 1)
            self.assertEqual(manifest["failure_code"], "ValueError")
            self.assertEqual(manifest["outputs"], {})
            _validate_json_schema("run_manifest.schema.json", manifest)

    def test_cli_and_api_are_semantically_equivalent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = write_demo_inputs(root / "inputs")
            api_output = root / "api"
            cli_output = root / "cli"
            qualify(paths["evidence"], paths["entities"], paths["layers"], paths["config"], api_output)
            command = [
                sys.executable, "-m", "itchevi.cli", "qualify",
                "--evidence", str(paths["evidence"]),
                "--entities", str(paths["entities"]),
                "--layers", str(paths["layers"]),
                "--config", str(paths["config"]),
                "--output", str(cli_output),
            ]
            completed = subprocess.run(command, check=False, capture_output=True, text=True)
            self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
            self.assertEqual(
                (api_output / "qualification.tsv").read_text(encoding="utf-8"),
                (cli_output / "qualification.tsv").read_text(encoding="utf-8"),
            )
            self.assertEqual(
                (api_output / "terminal_ledger.tsv").read_text(encoding="utf-8"),
                (cli_output / "terminal_ledger.tsv").read_text(encoding="utf-8"),
            )

    def test_demo_is_deterministic_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            result = run_demo(Path(directory))
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["qualification"]["final_class"], "QUALIFIED_WITH_BOUNDARY")


if __name__ == "__main__":
    unittest.main()
