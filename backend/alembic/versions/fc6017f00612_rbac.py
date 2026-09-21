"""rbac

Revision ID: fc6017f00612
Revises: aa244a8b436f
Create Date: 2026-09-21 22:57:52.302619

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fc6017f00612'
down_revision: Union[str, Sequence[str]] = 'aa244a8b436f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add role column as nullable initially
    op.add_column('workspace_members', sa.Column('role', sa.String(length=50), nullable=True))

    # 2. Precondition Verification: every workspace must have exactly ONE membership
    conn = op.get_bind()
    workspaces = conn.execute(sa.text("SELECT id FROM workspaces")).fetchall()

    for ws in workspaces:
        ws_id = ws[0]
        member_count = conn.execute(
            sa.text("SELECT COUNT(*) FROM workspace_members WHERE workspace_id = :id"),
            {"id": ws_id}
        ).scalar()
        if member_count != 1:
            raise Exception(
                f"Workspace {ws_id} has {member_count} members. "
                "Aborting migration to prevent guessing historical ownership."
            )

    # 3. Treat singleton memberships as original creator -> role = 'owner'
    conn.execute(sa.text("UPDATE workspace_members SET role = 'owner'"))

    # 4. Alter role to NOT NULL with server_default='member'
    op.alter_column(
        'workspace_members', 'role',
        existing_type=sa.String(length=50),
        nullable=False,
        server_default='member'
    )

    # 5. Add CHECK constraint.
    # op.f() marks the name as already convention-resolved so Alembic does not
    # apply ck_%(table_name)s_%(constraint_name)s a second time.
    # Final DB name: ck_workspace_members_role_allowed
    op.create_check_constraint(
        op.f("ck_workspace_members_role_allowed"),
        "workspace_members",
        "role IN ('owner', 'admin', 'member')",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("ck_workspace_members_role_allowed"),
        "workspace_members",
        type_="check",
    )
    op.drop_column('workspace_members', 'role')
