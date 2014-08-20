#!/bin/bash

# Based on:
# https://github.com/open-data/ckanext-canada/blob/master/bin/build-combined-ckan-mo.sh

HERE=`dirname $0`

msgcat --use-first \
    "$HERE/../ckanext/sgdata/i18n/en_GB/LC_MESSAGES/ckan.po" \
    "$HERE/../../ckan/ckan/i18n/en_GB/LC_MESSAGES/ckan.po" \
    | msgfmt - -o "$HERE/../../ckan/ckan/i18n/en_GB/LC_MESSAGES/ckan.mo"
