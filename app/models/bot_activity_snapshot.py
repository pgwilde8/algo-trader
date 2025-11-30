import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.db.base_class import Base


class BotActivitySnapshot(Base):
    __tablename__ = "bot_activity_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bot_instance_id = Column(UUID(as_uuid=True), ForeignKey("bot_instances.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    open_positions = Column(JSONB, nullable=True)  # or use Text if JSONB isn't available
    balance = Column(Numeric, nullable=False)
    pnl = Column(Numeric, nullable=False)
    notes = Column(Text, nullable=True)

    bot_instance = relationship("BotInstance", back_populates="activity_snapshots")

