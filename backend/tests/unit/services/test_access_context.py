import pytest

from app.services.access_context import build_menu_tree


def test_build_menu_tree_returns_nested_nodes():
    tree = build_menu_tree(
        [
            {"id": 1, "parent_id": None, "name": "System"},
            {"id": 2, "parent_id": 1, "name": "Users"},
            {"id": 3, "parent_id": 2, "name": "Audit Logs"},
            {"id": 4, "parent_id": None, "name": "Workbench"},
        ]
    )

    assert tree[0]["children"][0]["name"] == "Users"
    assert tree[0]["children"][0]["children"][0]["name"] == "Audit Logs"
    assert tree[1]["children"] == []


def test_build_menu_tree_rejects_orphaned_children():
    with pytest.raises(ValueError, match="missing parent"):
        build_menu_tree(
            [
                {"id": 1, "parent_id": 99, "name": "Detached"},
            ]
        )
