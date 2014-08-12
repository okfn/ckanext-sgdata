import datetime
import logging
import os.path
import json

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import ckan.lib.helpers as helpers
import ckan.model

import ckanext.sgdata.model as model


SIMPLE_MANDATORY_TEXT_FIELDS = (
    'administrative_source',
    'coverage',
    'conditions_of_use',
    'unit_of_measure',
    'data_provider',
    'data_provider_contact_name',
    'data_provider_contact_designation',
    'data_provider_contact_department',
    'data_provider_contact_telephone_number',
    'data_provider_contact_email_address',
    'data_provider_alternate_contact_name',
    'data_provider_alternate_contact_designation',
    'data_provider_alternate_contact_department',
    'data_provider_alternate_contact_telephone_number',
    'data_provider_alternate_contact_email_address',
    'category',
    )


SIMPLE_OPTIONAL_TEXT_FIELDS = (
    'comments',
    'agency_record_identifier',
    'data_compiler',
    'data_compiler_contact_name',
    'data_compiler_contact_designation',
    'data_compiler_contact_department',
    'data_compiler_contact_telephone_number',
    'data_compiler_contact_email_address',
    )


def _change_error_dict(err):
    errors = err.error_dict.copy()

    # Change "Tags" to "Keywords" in the error summary shown to the user.
    if 'tags' in errors:
        errors['keywords'] = errors['tags']
        del errors['tags']

    # The 'tags' errors seem to also be repeated as 'tag_string', which is also
    # shown to the user! Stop it.
    if 'tag_string' in errors:
        del errors['tag_string']

    # Change "Name" to "URL" in the error summary shown to the user.
    if 'name' in errors:
        errors['URL'] = errors['name']
        del errors['name']

    return errors


def _custom_validation(data_dict):

    errors = {}

    if not data_dict.get('tags'):
        errors['keywords'] = ['Missing value']

    if (data_dict.get('reference-period-start')
            and data_dict.get('reference-period-end')):

        # TODO: Handle invalid date strings.
        start = datetime.datetime.strptime(data_dict['reference-period-start'],
                                           '%m/%d/%Y')
        end = datetime.datetime.strptime(data_dict['reference-period-end'],
                                         '%m/%d/%Y')

        if start > end:
            errors['reference-period-start'] = [
                'Start date must be before end date']
            errors['reference-period-end'] = [
                'End date must be after start date']

    return errors


def package_create(context, data_dict):
    import ckan.logic.action.create

    error_dict = _custom_validation(data_dict)

    try:
        result = ckan.logic.action.create.package_create(context, data_dict)
    except toolkit.ValidationError as err:
        error_dict.update(_change_error_dict(err))

    if error_dict:
        raise toolkit.ValidationError(error_dict)

    model.save_sg_data_record_identifier(result)

    return result


def package_update(context, data_dict):
    import ckan.logic.action.update

    error_dict = _custom_validation(data_dict)

    try:
        result = ckan.logic.action.update.package_update(context, data_dict)
    except toolkit.ValidationError as err:
        error_dict.update(_change_error_dict(err))

    if error_dict:
        raise toolkit.ValidationError(error_dict)

    return result


def today():
    return datetime.datetime.now().strftime('%m/%d/%Y')


def _create_vocabulary(name, tags):
    user = toolkit.get_action('get_site_user')({'ignore_auth': True}, {})
    context = {'user': user['name']}
    try:
        data = {'id': name}
        toolkit.get_action('vocabulary_show')(context, data)
        logging.info("{name} vocabulary already exists, skipping.".format(
            name=name))
    except toolkit.ObjectNotFound:
        logging.info("Creating vocabulary '{name}'".format(name=name))
        data = {'name': name}
        vocab = toolkit.get_action('vocabulary_create')(context, data)

        for tag in tags:
            logging.info(
                "Adding tag {tag} to vocab {vocab}".format(tag=tag,
                                                           vocab=name))
            data = {'name': tag, 'vocabulary_id': vocab['id']}
            toolkit.get_action('tag_create')(context, data)


def _get_tags_from_vocabulary(name, initial_tags):
    _create_vocabulary(name, initial_tags)
    try:
        tags = toolkit.get_action('tag_list')(
            data_dict={'vocabulary_id': name})
        return tags
    except toolkit.ObjectNotFound:
        return []


def types_of_data_collection():
    return _get_tags_from_vocabulary('type_of_data_collection',
                                     ('Survey Data Collection',
                                     'Administrative Data Collection',
                                     'Mix of Survey and Administrative Data Collection',
                                     'Others'))


