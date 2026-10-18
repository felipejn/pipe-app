"""substitui rastreio Mailjet dos convites por Zoho

Revision ID: fd5793bc73bf
Revises: d7a4c91e2f60
Create Date: 2026-10-18 12:07:20.006257

"""
from alembic import op
import sqlalchemy as sa


# Identificadores da revisão, usados pelo Alembic.
revision = 'fd5793bc73bf'
down_revision = 'd7a4c91e2f60'
branch_labels = None
depends_on = None


def upgrade():
    # Normaliza os estados Mailjet existentes antes de remover o histórico.
    op.execute("UPDATE convites SET email_estado = 'enviado' "
               "WHERE email_estado IN ('aceite', 'sent', 'delivered', 'expanded', 'opened', 'clicked')")
    op.execute("UPDATE convites SET email_estado = 'falhou' "
               "WHERE email_estado IN ('softbounced', 'bounced', 'failed', 'blocked', 'abuse')")
    with op.batch_alter_table('convites', schema=None) as batch_op:
        batch_op.alter_column(
            'mailjet_message_id',
            new_column_name='email_message_id',
            existing_type=sa.String(length=20),
            type_=sa.String(length=128),
            existing_nullable=True,
        )
        batch_op.drop_column('email_verificado_em')



def downgrade():
    # Repõe as colunas antigas para permitir reverter a migration.
    with op.batch_alter_table('convites', schema=None) as batch_op:
        batch_op.add_column(sa.Column('mailjet_message_id', sa.VARCHAR(length=20), nullable=True))
        batch_op.add_column(sa.Column('email_verificado_em', sa.DATETIME(), nullable=True))
        batch_op.drop_column('email_message_id')
