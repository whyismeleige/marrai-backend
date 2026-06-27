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
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from app.models.base import metadata


class ExtractionMethod(enum.Enum):
    REGEX = "regex"
    LLM = "llm"
    HYBRID = "hybrid"
    MANUAL = "manual"


class ExtractionStatus(enum.Enum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    PARTIAL = "partial"


extraction_results_table = Table(
    "extraction_results",
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

    Column("extractor_version", Text, nullable=False),

    Column(
        "extraction_method",
        Enum(
            ExtractionMethod,
            name="extraction_method",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    ),
    Column(
        "status",
        Enum(
            ExtractionStatus,
            name="extraction_status",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=ExtractionStatus.PENDING,
        server_default=ExtractionStatus.PENDING.value,
    ),

    Column(
        "brand_mentioned",
        Boolean,
        nullable=False,
        default=False,
        server_default=sa.text("false"),
    ),
    Column(
        "brand_cited",
        Boolean,
        nullable=False,
        default=False,
        server_default=sa.text("false"),
    ),
    Column(
        "brand_recommended",
        Boolean,
        nullable=False,
        default=False,
        server_default=sa.text("false"),
    ),

    Column("best_brand_rank", Integer, nullable=True),

    Column(
        "competitor_mentioned",
        Boolean,
        nullable=False,
        default=False,
        server_default=sa.text("false"),
    ),
    Column(
        "competitor_recommended",
        Boolean,
        nullable=False,
        default=False,
        server_default=sa.text("false"),
    ),

    Column(
        "total_citations",
        Integer,
        nullable=False,
        default=0,
        server_default=sa.text("0"),
    ),
    Column(
        "owned_citations_count",
        Integer,
        nullable=False,
        default=0,
        server_default=sa.text("0"),
    ),
    Column(
        "competitor_citations_count",
        Integer,
        nullable=False,
        default=0,
        server_default=sa.text("0"),
    ),
    Column(
        "third_party_citations_count",
        Integer,
        nullable=False,
        default=0,
        server_default=sa.text("0"),
    ),

    Column(
        "confidence_score",
        Numeric,
        nullable=False,
        default=0,
        server_default=sa.text("0"),
    ),

    Column(
        "raw_extraction",
        JSONB,
        nullable=False,
        default=dict,
        server_default=sa.text("'{}'::jsonb"),
    ),
    Column("error_message", Text, nullable=True),

    Column(
        "created_at",
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    ),

    Index("ix_extraction_results_organization_id", "organization_id"),
    Index("ix_extraction_results_project_id", "project_id"),
    Index("ix_extraction_results_run_batch_id", "run_batch_id"),
    Index("ix_extraction_results_prompt_run_id", "prompt_run_id"),
    Index("ix_extraction_results_observation_id", "observation_id"),
    Index("ix_extraction_results_prompt_id", "prompt_id"),
    Index("ix_extraction_results_platform_id", "platform_id"),
    Index("ix_extraction_results_status", "status"),
    Index("ix_extraction_results_extractor_version", "extractor_version"),
    Index(
        "ix_extraction_results_observation_extractor_version",
        "observation_id",
        "extractor_version",
        unique=True,
    ),
)
