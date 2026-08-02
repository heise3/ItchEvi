from __future__ import annotations

import gzip
from pathlib import Path

from scipy.io import mmwrite
from scipy.sparse import csr_matrix

from .io import read_cellranger_pseudobulk


def run_smoke(workdir: Path) -> dict[str, object]:
    workdir.mkdir(parents=True, exist_ok=True)
    matrix = csr_matrix([[1, 0, 2], [0, 3, 1], [2, 0, 0]], dtype=int)
    raw_matrix = workdir / "matrix.mtx"
    matrix_gz = workdir / "matrix.mtx.gz"
    features = workdir / "features.tsv.gz"
    barcodes = workdir / "barcodes.tsv.gz"
    mmwrite(raw_matrix, matrix)
    with raw_matrix.open("rb") as source, gzip.open(matrix_gz, "wb") as target:
        target.write(source.read())
    raw_matrix.unlink()
    with gzip.open(features, "wt", encoding="utf-8") as handle:
        handle.write("g1\tKRT16\tGene Expression\n")
        handle.write("g2\tS100A8\tGene Expression\n")
        handle.write("g3\tKRT16\tGene Expression\n")
    with gzip.open(barcodes, "wt", encoding="utf-8") as handle:
        handle.write("c1\nc2\nc3\n")
    counts, summary = read_cellranger_pseudobulk(matrix_gz, features, barcodes)
    expected = {"KRT16": 5, "S100A8": 4}
    observed = {gene: int(value) for gene, value in counts.items()}
    return {
        "status": "PASS" if observed == expected else "FAIL",
        "observed_counts": observed,
        "expected_counts": expected,
        "object_summary": summary,
    }
