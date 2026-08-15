"""merge workflow and repair_order heads

Revision ID: 28f68e893c13
Revises: 14dbb8904c17, 35acb890def4
Create Date: 2026-08-09 08:37:27.497442

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '28f68e893c13'
down_revision: Union[str, Sequence[str], None] = ('14dbb8904c17', '35acb890def4')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
