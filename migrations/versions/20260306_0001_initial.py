"""initial lifecycle policy engine schema

Revision ID: 20260306_0001
Revises:
Create Date: 2026-03-06 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '20260306_0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'assets',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True, nullable=False),
        sa.Column('asset_type', sa.Text(), nullable=False),
        sa.Column('vendor', sa.Text(), nullable=True),
        sa.Column('model', sa.Text(), nullable=True),
        sa.Column('environment', sa.Text(), nullable=True),
        sa.Column('hostname', sa.Text(), nullable=True),
        sa.Column('identifiers', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('first_seen_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        'component_types',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True, nullable=False),
        sa.Column('key', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.UniqueConstraint('key', name='uq_component_types_key'),
    )
    op.create_table(
        'observations',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True, nullable=False),
        sa.Column('asset_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('assets.id', ondelete='CASCADE'), nullable=False),
        sa.Column('component_type_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('component_types.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('version', sa.Text(), nullable=False),
        sa.Column('observed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('source', sa.Text(), nullable=False),
        sa.Column('raw', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.UniqueConstraint('asset_id', 'component_type_id', 'observed_at', 'version', name='uq_observations_asset_component_seen_version'),
    )
    op.create_table(
        'policies',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True, nullable=False),
        sa.Column('component_type_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('component_types.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('asset_type', sa.Text(), nullable=True),
        sa.Column('vendor', sa.Text(), nullable=True),
        sa.Column('model', sa.Text(), nullable=True),
        sa.Column('environment', sa.Text(), nullable=True),
        sa.Column('version', sa.Text(), nullable=False),
        sa.Column('match_mode', sa.Text(), nullable=False, server_default='exact'),
        sa.Column('lifecycle_tier', sa.Text(), nullable=False),
        sa.Column('effective_from', sa.DateTime(timezone=True), nullable=False),
        sa.Column('effective_to', sa.DateTime(timezone=True), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.Text(), nullable=True),
    )
    op.create_table(
        'evaluations',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True, nullable=False),
        sa.Column('asset_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('assets.id', ondelete='CASCADE'), nullable=False),
        sa.Column('component_type_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('component_types.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('observed_version', sa.Text(), nullable=False),
        sa.Column('lifecycle_tier', sa.Text(), nullable=False),
        sa.Column('matched_policy_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('policies.id', ondelete='SET NULL'), nullable=True),
        sa.Column('evaluated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('rationale', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    )
    op.create_table(
        'ingestion_runs',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True, nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.Text(), nullable=False),
        sa.Column('source', sa.Text(), nullable=False),
        sa.Column('stats', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('error', sa.Text(), nullable=True),
    )
    op.create_table(
        'policy_audit_log',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True, nullable=False),
        sa.Column('policy_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('policies.id', ondelete='CASCADE'), nullable=False),
        sa.Column('actor', sa.Text(), nullable=True),
        sa.Column('action', sa.Text(), nullable=False),
        sa.Column('diff', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('at', sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('policy_audit_log')
    op.drop_table('ingestion_runs')
    op.drop_table('evaluations')
    op.drop_table('policies')
    op.drop_table('observations')
    op.drop_table('component_types')
    op.drop_table('assets')
