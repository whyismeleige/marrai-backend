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


class MentionType(enum.Enum):
    NEUTRAL = "neutral"
    RECOMMENDATION = "recommendation"
    COMPARISON = "comparison"
    WARNING = "warning"
    PRODUCT_LISTING = "product_listing"


class SentimentType(enum.Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    MIXED = "mixed"
    UNKNOWN = "unknown"


class RecommendationStrength(enum.Enum):
    STRONG = "strong"
    MEDIUM = "medium"
    WEAK = "weak"
    NONE = "none"
    UNKNOWN = "unknown"


brand_mentions_table = Table(
    "brand_mentions",
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

    Column("brand_name_snapshot", Text, nullable=False),

    Column("mention_text", Text, nullable=False),
    Column("mention_context", Text, nullable=True),

    Column("character_start", Integer, nullable=True),
    Column("character_end", Integer, nullable=True),

    Column(
        "mention_type",
        Enum(
            MentionType,
            name="mention_type",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=MentionType.NEUTRAL,
        server_default=MentionType.NEUTRAL.value,
    ),
    Column(
        "sentiment",
        Enum(
            SentimentType,
            name="sentiment_type",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=SentimentType.UNKNOWN,
        server_default=SentimentType.UNKNOWN.value,
    ),

    Column(
        "is_recommended",
        Boolean,
        nullable=False,
        default=False,
        server_default=sa.text("false"),
    ),
    Column(
        "recommendation_strength",
        Enum(
            RecommendationStrength,
            name="recommendation_strength",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=RecommendationStrength.UNKNOWN,
        server_default=RecommendationStrength.UNKNOWN.value,
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

    Index("ix_brand_mentions_organization_id", "organization_id"),
    Index("ix_brand_mentions_project_id", "project_id"),
    Index("ix_brand_mentions_run_batch_id", "run_batch_id"),
    Index("ix_brand_mentions_prompt_run_id", "prompt_run_id"),
    Index("ix_brand_mentions_observation_id", "observation_id"),
    Index("ix_brand_mentions_extraction_result_id", "extraction_result_id"),
    Index("ix_brand_mentions_prompt_id", "prompt_id"),
    Index("ix_brand_mentions_platform_id", "platform_id"),
    Index("ix_brand_mentions_is_recommended", "is_recommended"),
    Index("ix_brand_mentions_sentiment", "sentiment"),
    Index("ix_brand_mentions_mention_type", "mention_type"),
)
