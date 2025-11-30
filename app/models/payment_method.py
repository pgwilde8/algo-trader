import uuid
from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base_class import Base


class PaymentMethod(Base):
    __tablename__ = "payment_methods"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    brand = Column(String, nullable=False)          # e.g. "Visa", "Mastercard"
    last4 = Column(String, nullable=False)          # last 4 digits
    exp_month = Column(Integer, nullable=False)
    exp_year = Column(Integer, nullable=False)

    user = relationship("User", back_populates="payment_methods")

