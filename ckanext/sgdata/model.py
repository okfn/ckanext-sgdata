import sqlalchemy
import sqlalchemy.types as types
import sqlalchemy.orm.exc

import ckan.model
import ckan.model.meta


sg_data_record_identifier_table = sqlalchemy.Table(
    'sg_data_record_identifier', ckan.model.meta.metadata,
    sqlalchemy.Column('first_level_category', types.Integer, primary_key=True),
    sqlalchemy.Column('second_level_category', types.Integer, primary_key=True),
    sqlalchemy.Column('id', types.Integer, primary_key=True),
    sqlalchemy.Column('package_id', types.UnicodeText, unique=True,
                      nullable=False))


class SGDataRecordIdentifier(object):
    def __init__(self, first_level_category, second_level_category, id,
                 package_id):
        self.first_level_category = first_level_category
        self.second_level_category = second_level_category
        self.id = id,
        self.package_id = package_id


ckan.model.meta.mapper(SGDataRecordIdentifier, sg_data_record_identifier_table)


def setup():
    if not sg_data_record_identifier_table.exists():
        sg_data_record_identifier_table.create()


def sg_data_record_identifier(package_id):
    '''Return the SGDataRecordIdentifier for the given package.'''

    q = ckan.model.Session.query(SGDataRecordIdentifier)
    q = q.filter_by(package_id=package_id)
    obj = q.one()
    return '{cat_1:02}{cat_2:02}{id:015}A'.format(
        cat_1=obj.first_level_category, cat_2=obj.second_level_category,
        id=obj.id)


# FIXME: This method may fail on concurrent transactions that generate the
# same id value.
def save_sg_data_record_identifier(package_dict):

    category_string = package_dict.get('category')

    if not category_string:
        return

    first_level_category, second_level_category = category_string.split('.')

    first_level_category = int(first_level_category)
    second_level_category = int(second_level_category)

    # Figure out what the next id value should be.
    q = ckan.model.Session.query(
        sqlalchemy.func.max(SGDataRecordIdentifier.id))
    q = q.filter_by(first_level_category=first_level_category)
    q = q.filter_by(second_level_category=second_level_category)
    highest_id_so_far = q.scalar()
    if highest_id_so_far is None:
        id_ = 1
    else:
        id_ = highest_id_so_far + 1

    # Make a new row in the sg_data_record_identifier table.
    obj = SGDataRecordIdentifier(first_level_category, second_level_category,
                                 id_, package_dict['id'])
    ckan.model.Session.add(obj)
    ckan.model.Session.commit()
