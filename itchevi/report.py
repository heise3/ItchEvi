from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any


def render_report(
    qualification_rows: list[dict[str, Any]],
    terminal_ledger: list[dict[str, Any]],
    run_id: str,
) -> str:
    classes = Counter(str(row["final_class"]) for row in qualification_rows)
    states = Counter(str(row["terminal_state"]) for row in terminal_ledger)
    lines = [
        "# ItchEvi qualification report",
        "",
        f"- Run ID: `{run_id}`",
        f"- Entities: {len(qualification_rows)}",
        f"- Terminal records: {len(terminal_ledger)}",
        "",
        "## Qualification classes",
        "",
        "| Class | Count |",
        "|---|---:|",
    ]
    lines.extend(f"| {name} | {count} |" for name, count in sorted(classes.items()))
    lines.extend(["", "## Terminal states", "", "| State | Count |", "|---|---:|"])
    lines.extend(f"| {name} | {count} |" for name, count in sorted(states.items()))
    lines.extend(
        [
            "",
            "## Entity decisions",
            "",
            "| Entity | Claim | Class | Coverage | Support | Conflict | Boundaries |",
            "|---|---|---|---:|---:|---:|---|",
        ]
    )
    for row in qualification_rows:
        support = f"{row['support']:.3f}" if isinstance(row["support"], float) else "NA"
        conflict = f"{row['conflict']:.3f}" if isinstance(row["conflict"], float) else "NA"
        lines.append(
            f"| {row['entity_id']} | {row['claim_id']} | {row['final_class']} | "
            f"{row['coverage']:.3f} | {support} | {conflict} | {row['boundary_codes']} |"
        )
    lines.extend(
        [
            "",
            "Missing, failed and not-applicable records are not encoded as zero. "
            "Qualification classes apply only to the configured claim and are not biological truth probabilities.",
            "",
        ]
    )
    return "\n".join(lines)


def write_report(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
