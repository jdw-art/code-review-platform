from app.services.access_context import build_menu_tree


def test_build_menu_tree_returns_nested_nodes():
    tree = build_menu_tree(
        [
            {"id": 1, "parent_id": None, "name": "System"},
            {"id": 2, "parent_id": 1, "name": "Users"},
        ]
    )

    assert tree[0]["children"][0]["name"] == "Users"
