from __future__ import annotations

import gzip
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.io import mmread


def read_cellranger_pseudobulk(
    matrix_path: Path,
    features_path: Path,
    barcodes_path: Path,
) -> tuple[pd.Series, dict[str, int]]:
    features = pd.read_csv(
        features_path,
        sep="\t",
        header=None,
        compression="gzip",
    )
    barcodes = pd.read_csv(
        barcodes_path,
        sep="\t",
        header=None,
        compression="gzip",
    )
    with gzip.open(matrix_path, "rb") as handle:
        matrix = mmread(handle).tocsr()
    n_features, n_cells = matrix.shape
    if n_features != len(features):
        raise ValueError("Feature count does not match matrix rows")
    if n_cells != len(barcodes):
        raise ValueError("Barcode count does not match matrix columns")
    counts = np.asarray(matrix.sum(axis=1)).ravel()
    pseudobulk = (
        pd.DataFrame(
            {
                "gene": features.iloc[:, 1].astype(str).str.upper(),
                "count": counts,
            }
        )
        .groupby("gene", sort=True)["count"]
        .sum()
    )
    return pseudobulk, {
        "n_features": int(n_features),
        "n_cells": int(n_cells),
        "nnz": int(matrix.nnz),
        "total_counts": int(counts.sum()),
    }

