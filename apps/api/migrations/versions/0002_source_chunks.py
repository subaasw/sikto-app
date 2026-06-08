import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "source_chunks",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("content", sa.String(), nullable=False),
        sa.Column("embedding", Vector(1536), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("source_chunks")
