"""regista ultimo envio do resumo diario

Revision ID: 8f3b90a1c2d4
Revises: 3058f716df40
"""
from alembic import op
import sqlalchemy as sa

revision = '8f3b90a1c2d4'
down_revision = '3058f716df40'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('resumo_diario_configuracoes', sa.Column('ultimo_envio', sa.Date(), nullable=True))


def downgrade():
    op.drop_column('resumo_diario_configuracoes', 'ultimo_envio')
