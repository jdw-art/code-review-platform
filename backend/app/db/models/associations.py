from sqlalchemy import BigInteger, Column, ForeignKey, PrimaryKeyConstraint, Table

from app.db.base import Base


user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("role_id", BigInteger, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False),
    PrimaryKeyConstraint("user_id", "role_id", name="pk_user_roles"),
)

role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column(
        "role_id",
        BigInteger,
        ForeignKey("roles.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column(
        "permission_id",
        BigInteger,
        ForeignKey("permissions.id", ondelete="CASCADE"),
        nullable=False,
    ),
    PrimaryKeyConstraint("role_id", "permission_id", name="pk_role_permissions"),
)

role_menus = Table(
    "role_menus",
    Base.metadata,
    Column("role_id", BigInteger, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False),
    Column("menu_id", BigInteger, ForeignKey("menus.id", ondelete="CASCADE"), nullable=False),
    PrimaryKeyConstraint("role_id", "menu_id", name="pk_role_menus"),
)
