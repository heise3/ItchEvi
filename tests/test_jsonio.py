import csv
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from itchevi.demo import write_demo_inputs
from itchevi.jsonio import normalize_inputs


class JsonNormalizationTest(unittest.TestCase):
    def test_normalized_outputs_pass_and_missing_is_null(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = write_demo_inputs(root / "inputs")
            output = root / "json"
            manifest = normalize_inputs(
                paths["evidence"], paths["entities"], paths["layers"], paths["config"], output
            )
            self.assertEqual(manifest["status"], "PASS")
            self.assertEqual(manifest["row_counts"], {"evidence": 4, "entities": 1, "layers": 4})
            evidence = json.loads((output / "evidence.json").read_text(encoding="utf-8"))
            missing = next(row for row in evidence if row["terminal_state"] == "MISSING")
            self.assertIsNone(missing["effect"])
            self.assertIsNone(missing["direction"])
            self.assertNotEqual(missing["effect"], 0)
            self.assertIsInstance(evidence[0]["effect"], float)
            self.assertIsInstance(evidence[0]["n_independent_units"], int)

    def test_cli_and_api_normalized_payloads_match(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = write_demo_inputs(root / "inputs")
            api_output = root / "api"
            cli_output = root / "cli"
            normalize_inputs(
                paths["evidence"], paths["entities"], paths["layers"], paths["config"], api_output
            )
            command = [
                sys.executable,
                "-m",
                "itchevi.cli",
                "normalize",
                "--evidence",
                str(paths["evidence"]),
                "--entities",
                str(paths["entities"]),
                "--layers",
                str(paths["layers"]),
                "--config",
                str(paths["config"]),
                "--output",
                str(cli_output),
            ]
            completed = subprocess.run(command, check=False, capture_output=True, text=True)
            self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
            for name in ["evidence.json", "entities.json", "layers.json", "qualification_config.json"]:
                self.assertEqual(
                    (api_output / name).read_bytes(),
                    (cli_output / name).read_bytes(),
                    name,
                )

    def test_extra_tsv_column_is_rejected_not_silently_dropped(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = write_demo_inputs(root / "inputs")
            with paths["entities"].open("r", encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle, delimiter="\t"))
            rows[0]["unexpected"] = "must not disappear"
            with paths["entities"].open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0]), delimiter="\t")
                writer.writeheader()
                writer.writerows(rows)
            with self.assertRaisesRegex(ValueError, "outside its JSON Schema"):
                normalize_inputs(
                    paths["evidence"],
                    paths["entities"],
                    paths["layers"],
                    paths["config"],
                    root / "json",
                )


if __name__ == "__main__":
    unittest.main()
