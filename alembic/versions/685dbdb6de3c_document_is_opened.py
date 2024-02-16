"""document is opened

Revision ID: 685dbdb6de3c
Revises: 48a929cf359d
Create Date: 2023-10-16 21:49:41.923572

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "685dbdb6de3c"
down_revision: Union[str, None] = "48a929cf359d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("is_opened", sa.Boolean(), nullable=True), schema="test")


def downgrade() -> None:
    op.drop_column("documents", "is_opened", schema="test")
