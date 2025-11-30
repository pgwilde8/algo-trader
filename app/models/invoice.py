import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Enum as PgEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base_class import Base
from app.models.enums import InvoiceStatus


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    amount_paid = Column(Integer, nullable=False)
    paid_at = Column(DateTime, nullable=False)
    status = Column(PgEnum(InvoiceStatus), nullable=False)
    pdf_url = Column(String, nullable=True)

    user = relationship("User", back_populates="invoices")

