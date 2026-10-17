"""adiciona nome próprio e apelido aos utilizadores

Revision ID: d7a4c91e2f60
Revises: c420a200f2f2
Create Date: 2026-10-17
"""
from alembic import op
import sqlalchemy as sa


revision = 'd7a4c91e2f60'
down_revision = '8f3b90a1c2d4'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('utilizadores', sa.Column('nome', sa.String(length=80), nullable=True))
    op.add_column('utilizadores', sa.Column('apelido', sa.String(length=80), nullable=True))


def downgrade():
    op.drop_column('utilizadores', 'apelido')
    op.drop_column('utilizadores', 'nome')
