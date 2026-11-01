"""Create chat, ticket, and unanswered-question tables."""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "chat_sessions",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "tickets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.String(length=64), sa.ForeignKey("chat_sessions.id"), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="open"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_tickets_session_id", "tickets", ["session_id"])
    op.create_index("ix_tickets_status", "tickets", ["status"])
    op.create_table(
        "chat_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.String(length=64), sa.ForeignKey("chat_sessions.id"), nullable=False),
        sa.Column("ticket_id", sa.Integer(), sa.ForeignKey("tickets.id"), nullable=True),
        sa.Column("sender", sa.String(length=16), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_chat_messages_session_id", "chat_messages", ["session_id"])
    op.create_index("ix_chat_messages_ticket_id", "chat_messages", ["ticket_id"])
    op.create_table(
        "unanswered_questions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.String(length=64), sa.ForeignKey("chat_sessions.id"), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_unanswered_questions_session_id", "unanswered_questions", ["session_id"])


def downgrade():
    op.drop_index("ix_unanswered_questions_session_id", table_name="unanswered_questions")
    op.drop_table("unanswered_questions")
    op.drop_index("ix_chat_messages_ticket_id", table_name="chat_messages")
    op.drop_index("ix_chat_messages_session_id", table_name="chat_messages")
    op.drop_table("chat_messages")
    op.drop_index("ix_tickets_status", table_name="tickets")
    op.drop_index("ix_tickets_session_id", table_name="tickets")
    op.drop_table("tickets")
    op.drop_table("chat_sessions")
