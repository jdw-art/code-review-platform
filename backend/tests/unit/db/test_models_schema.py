from app.db.models import Menu, Permission, RefreshSession, Role, User


def test_primary_keys_use_bigint() -> None:
    assert str(User.__table__.c.id.type) == "BIGINT"
    assert str(Role.__table__.c.id.type) == "BIGINT"
    assert str(Permission.__table__.c.id.type) == "BIGINT"
    assert str(Menu.__table__.c.id.type) == "BIGINT"
    assert str(RefreshSession.__table__.c.id.type) == "BIGINT"
