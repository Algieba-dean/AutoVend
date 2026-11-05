"""
Tests for release alignment gate (Cohen's Kappa & human calibration review).
"""

import json

from src.eval import alignment_gate


def test_alignment_gate_on_seeded_dataset():
    """Verify the seeded evaluation/review/latest.jsonl passes calibration gate."""
    exit_code = alignment_gate.main(["--review", "evaluation/review/latest.jsonl"])
    assert exit_code == 0


def test_alignment_gate_missing_file_fails(tmp_path):
    """Missing review file without fallback must fail cleanly with non-zero exit."""
    missing = tmp_path / "nonexistent.jsonl"
    exit_code = alignment_gate.main(["--review", str(missing)])
    assert exit_code == 1


def test_alignment_gate_fallback_mechanism(tmp_path):
    """When target file is missing, fallback to baseline.jsonl in same dir."""
    review_dir = tmp_path / "review"
    review_dir.mkdir()

    baseline_jsonl = review_dir / "baseline.jsonl"
    baseline_judged = review_dir / "baseline.judged.json"

    # Write 20 identical cases
    with baseline_jsonl.open("w", encoding="utf-8") as f:
        for i in range(20):
            f.write(json.dumps({"id": f"c{i}", "human_score": 1.0, "answer": "ok"}) + "\n")

    baseline_judged.write_text(
        json.dumps({"scores": {f"c{i}": 1.0 for i in range(20)}}), encoding="utf-8"
    )

    target_missing = review_dir / "latest.jsonl"
    # When latest.jsonl is missing, should fall back to baseline.jsonl
    exit_code = alignment_gate.main(["--review", str(target_missing)])
    assert exit_code == 0


def test_alignment_gate_json_out(tmp_path):
    """Verify --json-out writes structured alignment report."""
    out_file = tmp_path / "alignment_report.json"
    exit_code = alignment_gate.main(
        [
            "--review",
            "evaluation/review/latest.jsonl",
            "--json-out",
            str(out_file),
        ]
    )
    assert exit_code == 0
    assert out_file.exists()
    data = json.loads(out_file.read_text(encoding="utf-8"))
    assert data["n"] == 32
    assert data["kappa"] == 1.0
    assert data["passed"] is True
