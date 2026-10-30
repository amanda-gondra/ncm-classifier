import json
from pathlib import Path

import pytest

from ncm_classifier.data.ncm_table import parse_ncm_payload
from ncm_classifier.data.scope import ScopeError, load_scope

PROJECT_SCOPE = Path(__file__).resolve().parents[1] / "configs" / "scope.json"


def _write(tmp_path: Path, groups: dict[str, object]) -> Path:
    path = tmp_path / "scope.json"
    path.write_text(json.dumps({"groups": groups}), encoding="utf-8")
    return path


def _table(*codes: str):
    return parse_ncm_payload(
        {
            "Data_Ultima_Atualizacao_NCM": "x",
            "Ato": "x",
            "Nomenclaturas": [
                {"Codigo": c, "Descricao": c, "Data_Inicio": "01/01/2022", "Data_Fim": "31/12/9999"}
                for c in codes
            ],
        }
    )


def test_project_scope_has_37_unique_positions() -> None:
    scope = load_scope(PROJECT_SCOPE)
    assert len(scope.positions) == 37
    assert scope.group_by_position["8543"] == "tools_wire_fencing"


def test_validate_passes_when_all_positions_exist(tmp_path: Path) -> None:
    scope = load_scope(_write(tmp_path, {"g": {"label": "G", "positions": ["7313"]}}))
    scope.validate_against(_table("7313.00.00"))


def test_validate_fails_for_missing_position(tmp_path: Path) -> None:
    scope = load_scope(_write(tmp_path, {"g": {"label": "G", "positions": ["7313", "9999"]}}))
    with pytest.raises(ScopeError, match="9999"):
        scope.validate_against(_table("7313.00.00"))


@pytest.mark.parametrize(
    "groups",
    [
        {},
        {"g": {"label": "G", "positions": ["731"]}},
        {"a": {"label": "A", "positions": ["7313"]}, "b": {"label": "B", "positions": ["7313"]}},
    ],
)
def test_rejects_invalid_scope(tmp_path: Path, groups: dict[str, object]) -> None:
    with pytest.raises(ScopeError):
        load_scope(_write(tmp_path, groups))
