import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as PgEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base_class import Base
from app.models.enums import BotStatus


class BotInstance(Base):
    __tablename__ = "bot_instances"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    broker_credentials_id = Column(UUID(as_uuid=True), ForeignKey("broker_credentials.id"), nullable=False)
    strategy_name = Column(String, nullable=False)
    asset_pair = Column(String, nullable=False)
    bot_status = Column(PgEnum(BotStatus), nullable=False, default=BotStatus.launched)
    docker_container_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="bot_instances")
    broker_credentials = relationship("BrokerCredentials", back_populates="bot_instances")
    trade_records = relationship("TradeRecord", back_populates="bot_instance")
    activity_snapshots = relationship("BotActivitySnapshot", back_populates="bot_instance")

