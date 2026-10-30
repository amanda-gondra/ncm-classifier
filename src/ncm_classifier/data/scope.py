"""Classification scope: which NCM positions the model can suggest.

The scope lives in configs/scope.json so it can change without touching code.
It is always validated against the official table: a position that does not
exist, or is no longer valid, stops the pipeline instead of producing labels
the model could never be right about.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from ncm_classifier.data.ncm_table import NcmTable


class ScopeError(ValueError):
    """Raised when the scope file is malformed or disagrees with the NCM table."""


@dataclass(frozen=True)
class Scope:
    group_by_position: dict[str, str]
    group_labels: dict[str, str]

    @property
    def positions(self) -> list[str]:
        return sorted(self.group_by_position)

    def validate_against(self, table: NcmTable) -> None:
        """Fail if any scope position is missing from the (already filtered) table."""
        available = set(table.positions()["code"])
        missing = sorted(set(self.group_by_position) - available)
        if missing:
            raise ScopeError(f"positions not found in the NCM table: {missing}")


def load_scope(path: Path) -> Scope:
    with path.open(encoding="utf-8") as file:
        raw = json.load(file)

    try:
        groups = raw["groups"]
    except (KeyError, TypeError) as exc:
        raise ScopeError("scope file must have a 'groups' object") from exc

    group_by_position: dict[str, str] = {}
    group_labels: dict[str, str] = {}
    for group_id, group in groups.items():
        group_labels[group_id] = group["label"]
        for position in group["positions"]:
            if not (isinstance(position, str) and len(position) == 4 and position.isdigit()):
                raise ScopeError(f"invalid position {position!r} in group {group_id!r}")
            if position in group_by_position:
                raise ScopeError(f"position {position} appears in more than one group")
            group_by_position[position] = group_id

    if not group_by_position:
        raise ScopeError("scope has no positions")

    return Scope(group_by_position=group_by_position, group_labels=group_labels)
