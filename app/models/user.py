# app/models/user.py

import uuid
from sqlalchemy import Column, String, TIMESTAMP, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base_class import Base
from app.models.enums import UserRole

class User(Base):
    __tablename__ = "users"

    id: uuid.UUID = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email: str = Column(String, unique=True, index=True, nullable=False)
    username: str | None = Column(String, nullable=True)
    phone: str | None = Column(String, nullable=True)
    stripe_customer_id: str = Column(String, nullable=False)
    password_hash: str = Column(String, nullable=False)
    role: str = Column(Enum(UserRole), default=UserRole.user, nullable=False)
    created_at = Column(TIMESTAMP, server_default="now()", nullable=False)

    # Relationships
    broker_credentials = relationship(
        "BrokerCredentials",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    bot_instances = relationship(
        "BotInstance",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    subscriptions = relationship(
        "Subscription",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    payment_methods = relationship(
        "PaymentMethod",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    invoices = relationship(
        "Invoice",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    admin_logs = relationship(
        "AdminActionLog",
        back_populates="admin_user",
        cascade="all, delete-orphan",
    )
    support_tickets = relationship(
        "SupportTicket",
        back_populates="user",
        cascade="all, delete-orphan",
    )

