"""add_backtest_tables

Revision ID: abc123def456
Revises: 4fbde05a2206
Create Date: 2026-01-04 21:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'abc123def456'
down_revision: Union[str, Sequence[str], None] = '4fbde05a2206'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - add backtest tables."""
    # Create backtests table
    op.create_table(
        'backtests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('strategy_id', sa.Integer(), nullable=False),
        sa.Column('connection_id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(length=50), nullable=False),
        sa.Column('start_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('timeframe', sa.String(length=10), nullable=False),
        sa.Column('initial_balance', sa.Float(), nullable=False),
        sa.Column('initial_cash', sa.Float(), nullable=False),
        sa.Column('final_balance', sa.Float(), nullable=False),
        sa.Column('final_cash', sa.Float(), nullable=False),
        sa.Column('total_pnl', sa.Float(), nullable=False),
        sa.Column('total_pnl_percent', sa.Float(), nullable=False),
        sa.Column('total_trades', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('winning_trades', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('losing_trades', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('win_rate', sa.Float(), nullable=True),
        sa.Column('avg_win', sa.Float(), nullable=True),
        sa.Column('avg_loss', sa.Float(), nullable=True),
        sa.Column('profit_factor', sa.Float(), nullable=True),
        sa.Column('max_drawdown', sa.Float(), nullable=True),
        sa.Column('max_drawdown_percent', sa.Float(), nullable=True),
        sa.Column('sharpe_ratio', sa.Float(), nullable=True),
        sa.Column('largest_win', sa.Float(), nullable=True),
        sa.Column('largest_loss', sa.Float(), nullable=True),
        sa.Column('avg_trade_duration_hours', sa.Float(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='completed'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['strategy_id'], ['strategies.id'], ),
        sa.ForeignKeyConstraint(['connection_id'], ['exchange_connections.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_backtests_strategy_id'), 'backtests', ['strategy_id'], unique=False)
    op.create_index(op.f('ix_backtests_connection_id'), 'backtests', ['connection_id'], unique=False)
    op.create_index(op.f('ix_backtests_created_at'), 'backtests', ['created_at'], unique=False)

    # Create backtest_trades table
    op.create_table(
        'backtest_trades',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('backtest_id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(length=50), nullable=False),
        sa.Column('side', sa.String(length=10), nullable=False),
        sa.Column('entry_price', sa.Float(), nullable=False),
        sa.Column('exit_price', sa.Float(), nullable=True),
        sa.Column('quantity', sa.Float(), nullable=False),
        sa.Column('entry_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('exit_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('pnl', sa.Float(), nullable=True),
        sa.Column('pnl_percent', sa.Float(), nullable=True),
        sa.Column('stop_loss', sa.Float(), nullable=True),
        sa.Column('take_profit', sa.Float(), nullable=True),
        sa.Column('risk_reward_ratio', sa.Float(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='open'),
        sa.ForeignKeyConstraint(['backtest_id'], ['backtests.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_backtest_trades_backtest_id'), 'backtest_trades', ['backtest_id'], unique=False)
    op.create_index(op.f('ix_backtest_trades_entry_time'), 'backtest_trades', ['entry_time'], unique=False)


def downgrade() -> None:
    """Downgrade schema - remove backtest tables."""
    op.drop_index(op.f('ix_backtest_trades_entry_time'), table_name='backtest_trades')
    op.drop_index(op.f('ix_backtest_trades_backtest_id'), table_name='backtest_trades')
    op.drop_table('backtest_trades')
    op.drop_index(op.f('ix_backtests_created_at'), table_name='backtests')
    op.drop_index(op.f('ix_backtests_connection_id'), table_name='backtests')
    op.drop_index(op.f('ix_backtests_strategy_id'), table_name='backtests')
    op.drop_table('backtests')

