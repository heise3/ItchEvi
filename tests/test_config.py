import json
from pathlib import Path
import tempfile
import unittest

from itchevi.config import load_config, validate_config


class ConfigurationTest(unittest.TestCase):
    def test_missing_input_is_explicit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            script = root / "script.py"
            script.write_text("print('ok')\n", encoding="utf-8")
            config = {
                "phase_root": str(root),
                "data_root": str(root / "data"),
                "python": "python",
                "rscript": "Rscript",
                "scripts": {
                    "read": str(script),
                    "edger": str(script),
                    "score": str(script),
                },
                "inputs": {"missing": str(root / "missing.tsv")},
            }
            path = root / "config.json"
            path.write_text(json.dumps(config), encoding="utf-8")
            rows = validate_config(load_config(path))
            missing = [row for row in rows if row["input_id"] == "missing"]
            self.assertEqual(len(missing), 1)
            self.assertFalse(missing[0]["exists"])

    def test_contract_config_requires_contracts(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audit.json"
            path.write_text(
                json.dumps({"mode": "frozen_contract_audit", "contracts": {}}),
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                load_config(path)


if __name__ == "__main__":
    unittest.main()
