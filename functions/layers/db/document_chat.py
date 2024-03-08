import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    String,
    DateTime,
)

from db.base import Base


class DocumentChat(Base):
    """
    Attribute types are the types of attributes that can be used in the system.
    All the attribute types are system defined and cannot be changed by the user.
    """

    __tablename__ = "document_chat"

    id = Column(String(36), primary_key=True, default=uuid.uuid4())
    document_id = Column(String(36), nullable=False, index=True)
    chat_id = Column(String(36), nullable=False, index=True)
    chat_name = Column(String(36), nullable=False, index=True)

    created_at = Column(DateTime, default=datetime.utcnow)
