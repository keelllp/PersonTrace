"""add fk ondelete cascade

Revision ID: 5559d3176fae
Revises: a25f78e0f83f
Create Date: 2026-07-11 13:42:31.322054

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5559d3176fae'
down_revision: Union[str, Sequence[str], None] = 'a25f78e0f83f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint("jobs_user_id_fkey", "jobs", type_="foreignkey")
    op.create_foreign_key(
        "jobs_user_id_fkey", "jobs", "users", ["user_id"], ["id"], ondelete="CASCADE"
    )
    op.drop_constraint("persons_job_id_fkey", "persons", type_="foreignkey")
    op.create_foreign_key(
        "persons_job_id_fkey", "persons", "jobs", ["job_id"], ["id"], ondelete="CASCADE"
    )
    op.drop_constraint("sightings_person_id_fkey", "sightings", type_="foreignkey")
    op.create_foreign_key(
        "sightings_person_id_fkey", "sightings", "persons", ["person_id"], ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("sightings_person_id_fkey", "sightings", type_="foreignkey")
    op.create_foreign_key(
        "sightings_person_id_fkey", "sightings", "persons", ["person_id"], ["id"]
    )
    op.drop_constraint("persons_job_id_fkey", "persons", type_="foreignkey")
    op.create_foreign_key("persons_job_id_fkey", "persons", "jobs", ["job_id"], ["id"])
    op.drop_constraint("jobs_user_id_fkey", "jobs", type_="foreignkey")
    op.create_foreign_key("jobs_user_id_fkey", "jobs", "users", ["user_id"], ["id"])
