"""adiciona meteorologia_previsao_cache

Revision ID: a91e7c30d4b2
Revises: fd5793bc73bf
Create Date: 2026-10-18 19:05:00.000000

Cache da ultima previsao com sucesso por coordenadas (~1 km), usada como
fallback quando a API Open-Meteo esta em baixo. Uma linha por localizacao;
payload em JSON no formato devolvido por obter_previsao.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a91e7c30d4b2'
down_revision = 'fd5793bc73bf'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'meteorologia_previsao_cache',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('chave', sa.String(length=32), nullable=False),
        sa.Column('payload', sa.Text(), nullable=False),
        sa.Column('obtida_em', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_meteorologia_previsao_cache_chave'),
        'meteorologia_previsao_cache', ['chave'], unique=True)
    op.create_index(
        op.f('ix_meteorologia_previsao_cache_obtida_em'),
        'meteorologia_previsao_cache', ['obtida_em'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_meteorologia_previsao_cache_obtida_em'),
                  table_name='meteorologia_previsao_cache')
    op.drop_index(op.f('ix_meteorologia_previsao_cache_chave'),
                  table_name='meteorologia_previsao_cache')
    op.drop_table('meteorologia_previsao_cache')