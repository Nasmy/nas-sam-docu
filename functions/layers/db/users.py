import csv
import logging
import os
import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    String,
    DateTime,
    Boolean,
    Integer,
    ForeignKey,
    Text,
)

from db.base import Base

class Users(Base):
    """
    Attribute types are the types of attributes that can be used in the system.
    All the attribute types are system defined and cannot be changed by the user.
    """

    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=uuid.uuid4())
    username = Column(String(255), unique=True, index=True)
    password = Column(Text)
    is_verified = Column(Boolean, default=False)
    verification_token = Column(String(36), nullable=True, index=True)
    is_active = Column(Boolean, default=True)
    is_reset = Column(Boolean, default=False)
    reset_requested_at = Column(DateTime, default=None, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

