from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from app.schemas.domain import DatasetDocument, TestCase


class DatasetValidationError(ValueError):
    pass


def safe_dataset_path(path: str | Path, root: Path | None = None) -> Path:
    candidate = Path(path).resolve()
    if root is not None and not candidate.is_relative_to(root.resolve()):
        raise DatasetValidationError(f"dataset path must remain inside {root.resolve()}")
    if candidate.suffix.lower() not in {".json", ".jsonl"}:
        raise DatasetValidationError("dataset must be .json or .jsonl")
    return candidate


def load_dataset(path: str | Path) -> DatasetDocument:
    source = safe_dataset_path(path)
    try:
        if source.suffix.lower() == ".jsonl":
            lines = [json.loads(line) for line in source.read_text(encoding="utf-8").splitlines() if line.strip()]
            metadata = lines[0]["metadata"] if lines and "metadata" in lines[0] else {"name": source.stem, "version": "unversioned", "description": "", "source": str(source), "created_at": "1970-01-01T00:00:00Z"}
            cases = lines[1:] if lines and "metadata" in lines[0] else lines
            return DatasetDocument.model_validate({"metadata": metadata, "cases": cases})
        return DatasetDocument.model_validate_json(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValidationError, KeyError) as exc:
        raise DatasetValidationError(str(exc)) from exc


def dataset_checksum(document: DatasetDocument) -> str:
    canonical = json.dumps(document.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def dataset_stats(document: DatasetDocument) -> dict[str, Any]:
    return {"name": document.metadata.name, "version": document.metadata.version, "cases": len(document.cases),
        "categories": dict(Counter(case.category.value for case in document.cases)),
        "difficulty": dict(Counter(case.difficulty for case in document.cases)),
        "tags": dict(Counter(tag for case in document.cases for tag in case.tags).most_common()),
        "with_citations": sum(bool(case.expected_citations) for case in document.cases), "checksum": dataset_checksum(document)}


def diff_datasets(old: DatasetDocument, new: DatasetDocument) -> dict[str, Any]:
    before, after = {case.id: case for case in old.cases}, {case.id: case for case in new.cases}
    shared = before.keys() & after.keys()
    return {"from": old.metadata.version, "to": new.metadata.version, "added": sorted(after.keys() - before.keys()),
        "removed": sorted(before.keys() - after.keys()),
        "changed": sorted(case_id for case_id in shared if before[case_id].model_dump() != after[case_id].model_dump())}


def validate_unique_ids(cases: list[TestCase]) -> None:
    counts = Counter(case.id for case in cases)
    duplicates = sorted(case_id for case_id, count in counts.items() if count > 1)
    if duplicates:
        raise DatasetValidationError(f"duplicate case IDs: {', '.join(duplicates)}")

