import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit


class SGDatasetForm(plugins.SingletonPlugin, toolkit.DefaultDatasetForm):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IDatasetForm)

    # IConfigurer

    def update_config(self, config):
        toolkit.add_template_directory(config, 'templates')

    # IDatasetForm

    def is_fallback(self):
        return False

    def package_types(self):
        return ('dataset',)

    def _customize_package_schema(self, schema):
        schema['administrative_source'] = [
            toolkit.get_validator('not_empty'),
            toolkit.get_validator('not_missing'),
            toolkit.get_converter('convert_to_extras')]
        return schema

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
        return schema
