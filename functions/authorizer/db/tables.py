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
    Float,
    schema,
    ARRAY,
    Date,
)

from db.base import Base
from db.database import Database

current_schema = f"{os.getenv('database_schema', None)}"
if not current_schema:
    raise ModuleNotFoundError("Schema not set")


class Users(Base):
    """
    Attribute types are the types of attributes that can be used in the system.
    All the attribute types are system defined and cannot be changed by the user.
    """

    __tablename__ = "users"
    __table_args__ = {"schema": current_schema}

    id = Column(String(36), primary_key=True, default=uuid.uuid4)
    username = Column(String(255), unique=True, index=True)
    password = Column(Text)
    is_verified = Column(Boolean, default=False)
    verification_token = Column(String(36), nullable=True, index=True)
    is_google = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    is_reset = Column(Boolean, default=False)
    reset_requested_at = Column(DateTime, default=None, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)


class Sessions(Base):
    __tablename__ = "sessions"
    __table_args__ = {"schema": current_schema}

    id = Column(String(36), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(36), ForeignKey(f"{current_schema}.users.id"), nullable=False, index=True)
    session = Column(String(36), nullable=False, default=uuid.uuid4)
    created_at = Column(DateTime, default=datetime.utcnow)
    expire_at = Column(DateTime, default=datetime.utcnow)


class DocumentTypesTable(Base):
    __tablename__ = "document_types"
    __table_args__ = {"schema": current_schema}

    id = Column(String(36), primary_key=True, unique=True, default=uuid.uuid4)
    name = Column(String(64), unique=True, nullable=False, index=True)
    document_type = Column(String(64), unique=True, nullable=False)
    mime_type = Column(String(255), unique=True, nullable=False)
    extensions = Column(ARRAY(String), unique=True, nullable=True)


class Documents(Base):
    __tablename__ = "documents"
    __table_args__ = {"schema": current_schema}

    id = Column(String(36), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(36), ForeignKey(f"{current_schema}.users.id"), nullable=False, index=True)
    document_type_id = Column(String(36), ForeignKey(f"{current_schema}.document_types.id"), nullable=False, index=True)
    file_name = Column(String(64), nullable=False, index=True)
    file_alias = Column(String(64), nullable=True)
    file_extension = Column(String(8), nullable=True)
    file_size_kb = Column(Float, default=0)
    page_count = Column(Integer, default=0)
    is_deleted = Column(Boolean, default=False)
    is_uploaded = Column(Boolean, default=False)
    is_opened = Column(Boolean, default=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)


class OCRProgress(Base):
    __tablename__ = "ocr_progress"
    __table_args__ = {"schema": current_schema}

    id = Column(String(36), primary_key=True, default=uuid.uuid4)
    document_id = Column(String(36), ForeignKey(f"{current_schema}.documents.id"), nullable=False, index=True)
    page_index = Column(Integer)
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, default=datetime.utcnow)


class AnnotationTypesTable(Base):
    __tablename__ = "annotation_types"
    __table_args__ = {"schema": current_schema}

    id = Column(String(36), primary_key=True, default=uuid.uuid4)
    name = Column(String(64), unique=True, nullable=False, index=True)
    display_name = Column(String(64), unique=True, nullable=False)
    is_enabled = Column(Boolean, default=True)
    is_insight = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)


class Annotations(Base):
    __tablename__ = "annotations"
    __table_args__ = {"schema": current_schema}

    id = Column(String(36), primary_key=True, default=uuid.uuid4)
    document_id = Column(String(36), ForeignKey(f"{current_schema}.documents.id"), nullable=False, index=True)
    annotation_type_id = Column(
        String(36), ForeignKey(f"{current_schema}.annotation_types.id"), nullable=False, index=True
    )
    status = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Chats(Base):
    __tablename__ = "chats"
    __table_args__ = {"schema": current_schema}

    id = Column(String(36), primary_key=True, default=uuid.uuid4)
    # enable cascade delete

    document_id = Column(String(36), ForeignKey(f"{current_schema}.documents.id"), nullable=False, index=True)
    chat_name = Column(String(64), nullable=False, index=True)
    chat_type = Column(String(64), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Models(Base):
    __tablename__ = "models"
    __table_args__ = {"schema": current_schema}

    id = Column(String(36), primary_key=True, default=uuid.uuid4)
    name = Column(String(64), unique=True, nullable=False, index=True)
    prompt_1k_cost = Column(Float, default=0)
    completion_1k_cost = Column(Float, default=0)


class APIKeys(Base):
    __tablename__ = "api_keys"
    __table_args__ = {"schema": current_schema}

    id = Column(String(36), primary_key=True, default=uuid.uuid4)
    service_key = Column(String(64), unique=True, nullable=False, index=True)
    api_key = Column(String(256), nullable=False)
    is_active = Column(Boolean, default=True)


class Queries(Base):
    __tablename__ = "queries"
    __table_args__ = {"schema": current_schema}

    id = Column(String(36), primary_key=True, default=uuid.uuid4)
    chat_id = Column(String(36), ForeignKey(f"{current_schema}.chats.id"), nullable=False, index=True)
    model_id = Column(String(36), ForeignKey(f"{current_schema}.models.id"), nullable=False, index=True)
    api_key_id = Column(String(36), ForeignKey(f"{current_schema}.api_keys.id"), nullable=False, index=True)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    prompt_1k_cost = Column(Float, default=0)
    completion_1k_cost = Column(Float, default=0)
    total_amount = Column(Float, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class UserAttributes(Base):
    __tablename__ = "user_attributes"
    __table_args__ = {"schema": current_schema}

    id = Column(String(36), primary_key=True, default=uuid.uuid4)
    attribute_name = Column(String(128), nullable=False)


class UserDetails(Base):
    __tablename__ = "user_details"
    __table_args__ = {"schema": current_schema}

    id = Column(String(36), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(36), ForeignKey(f"{current_schema}.users.id"), nullable=False, index=True)
    user_attribute_id = Column(
        String(36), ForeignKey(f"{current_schema}.user_attributes.id"), nullable=False, index=True
    )
    value = Column(String(256), nullable=True, index=True, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)


class UsageTypesTable(Base):
    __tablename__ = "usage_types"
    __table_args__ = {"schema": current_schema}

    id = Column(String(36), primary_key=True, default=uuid.uuid4)
    name = Column(String(128), nullable=False)
    display_name = Column(String(128), nullable=False)
    credits_per_unit = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)


class Subscriptions(Base):
    __tablename__ = "subscriptions"
    __table_args__ = {"schema": current_schema}

    id = Column(String(36), primary_key=True, default=uuid.uuid4)
    stripe_price_id = Column(String(36), nullable=False, index=True)
    name = Column(String(128), nullable=False)
    display_name = Column(String(128), nullable=False)
    description = Column(String(256), nullable=False)
    amount = Column(Float, nullable=False)
    # daily, monthly, yearly
    interval = Column(String(32), nullable=False)
    credits = Column(Float, default=0)
    details = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    is_popular = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)


