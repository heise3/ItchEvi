import gzip
from pathlib import Path
import tempfile
import unittest

try:
    import numpy as np
    from scipy import sparse
    from scipy.io import mmwrite
    from itchevi.io import read_cellranger_pseudobulk

    SCIPY_AVAILABLE = True
except ModuleNotFoundError:
    SCIPY_AVAILABLE = False


@unittest.skipUnless(SCIPY_AVAILABLE, "optional legacy reader requires NumPy/SciPy")
class CellRangerPseudobulkTest(unittest.TestCase):
    def test_counts_and_duplicate_symbols(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            matrix = sparse.coo_matrix(
                np.array(
                    [
                        [1, 2],
                        [3, 0],
                        [0, 4],
                    ],
                    dtype=int,
                )
            )
            matrix_path = root / "matrix.mtx.gz"
            with gzip.open(matrix_path, "wb") as handle:
                mmwrite(handle, matrix)
            features = root / "features.tsv.gz"
            with gzip.open(features, "wt", encoding="utf-8") as handle:
                handle.write("id1\tGeneA\tGene Expression\n")
                handle.write("id2\tGeneA\tGene Expression\n")
                handle.write("id3\tGeneB\tGene Expression\n")
            barcodes = root / "barcodes.tsv.gz"
            with gzip.open(barcodes, "wt", encoding="utf-8") as handle:
                handle.write("cell1\ncell2\n")
            pseudobulk, summary = read_cellranger_pseudobulk(
                matrix_path,
                features,
                barcodes,
            )
            self.assertEqual(int(pseudobulk["GENEA"]), 6)
            self.assertEqual(int(pseudobulk["GENEB"]), 4)
            self.assertEqual(summary["n_cells"], 2)
            self.assertEqual(summary["total_counts"], 10)


if __name__ == "__main__":
    unittest.main()
