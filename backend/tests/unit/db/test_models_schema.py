from app.db.models import Menu, Permission, RefreshSession, Role, User
from app.db.models.associations import role_menus, role_permissions, user_roles


def test_primary_keys_use_bigint() -> None:
    assert str(User.__table__.c.id.type) == "BIGINT"
    assert str(Role.__table__.c.id.type) == "BIGINT"
    assert str(Permission.__table__.c.id.type) == "BIGINT"
    assert str(Menu.__table__.c.id.type) == "BIGINT"
    assert str(RefreshSession.__table__.c.id.type) == "BIGINT"


def test_join_tables_use_bigint_foreign_keys_with_composite_primary_keys() -> None:
    assert list(user_roles.c.keys()) == ["user_id", "role_id"]
    assert list(user_roles.primary_key.columns.keys()) == ["user_id", "role_id"]
    assert str(user_roles.c.user_id.type) == "BIGINT"
    assert str(user_roles.c.role_id.type) == "BIGINT"

    assert list(role_permissions.primary_key.columns.keys()) == ["role_id", "permission_id"]
    assert str(role_permissions.c.role_id.type) == "BIGINT"
    assert str(role_permissions.c.permission_id.type) == "BIGINT"

    assert list(role_menus.primary_key.columns.keys()) == ["role_id", "menu_id"]
    assert str(role_menus.c.role_id.type) == "BIGINT"
    assert str(role_menus.c.menu_id.type) == "BIGINT"


def test_refresh_sessions_indexes_and_foreign_keys_match_expected_shape() -> None:
    refresh_sessions = RefreshSession.__table__

    indexed_columns = {
        tuple(column.name for column in index.columns)
        for index in refresh_sessions.indexes
    }
    assert ("user_id",) in indexed_columns
    assert str(refresh_sessions.c.user_id.type) == "BIGINT"

    user_id_foreign_keys = list(refresh_sessions.c.user_id.foreign_keys)
    assert len(user_id_foreign_keys) == 1
    assert user_id_foreign_keys[0].target_fullname == "users.id"
    assert user_id_foreign_keys[0].ondelete == "CASCADE"


def test_orm_defaults_expose_schema_defaults_for_core_fields() -> None:
    user_defaults = User.__table__.c
    menu_defaults = Menu.__table__.c

    assert str(user_defaults.is_active.server_default.arg) == "true"
    assert str(user_defaults.is_superuser.server_default.arg) == "false"
    assert str(user_defaults.must_change_password.server_default.arg) == "false"
    assert str(menu_defaults.sort.server_default.arg) == "0"
    assert str(menu_defaults.visible.server_default.arg) == "true"
