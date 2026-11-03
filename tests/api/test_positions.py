from pathlib import Path

import pytest

from ncm_classifier.data.positions import load_positions
from ncm_classifier.data.scope import load_scope


def test_every_scope_position_has_an_official_description() -> None:
    catalog = load_positions()
    scope = load_scope(Path("configs/scope.json")).positions
    assert sorted(catalog.positions) == scope
    assert all(p.description.strip() for p in catalog.positions.values())
    assert catalog.describe("3105").formatted == "31.05"
    assert catalog.level == "position"


def test_unknown_position_is_an_error() -> None:
    with pytest.raises(KeyError, match="no official description"):
        load_positions().describe("9999")
