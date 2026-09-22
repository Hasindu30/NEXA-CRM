from datetime import datetime, timezone
import uuid
from sqlalchemy import String, DateTime, ForeignKey, Index, CheckConstraint, ForeignKeyConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

class Person(Base):
    __tablename__ = "people"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid7)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    
    first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    job_title: Mapped[str | None] = mapped_column(String(100), nullable=True)
    
    company_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    __table_args__ = (
        # Tenant isolation composite FK. No CASCADE/SET NULL on DB level, handled transactionally.
        ForeignKeyConstraint(
            ["workspace_id", "company_id"],
            ["companies.workspace_id", "companies.id"],
            name="fk_people_workspace_id_company_id_companies"
        ),
        # Identity requirement
        CheckConstraint(
            "(first_name IS NOT NULL AND btrim(first_name) != '') OR "
            "(last_name IS NOT NULL AND btrim(last_name) != '') OR "
            "(email IS NOT NULL AND btrim(email) != '')",
            name="ck_people_identity_required"
        ),
        Index("ix_people_workspace_id_created_at_id", "workspace_id", created_at.desc(), id.desc()),
        Index("ix_people_workspace_id_company_id", "workspace_id", "company_id"),
    )
