ckanext-sgdata
==============

A CKAN extension for the Singapore Ministry of Finance's metadata catalog.


## Custom translations

To get custom translated strings (eg *Agencies* instead of *Organizations*),
follow these steps:

* Set the following on your ini file:

    `ckan.locale_default = en_GB`

* Edit the `en_GB` language file in this extension:

    `ckanext/sgdata/i18n/en_GB/LC_MESSAGES/ckan.po`

* Run the following **on the server CKAN is running** (you'll need __gettext__ 
  `apt-get install gettext`):

    `./bin/build-combined-ckan-mo.sh`

* Restart the web server.

## Setup front end

* Dependancies `node` <http://nodejs.org/> & `bower` <http://bower.io/>
* Then: `bower update`
* Restart web server
