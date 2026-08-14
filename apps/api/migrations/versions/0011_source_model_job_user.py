import sqlalchemy as sa
from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sources", sa.Column("model", sa.String(), nullable=True))
    op.add_column("jobs", sa.Column("user_id", sa.Uuid(), nullable=True))
    op.create_index("ix_jobs_user_id", "jobs", ["user_id"])
    op.create_foreign_key("fk_jobs_user_id", "jobs", "users", ["user_id"], ["id"])


def downgrade() -> None:
    op.drop_constraint("fk_jobs_user_id", "jobs", type_="foreignkey")
    op.drop_index("ix_jobs_user_id", table_name="jobs")
    op.drop_column("jobs", "user_id")
    op.drop_column("sources", "model")
