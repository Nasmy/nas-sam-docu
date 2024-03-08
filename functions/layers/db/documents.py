import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    String,
    DateTime,
    Boolean,
    Integer,
)

from db.base import Base


class Documents(Base):
    """
    Attribute types are the types of attributes that can be used in the system.
    All the attribute types are system defined and cannot be changed by the user.
    """

    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=uuid.uuid4())
    user_id = Column(String(36), nullable=False, index=True)
    document_id = Column(String(36), nullable=False, index=True)
    document_type = Column(String(36), nullable=False)
    file_name = Column(String(255), nullable=False, index=True)
    file_alias = Column(String(255), nullable=True)
    file_extension = Column(String(8), nullable=True)
    mime_type = Column(String(255), nullable=True)
    page_count = Column(Integer, default=0)
    is_deleted = Column(Boolean, default=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
