"""empty message

Revision ID: 4452253fa763
Revises: 45395b974e2d
Create Date: 2016-07-05 14:08:11.091558

"""

# revision identifiers, used by Alembic.
revision = '4452253fa763'
down_revision = '45395b974e2d'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(u'users_phone_number_key', 'users', type_='unique')
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_unique_constraint(u'users_phone_number_key', 'users', ['phone_number'])
    ### end Alembic commands ###