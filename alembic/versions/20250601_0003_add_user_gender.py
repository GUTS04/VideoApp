"""add user gender

Revision ID: 20250601_0003
Revises: 20250531_0002
Create Date: 2025-06-01

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20250601_0003"
down_revision: Union[str, None] = "20250531_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("gender", sa.String(length=10), nullable=False, server_default="male"),
    )
    op.create_check_constraint(
        "ck_users_gender",
        "users",
        "gender IN ('male', 'female')",
    )
    op.alter_column("users", "gender", server_default=None)


def downgrade() -> None:
    op.drop_constraint("ck_users_gender", "users", type_="check")
    op.drop_column("users", "gender")
