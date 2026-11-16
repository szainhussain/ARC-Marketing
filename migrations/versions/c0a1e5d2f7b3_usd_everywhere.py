"""ARC works in US dollars: move existing profiles and ad caps to USD

Revision ID: c0a1e5d2f7b3
Revises: 6f26a0de5734
"""
from alembic import op

revision = "c0a1e5d2f7b3"
down_revision = "6f26a0de5734"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("UPDATE business_profiles SET currency = 'USD'")
    op.execute("UPDATE ad_guardrails SET currency = 'USD'")


def downgrade():
    pass  # previous per-workspace currencies are not restored
