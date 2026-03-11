"""Initial schema: voices, recordings, training_jobs, generated_audios.

Revision ID: 0001_initial
Revises:
Create Date: 2026-03-11
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "voices",
        sa.Column("voice_id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False, unique=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("embedding_path", sa.String(512), nullable=True),
        sa.Column("samples_path", sa.String(512), nullable=True),
        sa.Column(
            "status",
            sa.Enum("pending", "ready", "failed", name="voice_status"),
            nullable=False,
            server_default="pending",
        ),
    )

    op.create_table(
        "recordings",
        sa.Column("recording_id", sa.String(36), primary_key=True),
        sa.Column("voice_id", sa.String(36), sa.ForeignKey("voices.voice_id"), nullable=False),
        sa.Column("file_path", sa.String(512), nullable=False),
        sa.Column("duration_seconds", sa.Float, nullable=True),
        sa.Column("section", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "training_jobs",
        sa.Column("job_id", sa.String(36), primary_key=True),
        sa.Column("voice_id", sa.String(36), sa.ForeignKey("voices.voice_id"), nullable=False),
        sa.Column(
            "status",
            sa.Enum("queued", "running", "done", "failed", name="job_status"),
            nullable=False,
            server_default="queued",
        ),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "generated_audios",
        sa.Column("audio_id", sa.String(36), primary_key=True),
        sa.Column("voice_id", sa.String(36), sa.ForeignKey("voices.voice_id"), nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("file_path", sa.String(512), nullable=False),
        sa.Column("speed", sa.Float, nullable=False, server_default="1.0"),
        sa.Column("temperature", sa.Float, nullable=False, server_default="0.7"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("generated_audios")
    op.drop_table("training_jobs")
    op.drop_table("recordings")
    op.drop_table("voices")