# class SubscriptionLimits(Base):
#     __tablename__ = "subscriptions_limits"
#     __table_args__ = {"schema": current_schema}
#
#     id = Column(String(36), primary_key=True, default=uuid.uuid4)
#     subscription_id = Column(String(36), ForeignKey(f"{current_schema}.subscriptions.id"))
#     usage_type_id = Column(String(36), ForeignKey(f"{current_schema}.usage_types.id"))
#     limit = Column(Float, default=0)


class DailyUsage(Base):
    __tablename__ = "daily_usage"
    __table_args__ = {"schema": current_schema}

    id = Column(String(36), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(36), ForeignKey(f"{current_schema}.users.id"))
    usage_type_id = Column(String(36), ForeignKey(f"{current_schema}.usage_types.id"))
    units = Column(Float, nullable=False)
    credits = Column(Float, nullable=False)
    eod = Column(Boolean, default=False)
    date = Column(Date, default=datetime.date)
    timestamp = Column(DateTime, default=datetime.utcnow)


# class Balance(Base):
#     __tablename__ = "balance"
#     __table_args__ = {"schema": current_schema}
#
#     id = Column(String(36), primary_key=True, default=uuid.uuid4)
#     user_id = Column(String(36), ForeignKey(f"{current_schema}.users.id"), default=uuid.uuid4)
#     subscription_id = Column(String(36), ForeignKey(f"{current_schema}.subscriptions.id"), primary_key=True)
#     amount = Column(Float, default=0)


class Payments(Base):
    __tablename__ = "payments"
    __table_args__ = {"schema": current_schema}

    id = Column(String(36), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(36), ForeignKey(f"{current_schema}.users.id"))
    subscription_id = Column(String(36), ForeignKey(f"{current_schema}.subscriptions.id"))
    stripe_subscription_id = Column(String(36), nullable=True, default=None)
    stripe_customer_id = Column(String(18), nullable=True, default=None)
    subscribed_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)


class PaymentMethods(Base):
    __tablename__ = "payment_methods"
    __table_args__ = {"schema": current_schema}

    id = Column(String(36), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(36), ForeignKey(f"{current_schema}.users.id"))
    payment_method_id = Column(String(36), nullable=False, index=True)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


# class PaymentIntents(Base):
#     __tablename__ = "payment_intents"
#     __table_args__ = {"schema": current_schema}
#
#     id = Column(String(36), primary_key=True, default=uuid.uuid4)
#     user_id = Column(String(36), ForeignKey(f"{current_schema}.users.id"))
#     reference_no = Column(String(36), default=uuid.uuid4)
#     amount = Column(Float, default=0)
#     currency = Column(String(8), default="USD")
#     note = Column(String(256), default="")
#     made_at = Column(DateTime, default=datetime.utcnow)


def create_schema(engine, schema_name):
    if not engine.dialect.has_schema(engine, schema_name):
        engine.execute(schema.CreateSchema(schema_name))


def create_tables(engine, drop=False):
    if drop:
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def create_tables_with_keep_classes(engine, keep_classes, drop=False):
    # Extract table objects from keep_classes
    keep_tables = {cls.__table__ for cls in keep_classes}

    # Determine tables to operate on: those that are in the Base but not in the keep_tables set
    tables_to_operate_on = set(Base.metadata.tables.values()) - keep_tables

    if drop:
        for table in tables_to_operate_on:
            table.drop(engine, checkfirst=True)

    for table in tables_to_operate_on:
        table.create(engine, checkfirst=True)


def create_tables_with_create_classes(engine, table_classes, drop=False):
    if drop:
        for table_class in table_classes:
            table_class.__table__.drop(engine, checkfirst=True)

    for table_class in table_classes:
        table_class.__table__.create(engine, checkfirst=True)


def create_db():
    database = Database(echo=True)
    engine = database.get_engine()
    create_schema(engine, current_schema)
    create_tables(engine, drop=False)
    # create_tables_with_keep_classes(engine, [Users], drop=True)


if __name__ == "__main__":
    create_db()
