from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from database import Base  # Απλό, χωρίς try-except

class CreditTransaction(Base):
    __tablename__ = "credit_transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    type = Column(String, nullable=False)  # 'charge' ή 'use'
    amount = Column(Float, nullable=False)
    description = Column(String, nullable=True)

    timestamp = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="credit_transactions")
