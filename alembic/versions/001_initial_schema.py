"""initial schema

Revision ID: 001
Revises: 
Create Date: 2026-07-02

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column('email', sa.Text(), nullable=False, unique=True),
        sa.Column('hashed_password', sa.Text(), nullable=False),
        sa.Column('full_name', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text("TRUE")),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index('ix_users_email', 'users', ['email'])

    op.create_table(
        'refresh_tokens',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('token_hash', sa.Text(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked', sa.Boolean(), server_default=sa.text("FALSE")),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index('ix_refresh_tokens_user_id', 'refresh_tokens', ['user_id'])
    op.create_index('ix_refresh_tokens_token_hash', 'refresh_tokens', ['token_hash'])

    op.create_table(
        'documents',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('filename', sa.Text(), nullable=False),
        sa.Column('source_type', sa.Text(), nullable=True),
        sa.Column('page_count', sa.Integer(), nullable=True),
        sa.Column('risk_level', sa.Text(), nullable=True),
        sa.Column('risk_score', sa.Integer(), nullable=True),
        sa.Column('risk_breakdown', JSONB(), nullable=True),
        sa.Column('findings', JSONB(), nullable=True),
        sa.Column('raw_text', sa.Text(), nullable=True),
        sa.Column('redacted_text', sa.Text(), nullable=True),
        sa.Column('summary_text', sa.Text(), nullable=True),
        sa.Column('memory_summary', sa.Text(), nullable=True),
        sa.Column('indexed', sa.Boolean(), server_default=sa.text("FALSE")),
        sa.Column('has_summary', sa.Boolean(), server_default=sa.text("FALSE")),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index('ix_documents_user_id', 'documents', ['user_id'])

    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('document_id', UUID(as_uuid=True), sa.ForeignKey('documents.id', ondelete='SET NULL'), nullable=True),
        sa.Column('action', sa.Text(), nullable=False),
        sa.Column('filename', sa.Text(), nullable=True),
        sa.Column('risk_level', sa.Text(), nullable=True),
        sa.Column('details', JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index('ix_audit_logs_user_id', 'audit_logs', ['user_id'])

    op.create_table(
        'chat_messages',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('document_id', UUID(as_uuid=True), sa.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role', sa.Text(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index('ix_chat_messages_user_id', 'chat_messages', ['user_id'])
    op.create_index('ix_chat_messages_doc_created', 'chat_messages', ['document_id', 'created_at'])


def downgrade() -> None:
    op.drop_table('chat_messages')
    op.drop_table('audit_logs')
    op.drop_table('documents')
    op.drop_table('refresh_tokens')
    op.drop_table('users')
