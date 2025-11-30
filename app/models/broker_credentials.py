import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as PgEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base_class import Base
from app.models.enums import BrokerName, Environment


class BrokerCredentials(Base):
    __tablename__ = "broker_credentials"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    broker_name = Column(PgEnum(BrokerName), nullable=False)
    environment = Column(PgEnum(Environment), nullable=False)
    account_id = Column(String, nullable=True)
    api_key = Column(String, nullable=False)
    api_secret = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="broker_credentials")
    bot_instances = relationship("BotInstance", back_populates="broker_credentials")

