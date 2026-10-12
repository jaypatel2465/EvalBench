import json

import pytest

from app.services.datasets import DatasetValidationError, dataset_stats, diff_datasets, load_dataset, validate_unique_ids


def test_demo_dataset_is_valid_balanced_and_versioned():
    document = load_dataset("datasets/golden_v1.json")
    stats = dataset_stats(document)
    assert stats["cases"] == 75
    assert document.metadata.version == "v1"
    assert len(stats["categories"]) >= 8
    assert stats["with_citations"] == 75


def test_dataset_rejects_duplicate_ids():
    document = load_dataset("datasets/golden_v1.json")
    with pytest.raises(DatasetValidationError, match="duplicate"):
        validate_unique_ids([document.cases[0], document.cases[0]])


def test_dataset_diff_reports_content_change(tmp_path):
    raw = json.loads(open("datasets/golden_v1.json", encoding="utf-8").read())
    raw["metadata"]["version"] = "v2"
    raw["cases"][0]["reference_answer"] = "Changed"
    path = tmp_path / "v2.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    diff = diff_datasets(load_dataset("datasets/golden_v1.json"), load_dataset(path))
    assert diff["changed"] == ["sec-001"]

