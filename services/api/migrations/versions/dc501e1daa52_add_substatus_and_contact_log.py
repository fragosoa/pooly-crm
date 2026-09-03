"""add_substatus_and_contact_log

Revision ID: dc501e1daa52
Revises: 8187017da770
Create Date: 2026-08-26 00:00:00.000000

Picks up schema changes from the upstream prototype (synced from main):
a sub-status refinement per main status (Demo -> Por iniciar/En progreso/
Terminado, Cliente -> Activo/Inactivo, No Conversión -> Interés Futuro/
No Interés) and a simple contact-touchpoint log, separate from
historial_estados which only tracks status transitions.

Also renames the one status label that changed for existing rows this
DB already has: '1er Contacto' -> 'Contacto' (the new pipeline's spelling).
The other retired labels ('Interés Futuro', 'No Interés' as *main*
statuses) are left alone — no existing row uses them, and folding them
into 'Churned' vs 'No Conversión' automatically would be a guess this
migration shouldn't make.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'dc501e1daa52'
down_revision: Union[str, Sequence[str], None] = '8187017da770'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('crm_prospects', sa.Column('sub_status', sa.Text(), nullable=True))
    op.add_column('crm_prospects', sa.Column('sub_status_fecha', sa.Text(), nullable=True))
    op.add_column(
        'crm_prospects',
        sa.Column('contact_log', sa.JSON(), nullable=False, server_default='[]'),
    )
    op.execute("UPDATE crm_prospects SET status = 'Contacto' WHERE status = '1er Contacto'")


def downgrade() -> None:
    op.drop_column('crm_prospects', 'contact_log')
    op.drop_column('crm_prospects', 'sub_status_fecha')
    op.drop_column('crm_prospects', 'sub_status')
