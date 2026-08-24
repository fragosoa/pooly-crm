"""create_crm_prospects

Revision ID: 8187017da770
Revises:
Create Date: 2026-08-23 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '8187017da770'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # id is client-generated (matches the frontend's existing uid()) so the
    # original prototype's records keep their identity across the migration
    # to Postgres — no reconciliation needed between local state and the DB.
    op.create_table(
        'crm_prospects',
        sa.Column('id',                     sa.Text(),      nullable=False),
        sa.Column('empresa',                sa.Text(),      nullable=False),
        sa.Column('categoria',              sa.Text(),      nullable=True),
        sa.Column('ig',                     sa.Text(),      nullable=True),
        sa.Column('ciudad',                 sa.Text(),      nullable=True),
        sa.Column('prioridad',              sa.Text(),      nullable=True),
        sa.Column('status',                 sa.Text(),      nullable=False,
                  server_default='Pendiente'),
        sa.Column('contacto',               sa.Text(),      nullable=True),
        sa.Column('canal',                  sa.Text(),      nullable=True,
                  server_default='Instagram'),
        # Dates come from the frontend as ISO strings or '' (unset) — kept as
        # free-form text rather than DATE to avoid empty-string/NULL friction.
        sa.Column('ultimo_contacto',        sa.Text(),      nullable=True),
        sa.Column('email',                  sa.Text(),      nullable=True),
        sa.Column('whatsapp',               sa.Text(),      nullable=True),
        sa.Column('email_empresa',          sa.Text(),      nullable=True),
        sa.Column('whatsapp_empresa',       sa.Text(),      nullable=True),
        sa.Column('notas',                  sa.Text(),      nullable=True),
        sa.Column('fecha_primer_contacto',  sa.Text(),      nullable=True),
        sa.Column('proxima_accion',         sa.Text(),      nullable=True),
        sa.Column('fecha_proxima_accion',   sa.Text(),      nullable=True),
        sa.Column('historial_estados',      sa.JSON(),      nullable=False,
                  server_default='[]'),
        sa.Column('plantilla_enviada',      sa.Boolean(),   nullable=False,
                  server_default='false'),
        sa.Column('plantilla_override',     sa.Text(),      nullable=True),
        sa.Column('plantilla_texto',        sa.Text(),      nullable=True),
        sa.Column('created_at',             sa.TIMESTAMP(), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('updated_at',             sa.TIMESTAMP(), nullable=False,
                  server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('crm_prospects_status_idx', 'crm_prospects', ['status'])
    op.create_index('crm_prospects_categoria_idx', 'crm_prospects', ['categoria'])


def downgrade() -> None:
    op.drop_index('crm_prospects_categoria_idx', table_name='crm_prospects')
    op.drop_index('crm_prospects_status_idx', table_name='crm_prospects')
    op.drop_table('crm_prospects')
