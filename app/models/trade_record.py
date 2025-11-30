import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Numeric, Enum as PgEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base_class import Base
from app.models.enums import TradeSide


class TradeRecord(Base):
    __tablename__ = "trade_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bot_instance_id = Column(UUID(as_uuid=True), ForeignKey("bot_instances.id"), nullable=False)
    broker_order_id = Column(String, nullable=True)
    instrument = Column(String, nullable=False)  # e.g. "XAUUSD"
    side = Column(PgEnum(TradeSide), nullable=False)
    size = Column(Numeric, nullable=False)
    price = Column(Numeric, nullable=False)
    timestamp = Column(DateTime, nullable=False)

    bot_instance = relationship("BotInstance", back_populates="trade_records")

