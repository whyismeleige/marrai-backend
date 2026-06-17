import enum
import uuid

from sqlalchemy import (
    Table,
    Column,
    UUID,
    String,
    CheckConstraint,
    Enum,
    DateTime,
    MetaData,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

metadata = MetaData()


class JobStatus(enum.Enum):
    PENDING = "pending"
    STARTED = "started"
    CRAWLING = "crawling"
    SCORING = "scoring"
    SUCCESS = "success"
    FAILURE = "failure"


jobs_table = Table(
    "jobs",
    metadata,
    Column("job_id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    Column("url", String(2048), nullable=False),
    Column("status", Enum(JobStatus), nullable=False, default=JobStatus.PENDING),
    Column("result", JSONB, nullable=True),
    Column("error_message", String(2048), nullable=True),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
    Column(
        "updated_at",
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    ),
    Column("completed_at", DateTime(timezone=True), nullable=True),
)
