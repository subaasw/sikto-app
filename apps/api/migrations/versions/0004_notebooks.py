import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notebooks",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.add_column(
        "sources",
        sa.Column("notebook_id", sa.Uuid(), sa.ForeignKey("notebooks.id"), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("sources", "notebook_id")
    op.drop_table("notebooks")
