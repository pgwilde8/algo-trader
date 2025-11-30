"""
ML Model Performance Model
Tracks model accuracy and performance metrics over time
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Numeric, DateTime, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base_class import Base


class MLModelPerformance(Base):
    __tablename__ = "ml_model_performance"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    signal_id = Column(UUID(as_uuid=True), ForeignKey("ml_signal_history.id"), nullable=False)
    instrument = Column(String(30), nullable=False, index=True)  # e.g., 'EUR_USD', 'XAU_USD', 'BTC_USD'
    model_name = Column(String(150), nullable=False)  # e.g., 'EUR_USD_xgboost_seed43', 'BTC_USD_lstm_v2'
    predicted_direction = Column(String(10), nullable=False)  # 'BUY', 'SELL', 'NEUTRAL'
    predicted_probability = Column(Numeric(5, 3), nullable=False)  # Model's prediction probability
    actual_direction = Column(String(10), nullable=True)  # Actual price direction (filled after validation)
    actual_price_change = Column(Numeric(10, 6), nullable=True)  # Actual price change percentage (increased precision)
    was_correct = Column(Boolean, nullable=True)  # True if prediction was correct
    timestamp = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    validated_at = Column(DateTime(timezone=True), nullable=True)  # When actual result was recorded

    # Relationships
    signal = relationship("MLSignalHistory", backref="model_performances")

    def __repr__(self):
        return f"<MLModelPerformance(id={self.id}, instrument={self.instrument}, model={self.model_name}, was_correct={self.was_correct})>"

