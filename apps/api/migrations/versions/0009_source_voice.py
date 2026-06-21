import sqlalchemy as sa
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sources",
        sa.Column("voice", sa.String(), nullable=False, server_default="male"),
    )


def downgrade() -> None:
    op.drop_column("sources", "voice")
