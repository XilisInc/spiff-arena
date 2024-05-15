"""empty message

Revision ID: 3191627ae224
Revises: 441dca328887
Create Date: 2023-12-18 17:08:53.142318

"""
# import os
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql
from spiffworkflow_backend.models.db import db, dialect_name

# revision identifiers, used by Alembic.
revision = '3191627ae224'
down_revision = '441dca328887'
branch_labels = None
depends_on = None

def is_mysql() -> bool:
   return dialect_name() == 'mysql' 

def is_postgres() -> bool:
   return dialect_name() == 'postgres' 


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    # we did in fact heavily adjust this one. be careful if auto-generating.
    with op.batch_alter_table('task', schema=None) as batch_op:
        if is_mysql():
            batch_op.drop_index('guid')
        batch_op.create_index(batch_op.f('ix_task_guid'), ['guid'], unique=False)

    with op.batch_alter_table('human_task', schema=None) as batch_op:
        batch_op.add_column(sa.Column('task_guid', sa.String(length=36), nullable=True))

        # sqlite does not seem to have this foreignkey constraint
        if is_postgres():
            batch_op.drop_constraint('human_task_task_model_id_fkey', type_='foreignkey')
        elif is_mysql():
            batch_op.drop_constraint('human_task_ibfk_5', type_='foreignkey')
        batch_op.drop_index('ix_human_task_task_model_id')
        batch_op.create_index(batch_op.f('ix_human_task_task_guid'), ['task_guid'], unique=False)
        batch_op.create_foreign_key('human_task_ibfk_task_guid', 'task', ['task_guid'], ['guid'])
        batch_op.drop_column('task_model_id')

    with op.batch_alter_table('task', schema=None) as batch_op:
        batch_op.drop_column('id')
        batch_op.create_primary_key('guid_pk', ['guid'])

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('task', schema=None) as batch_op:
        batch_op.add_column(sa.Column('id', mysql.INTEGER(), autoincrement=True, nullable=False))
        batch_op.drop_index(batch_op.f('ix_task_guid'))
        batch_op.create_index('guid', ['guid'], unique=False)

    with op.batch_alter_table('human_task', schema=None) as batch_op:
        batch_op.add_column(sa.Column('task_model_id', mysql.INTEGER(), autoincrement=False, nullable=True))
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.create_foreign_key('human_task_ibfk_5', 'task', ['task_model_id'], ['id'])
        batch_op.drop_index(batch_op.f('ix_human_task_task_guid'))
        batch_op.create_index('ix_human_task_task_model_id', ['task_model_id'], unique=False)
        batch_op.drop_column('task_guid')

    # ### end Alembic commands ###
