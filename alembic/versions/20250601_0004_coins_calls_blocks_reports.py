"""coins, call sessions, blocks, reports

Revision ID: 20250601_0004
Revises: 20250601_0003
Create Date: 2025-06-01

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20250601_0004"
down_revision: Union[str, None] = "20250601_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("coin_balance", sa.Integer(), nullable=False, server_default="500"),
    )
    op.alter_column("users", "coin_balance", server_default=None)

    op.create_table(
        "call_sessions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("match_id", sa.String(length=64), nullable=False),
        sa.Column("user_a_id", sa.UUID(), nullable=False),
        sa.Column("user_b_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("connected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_billed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("user_a_connected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("user_b_connected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("user_a_coins_charged", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("user_b_coins_charged", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("billing_finalized", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_a_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_b_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("match_id"),
    )
    op.create_index("ix_call_sessions_match_id", "call_sessions", ["match_id"])
    op.create_index("ix_call_sessions_status", "call_sessions", ["status"])
    op.create_index("ix_call_sessions_user_a_id", "call_sessions", ["user_a_id"])
    op.create_index("ix_call_sessions_user_b_id", "call_sessions", ["user_b_id"])

    op.create_table(
        "coin_transactions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("transaction_type", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=False),
        sa.Column("call_session_id", sa.UUID(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["call_session_id"], ["call_sessions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key"),
    )
    op.create_index("ix_coin_transactions_user_id", "coin_transactions", ["user_id"])
    op.create_index("ix_coin_transactions_transaction_type", "coin_transactions", ["transaction_type"])
    op.create_index("ix_coin_transactions_call_session_id", "coin_transactions", ["call_session_id"])
    op.create_index("ix_coin_transactions_created_at", "coin_transactions", ["created_at"])

    op.create_table(
        "user_blocks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("blocker_id", sa.UUID(), nullable=False),
        sa.Column("blocked_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["blocked_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["blocker_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("blocker_id", "blocked_id", name="uq_user_blocks_pair"),
    )
    op.create_index("ix_user_blocks_blocker_id", "user_blocks", ["blocker_id"])
    op.create_index("ix_user_blocks_blocked_id", "user_blocks", ["blocked_id"])

    op.create_table(
        "user_reports",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("reporter_id", sa.UUID(), nullable=False),
        sa.Column("reported_id", sa.UUID(), nullable=False),
        sa.Column("reason", sa.String(length=64), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("call_session_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["call_session_id"], ["call_sessions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reporter_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reported_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_reports_reporter_id", "user_reports", ["reporter_id"])
    op.create_index("ix_user_reports_reported_id", "user_reports", ["reported_id"])
    op.create_index("ix_user_reports_created_at", "user_reports", ["created_at"])


def downgrade() -> None:
    op.drop_table("user_reports")
    op.drop_table("user_blocks")
    op.drop_table("coin_transactions")
    op.drop_table("call_sessions")
    op.drop_column("users", "coin_balance")
