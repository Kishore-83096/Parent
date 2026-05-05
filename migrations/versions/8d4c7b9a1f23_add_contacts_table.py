"""Add contacts table

Revision ID: 8d4c7b9a1f23
Revises: 2a191fdd6298
Create Date: 2026-05-05 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "8d4c7b9a1f23"
down_revision = "2a191fdd6298"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "contacts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_user_id", sa.Integer(), nullable=False),
        sa.Column("contact_user_id", sa.Integer(), nullable=False),
        sa.Column("alias_name", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["contact_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("owner_user_id", "contact_user_id", name="uq_contacts_owner_contact"),
    )
    with op.batch_alter_table("contacts", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_contacts_owner_user_id"), ["owner_user_id"], unique=False)


def downgrade():
    with op.batch_alter_table("contacts", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_contacts_owner_user_id"))

    op.drop_table("contacts")
