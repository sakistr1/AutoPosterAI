from sqlalchemy import Column, Integer, String, Boolean, Text
from sqlalchemy.orm import relationship

from database import Base

from .credit_transaction import CreditTransaction

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)

    woocommerce_url = Column(String, nullable=True)
    consumer_key = Column(String, nullable=True)
    consumer_secret = Column(String, nullable=True)
    
    sync_url = Column(String, nullable=True)  # <-- Πρόσθεσε αυτό το πεδίο

    credits = Column(Integer, default=10)

    products = relationship("Product", back_populates="owner", cascade="all, delete-orphan")
    posts = relationship("Post", back_populates="owner", cascade="all, delete-orphan")
    credit_transactions = relationship("CreditTransaction", back_populates="user", cascade="all, delete-orphan")
    templates = relationship("Template", back_populates="owner", cascade="all, delete-orphan")  # Νέα σχέση
