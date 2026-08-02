from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from itchevi.contracts import audit_contract


class TestContracts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_json_contract(self):
        path = self.root / "gate.json"
        path.write_text(json.dumps({"decision": "PASS"}), encoding="utf-8")
        result = audit_contract(
            "fixed_test",
            {
                "path": str(path),
                "format": "json",
                "expected": {"decision": "PASS"},
            },
        )
        self.assertEqual(result["status"], "PASS")

    def test_tsv_contract(self):
        path = self.root / "result.tsv"
        path.write_text("a\tb\n1\t2\n", encoding="utf-8")
        result = audit_contract(
            "external",
            {
                "path": str(path),
                "format": "tsv",
                "required_columns": ["a", "b"],
                "min_rows": 1,
            },
        )
        self.assertEqual(result["status"], "PASS")
