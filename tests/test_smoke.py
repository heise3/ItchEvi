from pathlib import Path
import tempfile
import unittest

try:
    from itchevi.smoke import run_smoke

    SCIPY_AVAILABLE = True
except ModuleNotFoundError:
    SCIPY_AVAILABLE = False


@unittest.skipUnless(SCIPY_AVAILABLE, "optional legacy reader requires NumPy/SciPy")
class TestSmoke(unittest.TestCase):
    def test_cellranger_smoke(self):
        with tempfile.TemporaryDirectory() as temp:
            result = run_smoke(Path(temp))
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["observed_counts"]["KRT16"], 5)