def statuses():
    return _get_tags_from_vocabulary('status',
                                     ('Active', 'Discontinued', 'Replaced',
                                     'To be Collected'))


def frequencies():
    return _get_tags_from_vocabulary(
        'frequency', ('Daily', 'Weekly', 'Monthly', 'Quarterly',
        'Half Yearly', 'Annually', 'Ad-Hoc', 'Others'))


def security_classifications():
    return _get_tags_from_vocabulary(
        'security_classification', ('Unclassified', 'Restricted',
        'Confidential', 'Secret'))


def data_granularities():
    return _get_tags_from_vocabulary(
        'data_granularity', ('Aggregated Data', 'Individual Record'))


def publish_on_data_gov_sg():
    return _get_tags_from_vocabulary(
        'publish_on_data_gov_sg', ('No', 'Yes - publish both metadata and data',
        'Yes - publish metadata only'))


def categories():

    path = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                        '../../categories.json')
    categories = json.loads(open(path, 'r').read())
    # FIXME: Sort the values.
    return categories.values()


def category(value):
    category = None
    for c in categories():
        for sc in c['categories'].values():
            if sc['value'] == value:
                category = sc
                break
        if category:
            break
    return '{0} -> {1}'.format(category['parent_label'], category['label'])


def last_update_by(pkg_dict):
    activities = toolkit.get_action('package_activity_list')(
            context={}, data_dict={'id': pkg_dict['id']})
    if not activities:
        return None
    user_id = activities[0]['user_id']
    user_dict = toolkit.get_action('user_show')(
            context={}, data_dict={'id': user_id})
    return user_dict


def sg_data_record_identifier(pkg_dict):
    return model.sg_data_record_identifier(pkg_dict['id'])


