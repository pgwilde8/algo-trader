# models/red_folder_event.py
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer
from app.db.base_class import Base

class RedFolderEvent(Base):
    __tablename__ = "red_folder_events"

    id = Column(Integer, primary_key=True)  # Matches existing table
    event_time = Column(DateTime, nullable=False)  # When the news event occurs
    currency = Column(String, nullable=False)  # e.g., "USD", "EUR"
    title = Column(String, nullable=False)  # e.g., "Non-Farm Payrolls", "FOMC Meeting"
    impact = Column(String, default="high")  # "high", "medium", "low"
    created_by = Column(Integer, nullable=True)  # Admin user who created it
    created_at = Column(DateTime, default=datetime.utcnow)  # When added to system

