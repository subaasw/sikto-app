import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "media_assets",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("storage_key", sa.String(), nullable=True),
        sa.Column("tags", JSONB(), nullable=False, server_default="[]"),
        sa.Column("source", sa.String(), nullable=True),
        sa.Column("license", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_media_assets_kind", "media_assets", ["kind"])


def downgrade() -> None:
    op.drop_index("ix_media_assets_kind", table_name="media_assets")
    op.drop_table("media_assets")