class SGDatasetForm(plugins.SingletonPlugin, toolkit.DefaultDatasetForm):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IDatasetForm)
    plugins.implements(plugins.IRoutes, inherit=True)
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.ITemplateHelpers)

    # IConfigurer

    def update_config(self, config):
        toolkit.add_template_directory(config, 'templates')
        toolkit.add_public_directory(config, 'public')
        toolkit.add_resource('resources', 'theme')
        #model.setup()

    # IDatasetForm

    def is_fallback(self):
        return False

    def package_types(self):
        return ('dataset',)

    def _customize_package_schema(self, schema):
        schema['title'] = [
            toolkit.get_validator('not_missing'),
            toolkit.get_validator('not_empty'),
            unicode]

        for field in SIMPLE_MANDATORY_TEXT_FIELDS:
            schema[field] = [
                toolkit.get_validator('not_missing'),
                toolkit.get_validator('not_empty'),
                toolkit.get_converter('convert_to_extras')]

        for field in SIMPLE_OPTIONAL_TEXT_FIELDS:
            schema[field] = [
                toolkit.get_validator('ignore_missing'),
                toolkit.get_converter('convert_to_extras')
                ]

        schema['reference-period-start'] = [
            toolkit.get_converter('convert_to_extras')]

        schema['reference-period-end'] = [
            toolkit.get_converter('convert_to_extras')]

        schema['available-from'] = [
            toolkit.get_converter('convert_to_extras')]

        schema['type_of_data_collection'] = [
            toolkit.get_validator('not_missing'),
            toolkit.get_validator('not_empty'),
            toolkit.get_converter('convert_to_tags')('type_of_data_collection')]

        schema['status'] = [
            toolkit.get_validator('not_missing'),
            toolkit.get_validator('not_empty'),
            toolkit.get_converter('convert_to_tags')('status')]

        schema['frequency'] = [
            toolkit.get_validator('not_missing'),
            toolkit.get_validator('not_empty'),
            toolkit.get_converter('convert_to_tags')('frequency')]

        schema['security_classification'] = [
            toolkit.get_validator('not_missing'),
            toolkit.get_validator('not_empty'),
            toolkit.get_converter('convert_to_tags')('security_classification')]

        schema['data_granularity'] = [
            toolkit.get_validator('not_missing'),
            toolkit.get_validator('not_empty'),
            toolkit.get_converter('convert_to_tags')('data_granularity')]

        schema['publish_on_data_gov_sg'] = [
            toolkit.get_validator('not_missing'),
            toolkit.get_validator('not_empty'),
            toolkit.get_converter('convert_to_tags')('publish_on_data_gov_sg')]

    def create_package_schema(self):
        schema = super(SGDatasetForm, self).create_package_schema()
        self._customize_package_schema(schema)
        return schema

    def update_package_schema(self):
        schema = super(SGDatasetForm, self).update_package_schema()
        self._customize_package_schema(schema)
        return schema

    def show_package_schema(self):
        schema = super(SGDatasetForm, self).show_package_schema()

        schema['tags']['__extras'].append(toolkit.get_converter(
            'free_tags_only'))

        for field in (SIMPLE_MANDATORY_TEXT_FIELDS +
                      SIMPLE_OPTIONAL_TEXT_FIELDS):
            schema[field] = [
                toolkit.get_converter('convert_from_extras'),
                toolkit.get_validator('ignore_missing')]

        schema['reference-period-start'] = [
            toolkit.get_converter('convert_from_extras')]

        schema['reference-period-end'] = [
            toolkit.get_converter('convert_from_extras')]

        schema['available-from'] = [
            toolkit.get_converter('convert_from_extras')]

        schema['type_of_data_collection'] = [
            toolkit.get_converter('convert_from_tags')('type_of_data_collection'),
            toolkit.get_validator('ignore_missing')]

        schema['status'] = [
            toolkit.get_converter('convert_from_tags')('status'),
            toolkit.get_validator('ignore_missing')]

        schema['frequency'] = [
            toolkit.get_converter('convert_from_tags')('frequency'),
            toolkit.get_validator('ignore_missing')]

        schema['security_classification'] = [
            toolkit.get_converter('convert_from_tags')('security_classification'),
            toolkit.get_validator('ignore_missing')]

        schema['data_granularity'] = [
            toolkit.get_converter('convert_from_tags')('data_granularity'),
            toolkit.get_validator('ignore_missing')]

        schema['publish_on_data_gov_sg'] = [
            toolkit.get_converter('convert_from_tags')('publish_on_data_gov_sg'),
            toolkit.get_validator('ignore_missing')]

        return schema

    # IRoutes

    def before_map(self, map_):

        # Override the package controller's new_metadata() method so we can
        # skip the "additional info" stage of the three-stage dataset creation
        # process and go straight to creating the dataset.
        map_.connect(
            '/dataset/new_metadata/{id}',
            controller='ckanext.sgdata.plugin:SGDataPackageController',
            action='new_metadata')

        map_.connect(
            '/dataset/contact/{dataset_id}',
            controller='ckanext.sgdata.plugin:SGDataPackageController',
            action='contact')

        return map_

    # IActions

    def get_actions(self):
        return {'package_create': package_create,
                'package_update': package_update,
                }

    # ITemplateHelpers

    def get_helpers(self):
        return {'today': today,
                'types_of_data_collection': types_of_data_collection,
                'statuses': statuses,
                'frequencies': frequencies,
                'security_classifications': security_classifications,
                'data_granularities': data_granularities,
                'publish_on_data_gov_sg': publish_on_data_gov_sg,
                'last_update_by': last_update_by,
                'categories': categories,
                'category': category,
                'sg_data_record_identifier': sg_data_record_identifier,
                }


class SGDataPackageController(toolkit.BaseController):

    def new_metadata(self, id, data=None, errors=None, error_summary=None):
        import ckan.lib.base as base

        # Change the package state from draft to active and save it.
        context = {'model': ckan.model, 'session': ckan.model.Session,
                   'user': toolkit.c.user or toolkit.c.author,
                   'auth_user_obj': toolkit.c.userobj}
        data_dict = toolkit.get_action('package_show')(context, {'id': id})
        data_dict['id'] = id
        data_dict['state'] = 'active'
        toolkit.get_action('package_update')(context, data_dict)

        base.redirect(helpers.url_for(controller='package', action='read',
                                      id=id))

    def contact(self, dataset_id):

        context = {'model': ckan.model, 'session': ckan.model.Session,
                   'user': toolkit.c.user or toolkit.c.author,
                   'for_view': True, 'auth_user_obj': toolkit.c.userobj}
        data_dict = {'id': dataset_id}

        try:
            toolkit.c.pkg_dict = toolkit.get_action('package_show')(context,
                                                                    data_dict)
        except toolkit.ObjectNotFound:
            toolkit.abort(404, _('Dataset not found'))
        except toolkit.NotAuthorized:
            toolkit.abort(401,
                          ('Unauthorized to read dataset %s') % dataset_id)

        return toolkit.render('package/contact.html')
