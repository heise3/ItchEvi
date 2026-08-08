import copy
from pathlib import Path
import tempfile
import unittest

from itchevi.core import qualify_records
from itchevi.demo import write_demo_inputs
from itchevi.validation import read_json, read_tsv, validate_objects


class QualificationCoreTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        paths = write_demo_inputs(Path(self.temp.name))
        self.evidence = read_tsv(paths["evidence"])
        self.entities = read_tsv(paths["entities"])
        self.layers = read_tsv(paths["layers"])
        self.config = read_json(paths["config"])

    def tearDown(self):
        self.temp.cleanup()

    def run_one(self, evidence=None, config=None):
        run = qualify_records(
            evidence if evidence is not None else self.evidence,
            self.entities,
            self.layers,
            config if config is not None else self.config,
        )
        return run, run.qualification_rows[0]

    def test_worked_example(self):
        run, row = self.run_one()
        self.assertEqual(row["final_class"], "QUALIFIED_WITH_BOUNDARY")
        self.assertAlmostEqual(row["support"], 0.75)
        self.assertAlmostEqual(row["conflict"], 0.25)
        self.assertAlmostEqual(row["coverage"], 1.0)
        self.assertEqual(len(run.terminal_ledger), 4)

    def test_required_missing_is_not_zero(self):
        evidence = [row for row in self.evidence if row["layer_id"] != "external_direction"]
        run, row = self.run_one(evidence)
        self.assertEqual(row["final_class"], "ABSTAIN")
        self.assertEqual(row["terminal_code"], "ABSTAIN_INSUFFICIENT_EVIDENCE")
        missing = [x for x in run.terminal_ledger if x["layer_id"] == "external_direction"]
        self.assertEqual(missing[0]["terminal_state"], "MISSING")
        self.assertTrue(missing[0]["synthetic_missing_receipt"])
        self.assertAlmostEqual(row["coverage"], 2 / 3)
        self.assertEqual(len(missing[0]["input_sha256"]), 64)
        self.assertEqual(len(missing[0]["config_sha256"]), 64)

    def test_required_layer_below_independent_unit_minimum_abstains(self):
        evidence = copy.deepcopy(self.evidence)
        external = next(row for row in evidence if row["layer_id"] == "external_direction")
        external["n_independent_units"] = "1"
        _, row = self.run_one(evidence)
        self.assertEqual(row["final_class"], "ABSTAIN")
        self.assertEqual(row["terminal_code"], "ABSTAIN_INSUFFICIENT_EVIDENCE")
        self.assertIn("INSUFFICIENT_INDEPENDENT_UNITS:external_direction", row["boundary_codes"])

    def test_inactive_conditional_critical_layer_is_excluded(self):
        evidence = copy.deepcopy(self.evidence)
        layers = copy.deepcopy(self.layers)
        config = copy.deepcopy(self.config)
        external_layer = next(row for row in layers if row["layer_id"] == "external_direction")
        external_layer["requirement"] = "critical"
        external_layer["conditional_rule"] = "flag:external_enabled"
        config["condition_flags"] = {"external_enabled": False}
        external = next(row for row in evidence if row["layer_id"] == "external_direction")
        external.update(
            terminal_state="NOT_APPLICABLE", failure_code="CONDITION_NOT_ACTIVE",
            effect="", direction="", SE="", P="", FDR="", gate_status="NOT_TESTED",
        )
        operator = next(row for row in evidence if row["layer_id"] == "operator_stability")
        operator.update(effect="0.2", direction="1", quality_multiplier="1.0")
        run = qualify_records(evidence, self.entities, layers, config)
        row = run.qualification_rows[0]
        self.assertEqual(row["final_class"], "QUALIFIED_WITH_BOUNDARY")
        ledger = next(item for item in run.terminal_ledger if item["layer_id"] == "external_direction")
        self.assertFalse(ledger["condition_active"])

    def test_optional_construction_layer_rejected(self):
        layers = copy.deepcopy(self.layers)
        next(row for row in layers if row["layer_id"] == "discovery_paired")["requirement"] = "optional"
        rows = validate_objects(self.evidence, self.entities, layers, self.config)
        self.assertEqual(rows[0]["status"], "FAIL")
        self.assertTrue(any("construction_layer_id must be critical or required" in row["detail"] for row in rows))

    def test_blank_provenance_hash_rejected(self):
        evidence = copy.deepcopy(self.evidence)
        evidence[0]["input_sha256"] = ""
        evidence[0]["config_sha256"] = ""
        rows = validate_objects(evidence, self.entities, self.layers, self.config)
        self.assertEqual(rows[0]["status"], "FAIL")
        self.assertTrue(any("input_sha256 is required" in row["detail"] for row in rows))

    def test_critical_missing_abstains(self):
        evidence = [row for row in self.evidence if row["layer_id"] != "discovery_paired"]
        _, row = self.run_one(evidence)
        self.assertEqual(row["final_class"], "ABSTAIN")
        self.assertEqual(row["terminal_code"], "ABSTAIN_INSUFFICIENT_EVIDENCE")

    def test_critical_backend_failure_not_qualified(self):
        evidence = copy.deepcopy(self.evidence)
        discovery = next(row for row in evidence if row["layer_id"] == "discovery_paired")
        discovery.update(
            terminal_state="FAILED",
            failure_code="BACKEND_TERMINATION",
            effect="",
            direction="",
            SE="",
            P="",
            FDR="",
            gate_status="FAIL",
        )
        _, row = self.run_one(evidence)
        self.assertEqual(row["final_class"], "NOT_QUALIFIED")
        self.assertEqual(row["terminal_code"], "NOT_QUALIFIED_EXECUTION_FAILURE")

    def test_discovery_gate_failure(self):
        evidence = copy.deepcopy(self.evidence)
        next(row for row in evidence if row["layer_id"] == "discovery_paired")["FDR"] = "0.20"
        _, row = self.run_one(evidence)
        self.assertEqual(row["final_class"], "NOT_QUALIFIED")
        self.assertEqual(row["terminal_code"], "NOT_QUALIFIED_DISCOVERY_GATE")

    def test_stability_failure(self):
        evidence = copy.deepcopy(self.evidence)
        next(row for row in evidence if row["layer_id"] == "operator_stability")["gate_status"] = "FAIL"
        _, row = self.run_one(evidence)
        self.assertEqual(row["final_class"], "DESCRIPTIVE_ONLY")
        self.assertEqual(row["terminal_code"], "DESCRIPTIVE_ONLY_UNSTABLE")

    def test_directional_conflict(self):
        evidence = copy.deepcopy(self.evidence)
        external = next(row for row in evidence if row["layer_id"] == "external_direction")
        external["direction"] = "-1"
        external["effect"] = "-0.8"
        _, row = self.run_one(evidence)
        self.assertEqual(row["final_class"], "DESCRIPTIVE_ONLY")
        self.assertEqual(row["terminal_code"], "DESCRIPTIVE_ONLY_CONFLICTED")

    def test_non_observed_numeric_value_rejected(self):
        evidence = copy.deepcopy(self.evidence)
        spatial = next(row for row in evidence if row["layer_id"] == "spatial_context")
        spatial["effect"] = "0"
        rows = validate_objects(evidence, self.entities, self.layers, self.config)
        self.assertEqual(rows[0]["status"], "FAIL")
        self.assertTrue(any("non-OBSERVED" in row["detail"] for row in rows))

    def test_duplicate_entity_layer_rejected(self):
        evidence = self.evidence + [copy.deepcopy(self.evidence[0])]
        evidence[-1]["record_id"] = "R_DUPLICATE_LAYER"
        rows = validate_objects(evidence, self.entities, self.layers, self.config)
        self.assertEqual(rows[0]["status"], "FAIL")
        self.assertTrue(any("entity_id/layer_id" in row["detail"] for row in rows))


if __name__ == "__main__":
    unittest.main()
