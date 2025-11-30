# app/models/admin_action_log.py

import uuid
from sqlalchemy import Column, String, ForeignKey, DateTime, Enum, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.models.enums import AdminActionTargetType
from app.db.base_class import Base

class AdminActionLog(Base):
    __tablename__ = "admin_action_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    admin_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    action = Column(Text, nullable=False)
    target_type = Column(Enum(AdminActionTargetType), nullable=False)
    target_id = Column(UUID(as_uuid=True), nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    admin_user = relationship("User", back_populates="admin_logs")

    def __repr__(self):
        return f"<AdminActionLog(id={self.id}, action={self.action}, target_type={self.target_type}, target_id={self.target_id})>"

