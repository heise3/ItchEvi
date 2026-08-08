import json
from pathlib import Path
import unittest

import itchevi
from jsonschema.validators import validator_for


class SchemaTest(unittest.TestCase):
    def test_all_schemas_are_valid_json_with_ids(self):
        schema_dir = Path(itchevi.__file__).resolve().parent / "schemas"
        schemas = sorted(schema_dir.glob("*.json"))
        self.assertEqual(len(schemas), 7)
        ids = set()
        for path in schemas:
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["$schema"], "https://json-schema.org/draft/2020-12/schema")
            self.assertIn("$id", payload)
            validator_for(payload).check_schema(payload)
            ids.add(payload["$id"])
        self.assertEqual(len(ids), len(schemas))

    def test_public_api_is_exposed(self):
        self.assertTrue(callable(itchevi.qualify))
        self.assertTrue(callable(itchevi.qualify_records))
        self.assertTrue(callable(itchevi.validate_inputs))
        self.assertEqual(itchevi.__version__, "0.5.1")


if __name__ == "__main__":
    unittest.main()
