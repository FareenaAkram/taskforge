"""Dataset record format (one JSON object per line in tasks.jsonl)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass


@dataclass
class Task:
    instance_id: str
    repo: str
    bug_count: int
    mutation_kinds: list
    problem_statement: str  # what a developer would see: failing behaviour, no hint of the fix
    patch: str  # golden patch (unified diff, source files only)
    snapshot: dict  # {path: contents} of the buggy repo, tests included
    test_files: list
    fail_to_pass: list  # fail on the snapshot, pass after the golden patch
    pass_to_pass: list  # pass before and after (regression guard)
    environment: dict
    validation: dict
    quality: dict
    difficulty: dict

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True)

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        return cls(**data)
