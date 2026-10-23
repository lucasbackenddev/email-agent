"""Tabelas iniciais: senders, emails, replies.

Revision ID: 0001_initial
Revises:
Create Date: 2026-10-22
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "senders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("address", sa.String(length=320), nullable=False, unique=True, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "emails",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("imap_uid", sa.String(length=64), nullable=False, index=True),
        sa.Column("subject", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed", sa.Boolean(), nullable=False, index=True),
        sa.Column("sender_id", sa.Integer(), sa.ForeignKey("senders.id"), nullable=False, index=True),
        sa.UniqueConstraint("imap_uid", name="uq_emails_imap_uid"),
    )
    op.create_table(
        "replies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email_id", sa.Integer(), sa.ForeignKey("emails.id"), nullable=False, index=True),
        sa.Column("suggestion", sa.Text(), nullable=False),
        sa.Column("sent_body", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("replies")
    op.drop_table("emails")
    op.drop_table("senders")
