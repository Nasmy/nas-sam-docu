import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    String,
    DateTime,
    Integer,
    Float,
)

from db.base import Base


class ChatCost(Base):
    """
    Attribute types are the types of attributes that can be used in the system.
    All the attribute types are system defined and cannot be changed by the user.
    """

    __tablename__ = "chat_cost"

    id = Column(String(36), primary_key=True, default=uuid.uuid4())
    user_id = Column(String(36), nullable=False, index=True)
    document_id = Column(String(36), nullable=False, index=True)
    chat_id = Column(String(36), nullable=False, index=True)
    query_id = Column(String(36), nullable=False, index=True)
    query_type = Column(String(64), nullable=False)
    model_name = Column(String(64), nullable=False)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    prompt_1k_cost = Column(Float, default=0)
    completion_1k_cost = Column(Float, default=0)
    total_amount = Column(Float, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
