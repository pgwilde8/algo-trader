# app/models/checkout_session.py

from app.db.base_class import Base
from sqlalchemy import Column, String, DateTime
from datetime import datetime

class CheckoutSession(Base):
    __tablename__ = "checkout_sessions"

    session_id = Column(String, primary_key=True, index=True)
    username = Column(String, nullable=False, index=True)
    bot_id = Column(String, nullable=False, index=True)  # e.g. "usdjpy"
    created_at = Column(DateTime, default=datetime.utcnow)

