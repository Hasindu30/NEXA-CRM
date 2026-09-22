"""crm_core

Revision ID: a1b2c3d4e5f6
Revises: fc6017f00612
Create Date: 2026-09-22 08:45:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = 'fc6017f00612' # This assumes Phase 6 migration was fc6017f00612
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create companies table
    op.create_table('companies',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('workspace_id', sa.Uuid(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('domain', sa.String(length=255), nullable=True),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('website', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], name=op.f('fk_companies_workspace_id_workspaces'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_companies')),
        sa.UniqueConstraint('workspace_id', 'id', name=op.f('uq_companies_workspace_id_id'))
    )
    op.create_index(op.f('ix_companies_workspace_id_created_at_id'), 'companies', ['workspace_id', sa.text('created_at DESC'), sa.text('id DESC')], unique=False)

    # 2. Create people table
    op.create_table('people',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('workspace_id', sa.Uuid(), nullable=False),
        sa.Column('first_name', sa.String(length=100), nullable=True),
        sa.Column('last_name', sa.String(length=100), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('job_title', sa.String(length=100), nullable=True),
        sa.Column('company_id', sa.Uuid(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], name=op.f('fk_people_workspace_id_workspaces'), ondelete='CASCADE'),
        # NO ON DELETE SET NULL here, handled transactionally
        sa.ForeignKeyConstraint(['workspace_id', 'company_id'], ['companies.workspace_id', 'companies.id'], name=op.f('fk_people_workspace_id_company_id_companies')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_people')),
        sa.CheckConstraint(
            "(first_name IS NOT NULL AND btrim(first_name) != '') OR "
            "(last_name IS NOT NULL AND btrim(last_name) != '') OR "
            "(email IS NOT NULL AND btrim(email) != '')",
            name=op.f('ck_people_identity_required')
        )
    )
    op.create_index(op.f('ix_people_workspace_id_created_at_id'), 'people', ['workspace_id', sa.text('created_at DESC'), sa.text('id DESC')], unique=False)
    op.create_index(op.f('ix_people_workspace_id_company_id'), 'people', ['workspace_id', 'company_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_people_workspace_id_company_id'), table_name='people')
    op.drop_index(op.f('ix_people_workspace_id_created_at_id'), table_name='people')
    op.drop_table('people')
    
    op.drop_index(op.f('ix_companies_workspace_id_created_at_id'), table_name='companies')
    op.drop_table('companies')
