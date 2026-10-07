"""adiciona meteorologia_localizacao

Revision ID: c420a200f2f2
Revises: 3b14f5bd26a5
Create Date: 2026-10-07

Etapa A do modulo Meteorologia: uma localizacao guardada por utilizador.
Gerada por `flask db migrate`; removido do autogenerate o bloco espurio
`alter_column utilizadores.is_admin` (deteccao de NULL local vs baseline,
sem efeito no esquema real).
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c420a200f2f2'
down_revision = '3b14f5bd26a5'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'meteorologia_localizacao',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(length=120), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('pais', sa.String(length=80), nullable=False),
        sa.Column('regiao', sa.String(length=120), nullable=True),
        sa.Column('timezone', sa.String(length=64), nullable=True),
        sa.Column('atualizada_em', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['utilizadores.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id'),
    )


def downgrade():
    op.drop_table('meteorologia_localizacao')
