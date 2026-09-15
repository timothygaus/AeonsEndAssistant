"""expedition battle attempts, configurable length, big pockets flag

Revision ID: a1b2c3d4e5f6
Revises: 19a4dc57fceb
Create Date: 2026-09-15 20:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '19a4dc57fceb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('expeditions', sa.Column('base_length', sa.Integer(), nullable=False, server_default='4'))
    op.add_column('expeditions', sa.Column('big_pockets', sa.Boolean(), nullable=False, server_default=sa.false()))

    # Big Pockets stops being a variant and becomes a banishing rule that can be
    # combined with any of the others.
    op.execute(
        "UPDATE expeditions SET big_pockets = true, variant = 'standard' "
        "WHERE variant = 'big-pockets'"
    )

    op.add_column('expedition_battles', sa.Column('attempt', sa.Integer(), nullable=False, server_default='1'))
    op.add_column('expedition_battles', sa.Column('locked', sa.Boolean(), nullable=False, server_default=sa.false()))

    op.create_table('expedition_battle_mages',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('battle_id', sa.Integer(), nullable=False),
    sa.Column('mage_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['battle_id'], ['expedition_battles.id'], ),
    sa.ForeignKeyConstraint(['mage_id'], ['breach_mages.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('expedition_battle_cards',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('battle_id', sa.Integer(), nullable=False),
    sa.Column('player_card_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['battle_id'], ['expedition_battles.id'], ),
    sa.ForeignKeyConstraint(['player_card_id'], ['player_cards.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    # A lost battle used to close its own row and leave nothing pending, which
    # made the expedition unresumable. Reopen an attempt for every such battle so
    # existing saves survive the upgrade.
    op.execute(
        """
        INSERT INTO expedition_battles (expedition_id, battle_number, attempt, nemesis_id, result, locked)
        SELECT lost.expedition_id, lost.battle_number, lost.attempt + 1, lost.nemesis_id, NULL, false
        FROM expedition_battles lost
        JOIN expeditions e ON e.id = lost.expedition_id
        WHERE lost.result = 'loss'
          AND e.status = 'active'
          AND NOT EXISTS (
              SELECT 1 FROM expedition_battles pending
              WHERE pending.expedition_id = lost.expedition_id
                AND pending.result IS NULL
          )
        """
    )

    # server_default was only needed to backfill existing rows.
    op.alter_column('expeditions', 'base_length', server_default=None)
    op.alter_column('expeditions', 'big_pockets', server_default=None)
    op.alter_column('expedition_battles', 'attempt', server_default=None)
    op.alter_column('expedition_battles', 'locked', server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DELETE FROM expedition_battles WHERE result IS NULL AND attempt > 1")
    op.drop_table('expedition_battle_cards')
    op.drop_table('expedition_battle_mages')
    op.drop_column('expedition_battles', 'locked')
    op.drop_column('expedition_battles', 'attempt')
    op.execute("UPDATE expeditions SET variant = 'big-pockets' WHERE big_pockets = true")
    op.drop_column('expeditions', 'big_pockets')
    op.drop_column('expeditions', 'base_length')
