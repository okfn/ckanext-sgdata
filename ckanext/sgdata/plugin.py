import datetime

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import ckan.lib.helpers as helpers


def _change_error_dict(err):
    errors = err.error_dict.copy()

    # Change "Tag string" to "Keywords" in the error summary shown to the user.
    if 'tag_string' in errors:
        errors['keywords'] = errors['tag_string']
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
        schema['administrative_source'] = [
            toolkit.get_validator('not_missing'),
            toolkit.get_validator('not_empty'),
            toolkit.get_converter('convert_to_extras')]
        schema['reference-period-start'] = [
            toolkit.get_converter('convert_to_extras')]
        schema['reference-period-end'] = [
            toolkit.get_converter('convert_to_extras')]
        schema['available-from'] = [
            toolkit.get_converter('convert_to_extras')]

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
        schema['administrative_source'] = [
            toolkit.get_converter('convert_from_extras')]
        schema['reference-period-start'] = [
            toolkit.get_converter('convert_from_extras')]
        schema['reference-period-end'] = [
            toolkit.get_converter('convert_from_extras')]
        schema['available-from'] = [
            toolkit.get_converter('convert_from_extras')]
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

        return map_

    # IActions

    def get_actions(self):
        return {'package_create': package_create,
                'package_update': package_update,
                }

    # ITemplateHelpers

    def get_helpers(self):
        return {'today': today}


class SGDataPackageController(toolkit.BaseController):

    def new_metadata(self, id, data=None, errors=None, error_summary=None):
        import ckan.model as model
        import ckan.lib.base as base

        # Change the package state from draft to active and save it.
        context = {'model': model, 'session': model.Session,
                   'user': toolkit.c.user or toolkit.c.author,
                   'auth_user_obj': toolkit.c.userobj}
        data_dict = toolkit.get_action('package_show')(context, {'id': id})
        data_dict['id'] = id
        data_dict['state'] = 'active'
        toolkit.get_action('package_update')(context, data_dict)

        base.redirect(helpers.url_for(controller='package', action='read',
                                      id=id))
