from sqlalchemy import Column, String, DateTime, Boolean, Integer
from datetime import datetime

from app.db.base_class import Base

class TrialUser(Base):
    __tablename__ = 'trial_users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    trial_start = Column(DateTime, default=datetime.utcnow)
    trial_end = Column(DateTime)
    is_active = Column(Boolean, default=True)
    oanda_account_id = Column(String)
    oanda_api_key = Column(String)
    mode = Column(String, default='practice')  # practice/live
    bot_id = Column(String, default='usdjpy-trial')
    password_hash = Column(String)  # Add password_hash column

