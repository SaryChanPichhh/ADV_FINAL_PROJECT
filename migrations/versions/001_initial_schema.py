"""Initial schema: admins, products, orders, order_items

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-11-13 13:30:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Admins table
    op.create_table(
        'admins',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=80), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_admins_username'), 'admins', ['username'], unique=True)

    # Products table
    op.create_table(
        'products',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('price', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('stock_quantity', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('image_url', sa.Text(), nullable=True),
        sa.Column('image_key', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # Orders table
    op.create_table(
        'orders',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('order_code', sa.String(length=30), nullable=False),
        sa.Column('customer_name', sa.String(length=120), nullable=False),
        sa.Column('customer_email', sa.String(length=120), nullable=False),
        sa.Column('customer_phone', sa.String(length=30), nullable=False),
        sa.Column('shipping_address', sa.Text(), nullable=False),
        sa.Column('total_amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=5), nullable=False, server_default='USD'),
        sa.Column('payment_status', sa.String(length=20), nullable=False, server_default='UNPAID'),
        sa.Column('khqr_md5', sa.String(length=32), nullable=True),
        sa.Column('payer_bank', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_orders_order_code'), 'orders', ['order_code'], unique=True)
    op.create_index(op.f('ix_orders_khqr_md5'), 'orders', ['khqr_md5'], unique=True)

    # Order Items table
    op.create_table(
        'order_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('unit_price', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('subtotal', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id']),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('order_items')
    op.drop_index(op.f('ix_orders_khqr_md5'), table_name='orders')
    op.drop_index(op.f('ix_orders_order_code'), table_name='orders')
    op.drop_table('orders')
    op.drop_table('products')
    op.drop_index(op.f('ix_admins_username'), table_name='admins')
    op.drop_table('admins')
