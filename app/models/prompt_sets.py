import enum
import uuid

import sqlalchemy as sa
from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Table,
    Text,
    UUID,
)
from sqlalchemy.sql import func

from app.models.base import metadata

class PromptSetStatus(enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"

prompt_sets_table = Table(
    "prompt_sets",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    Column(
        "organization_id",
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
    ),
    Column(
        "project_id",
        UUID(as_uuid=True),
        ForeignKey("brand_projects.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column(
        "created_by_user_id",
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    ),
    Column("name", Text, nullable=False),
    Column("description", Text, nullable=True),
    Column("version", Integer, nullable=False, default=1, server_default=sa.text("1")),
    Column(
        "status",
        Enum(
            PromptSetStatus,
            name="prompt_set_status",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=PromptSetStatus.DRAFT,
        server_default=PromptSetStatus.DRAFT.value,
    ),
    Column("prompt_count", Integer, nullable=False, default=0, server_default=sa.text("0")),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
    Column(
        "updated_at",
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    ),
    Column("deleted_at", DateTime(timezone=True), nullable=True),
    Index("ix_prompt_sets_organization_id", "organization_id"),
    Index("ix_prompt_sets_project_id", "project_id"),
    Index("ix_prompt_sets_created_by_user_id", "created_by_user_id"),
    Index("ix_prompt_sets_status", "status"),
    Index("ix_prompt_sets_project_name_version", "project_id", "name", "version", unique=True),
)
