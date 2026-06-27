import enum
import uuid

import sqlalchemy as sa
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Table,
    Text,
    UUID,
)
from sqlalchemy.sql import func

from app.models.base import metadata


class SourceCategory(enum.Enum):
    OWNED = "owned"
    COMPETITOR = "competitor"
    MARKETPLACE = "marketplace"
    PUBLISHER = "publisher"
    FORUM = "forum"
    SOCIAL = "social"
    UNKNOWN = "unknown"


citations_table = Table(
    "citations",
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
        "run_batch_id",
        UUID(as_uuid=True),
        ForeignKey("run_batches.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column(
        "prompt_run_id",
        UUID(as_uuid=True),
        ForeignKey("prompt_runs.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column(
        "observation_id",
        UUID(as_uuid=True),
        ForeignKey("ai_observations.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column(
        "extraction_result_id",
        UUID(as_uuid=True),
        ForeignKey("extraction_results.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column(
        "prompt_id",
        UUID(as_uuid=True),
        ForeignKey("prompts.id", ondelete="RESTRICT"),
        nullable=False,
    ),
    Column(
        "platform_id",
        UUID(as_uuid=True),
        ForeignKey("ai_platforms.id", ondelete="RESTRICT"),
        nullable=False,
    ),

    Column(
        "competitor_id",
        UUID(as_uuid=True),
        ForeignKey("competitors.id", ondelete="SET NULL"),
        nullable=True,
    ),

    Column("citation_index", Integer, nullable=False),
    Column("citation_marker", Text, nullable=True),

    Column("cited_url", Text, nullable=False),
    Column("canonical_url", Text, nullable=True),
    Column("cited_domain", Text, nullable=False),
    Column("root_domain", Text, nullable=True),

    Column("title", Text, nullable=True),
    Column("snippet", Text, nullable=True),
    Column("citation_context", Text, nullable=True),

    Column(
        "is_owned_domain",
        Boolean,
        nullable=False,
        default=False,
        server_default=sa.text("false"),
    ),
    Column(
        "is_competitor_domain",
        Boolean,
        nullable=False,
        default=False,
        server_default=sa.text("false"),
    ),

    Column(
        "source_category",
        Enum(
            SourceCategory,
            name="source_category",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=SourceCategory.UNKNOWN,
        server_default=SourceCategory.UNKNOWN.value,
    ),

    Column(
        "confidence_score",
        Numeric,
        nullable=False,
        default=0,
        server_default=sa.text("0"),
    ),

    Column(
        "created_at",
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    ),

    Index("ix_citations_organization_id", "organization_id"),
    Index("ix_citations_project_id", "project_id"),
    Index("ix_citations_run_batch_id", "run_batch_id"),
    Index("ix_citations_prompt_run_id", "prompt_run_id"),
    Index("ix_citations_observation_id", "observation_id"),
    Index("ix_citations_extraction_result_id", "extraction_result_id"),
    Index("ix_citations_prompt_id", "prompt_id"),
    Index("ix_citations_platform_id", "platform_id"),
    Index("ix_citations_competitor_id", "competitor_id"),
    Index("ix_citations_cited_domain", "cited_domain"),
    Index("ix_citations_root_domain", "root_domain"),
    Index("ix_citations_source_category", "source_category"),
    Index("ix_citations_is_owned_domain", "is_owned_domain"),
    Index("ix_citations_is_competitor_domain", "is_competitor_domain"),
    Index("ix_citations_citation_index", "citation_index"),
)
