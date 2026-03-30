"""Add yandex delivery fields to orders

Revision ID: a1b2c3d4e5f6
Revises: 53047893116c
Create Date: 2026-03-27 00:20:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '53047893116c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column('orders', sa.Column('yandex_request_id', sa.String(), nullable=True))
    op.add_column('orders', sa.Column('yandex_status', sa.String(), nullable=True))
    op.add_column('orders', sa.Column('yandex_offer_id', sa.String(), nullable=True))
    op.add_column('orders', sa.Column('delivery_cost', sa.Integer(), nullable=True, server_default='0'))

def downgrade() -> None:
    op.drop_column('orders', 'delivery_cost')
    op.drop_column('orders', 'yandex_offer_id')
    op.drop_column('orders', 'yandex_status')
    op.drop_column('orders', 'yandex_request_id')
