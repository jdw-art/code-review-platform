"""compat alias for pico online agent schema

Revision ID: 0004_pico_online_agent_schema
Revises: 0003_webhook_review_execution
Create Date: 2026-06-04
"""

from __future__ import annotations


revision = "0004_pico_online_agent_schema"
down_revision = "0003_webhook_review_execution"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Compatibility bridge for databases already stamped with the old revision id."""


def downgrade() -> None:
    """No-op compatibility bridge."""
