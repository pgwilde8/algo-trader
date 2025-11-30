"""
ML Trade Execution Model
Stores trades executed based on ML signals
Links to ml_signal_history and optionally to bot_instances
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Numeric, DateTime, ForeignKey, Enum as PgEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base_class import Base
from app.models.enums import TradeSide


class MLTradeExecution(Base):
    __tablename__ = "ml_trade_executions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    signal_id = Column(UUID(as_uuid=True), ForeignKey("ml_signal_history.id"), nullable=False)
    bot_instance_id = Column(UUID(as_uuid=True), ForeignKey("bot_instances.id"), nullable=True)  # Optional if bot exists
    instrument = Column(String(30), nullable=False, index=True)  # e.g., 'EUR_USD', 'XAU_USD', 'BTC_USD'
    side = Column(PgEnum(TradeSide), nullable=False)  # 'buy' or 'sell'
    size = Column(Numeric(15, 8), nullable=False)  # Position size/units (increased for crypto precision)
    entry_price = Column(Numeric(15, 8), nullable=False)  # Increased precision for crypto, commodities, forex
    stop_loss = Column(Numeric(15, 8), nullable=True)
    take_profit = Column(Numeric(15, 8), nullable=True)
    exit_price = Column(Numeric(15, 8), nullable=True)
    pnl = Column(Numeric(12, 2), nullable=True)  # Profit/Loss
    status = Column(String(10), nullable=False, default="open")  # 'open', 'closed', 'stopped'
    broker_order_id = Column(String(100), nullable=True)  # OANDA order ID
    opened_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Relationships
    signal = relationship("MLSignalHistory", back_populates="ml_trade_executions")
    bot_instance = relationship("BotInstance", backref="ml_trade_executions")

    def __repr__(self):
        return f"<MLTradeExecution(id={self.id}, instrument={self.instrument}, side={self.side}, status={self.status})>"

