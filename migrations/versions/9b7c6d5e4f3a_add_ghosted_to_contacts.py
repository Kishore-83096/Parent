"""Add ghosted to contacts

Revision ID: 9b7c6d5e4f3a
Revises: f0a1c2d3e4b5
Create Date: 2026-06-04 19:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "9b7c6d5e4f3a"
down_revision = "f0a1c2d3e4b5"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("contacts", schema=None) as batch_op:
        batch_op.add_column(sa.Column("ghosted", sa.Boolean(), server_default=sa.false(), nullable=False))
        batch_op.alter_column("ghosted", server_default=None)


def downgrade():
    with op.batch_alter_table("contacts", schema=None) as batch_op:
        batch_op.drop_column("ghosted")
