"""create remove query type

Revision ID: 48a929cf359d
Revises: 8b3a4a73ab6a
Create Date: 2023-09-19 01:00:05.265501

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "48a929cf359d"
down_revision: Union[str, None] = "8b3a4a73ab6a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("queries", "query_type", schema="test")


def downgrade() -> None:
    op.add_column("queries", sa.Column("query_type", sa.String(length=64), nullable=False), schema="test")
