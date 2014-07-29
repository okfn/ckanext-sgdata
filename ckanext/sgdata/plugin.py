import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit


class SGDatasetForm(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)

    # IConfigurer

    def update_config(self, config):
        toolkit.add_template_directory(config, 'templates')
