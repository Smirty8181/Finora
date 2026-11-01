"""Align ticket status values and persist Nova answer feedback."""
from alembic import op
import sqlalchemy as sa

revision = "0002_frontend_ticket_fields"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "tickets",
        sa.Column("nova_answer_wrong", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.execute("UPDATE tickets SET status = 'new' WHERE status = 'open'")
    op.execute("UPDATE tickets SET status = 'closed' WHERE status = 'resolved'")


def downgrade():
    op.execute("UPDATE tickets SET status = 'open' WHERE status = 'new'")
    op.execute("UPDATE tickets SET status = 'resolved' WHERE status = 'closed'")
    op.drop_column("tickets", "nova_answer_wrong")
