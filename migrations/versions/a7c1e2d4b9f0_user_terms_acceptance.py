"""user terms acceptance

Revision ID: a7c1e2d4b9f0
Revises: f3b22abec84e
Create Date: 2026-11-05 15:00:00

"""
from alembic import op
import sqlalchemy as sa


revision = 'a7c1e2d4b9f0'
down_revision = 'f3b22abec84e'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('terms_version', sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column('terms_accepted_at', sa.DateTime(timezone=True), nullable=True))


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('terms_accepted_at')
        batch_op.drop_column('terms_version')
