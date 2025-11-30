from datetime import datetime
from sqlalchemy import Column, String, DateTime
from app.db.base_class import Base

class SystemSettings(Base):
    __tablename__ = "system_settings"

    key = Column(String, primary_key=True)  # e.g. "maintenance_mode"
    value = Column(String, nullable=False)  # e.g. "true"
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

