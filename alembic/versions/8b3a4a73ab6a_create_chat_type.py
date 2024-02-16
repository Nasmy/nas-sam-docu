"""create chat type

Revision ID: 8b3a4a73ab6a
Revises: 
Create Date: 2023-09-18 23:10:03.885415

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8b3a4a73ab6a"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("chats", sa.Column("chat_type", sa.String(length=64), nullable=True), schema="test")


def downgrade() -> None:
    op.drop_column("chats", "chat_type", schema="test")
