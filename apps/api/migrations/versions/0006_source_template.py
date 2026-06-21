import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sources",
        sa.Column("template", sa.String(), nullable=False, server_default="explainer"),
    )


def downgrade() -> None:
    op.drop_column("sources", "template")
