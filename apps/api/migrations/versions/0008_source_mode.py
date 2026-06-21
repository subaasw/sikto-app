import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sources",
        sa.Column("mode", sa.String(), nullable=False, server_default="auto"),
    )


def downgrade() -> None:
    op.drop_column("sources", "mode")
