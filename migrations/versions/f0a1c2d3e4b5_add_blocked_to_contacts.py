"""Add blocked to contacts

Revision ID: f0a1c2d3e4b5
Revises: 8d4c7b9a1f23
Create Date: 2026-05-05 15:20:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f0a1c2d3e4b5"
down_revision = "8d4c7b9a1f23"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("contacts", schema=None) as batch_op:
        batch_op.add_column(sa.Column("blocked", sa.Boolean(), server_default=sa.false(), nullable=False))
        batch_op.alter_column("blocked", server_default=None)


def downgrade():
    with op.batch_alter_table("contacts", schema=None) as batch_op:
        batch_op.drop_column("blocked")
