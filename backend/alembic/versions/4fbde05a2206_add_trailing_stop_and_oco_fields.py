"""add_trailing_stop_and_oco_fields

Revision ID: 4fbde05a2206
Revises: f48e5002e1fc
Create Date: 2026-01-04 18:36:15.851857

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4fbde05a2206'
down_revision: Union[str, Sequence[str], None] = 'f48e5002e1fc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - add trailing stop and OCO order fields."""
    # Add trailing stop fields to positions table
    op.add_column('positions', sa.Column('trailing_stop_enabled', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('positions', sa.Column('trailing_stop_percent', sa.Float(), nullable=True))
    op.add_column('positions', sa.Column('trailing_stop_trigger_price', sa.Float(), nullable=True))
    op.add_column('positions', sa.Column('stop_loss_order_id', sa.Integer(), nullable=True))
    op.add_column('positions', sa.Column('take_profit_order_id', sa.Integer(), nullable=True))
    
    # Add OCO order fields to orders table
    op.add_column('orders', sa.Column('oco_group_id', sa.String(length=100), nullable=True))
    op.add_column('orders', sa.Column('related_order_id', sa.Integer(), nullable=True))
    
    # Update order_type to support new types (stop_market, oco)
    # Note: The column already exists as VARCHAR(20) - application code handles new types


def downgrade() -> None:
    """Downgrade schema - remove trailing stop and OCO order fields."""
    # Remove OCO fields from orders table
    op.drop_column('orders', 'related_order_id')
    op.drop_column('orders', 'oco_group_id')
    
    # Remove trailing stop fields from positions table
    op.drop_column('positions', 'take_profit_order_id')
    op.drop_column('positions', 'stop_loss_order_id')
    op.drop_column('positions', 'trailing_stop_trigger_price')
    op.drop_column('positions', 'trailing_stop_percent')
    op.drop_column('positions', 'trailing_stop_enabled')
