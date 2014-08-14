'''Paster commands provided by this extension.'''

import csv

import ckanapi

import ckan.plugins.toolkit as toolkit
import ckan.lib.cli


class SGDataImportCommand(ckan.lib.cli.CkanCommand):

    '''A paster command to import 3500_unclassified_metadata.csv into CKAN.'''

    summary = 'Import datasets from 3500_unclassified_metadata.csv into CKAN.'
    min_args = 3
    max_args = 3

    def command(self):
        '''Run the import datasets command.'''
        url = self.args[0]
        apikey = self.args[1]
        owner_org = self.args[2]
        import_datasets(ckanapi.RemoteCKAN(url, apikey=apikey), owner_org)


def import_datasets(ckan, owner_org):
    '''Import datasets from 3500_unclassified_metadata.csv into CKAN.'''
    header_translations = {
        'SG-DATA RECORD IDENTIFIER': 'sg_data_record_identifier',
        'REFERENCE PERIOD FROM': 'reference_period_start',
        'REFERENCE PERIOD TO': 'reference_period_end',
        'AGENCY RECORD IDENTIFIER': 'agency_record_identifier',
        '1ST LEVEL CATEGORY NUMBER (2-DIGITS)*': 'first_level_category',
        '2ND LEVEL CATEGORY NUMBER (2-DIGITS)*': 'second_level_category',
        '3RD LEVEL CATEGORY NUMBER (2-DIGITS)*': 'third_level_category',
        "SURVEY/ADMINISTRATIVE SOURCE (COMPULSORY IF TYPE OF DATA COLLECTION IS NOT 'OT')": 'zzz_administrative_source',
        'DATA PROVIDER/DISTRIBUTOR*': 'data_provider',
        'ALTERNATE PROVIDER NAME*': 'data_provider_alternate_contact_name',
        'ALTERNATE PROVIDER DESIGNATION*': 'data_provider_alternate_contact_designation',
        'ALTERNATE PROVIDER DEPARTMENT*': 'data_provider_alternate_contact_department',
        'ALTERNATE PROVIDER TELEPHONE NUMBER*': 'data_provider_alternate_contact_telephone_number',
        'ALTERNATE PROVIDER EMAIL ADDRESS*': 'data_provider_alternate_contact_email_address',
        'DATA COMPILER/SOURCE': 'data_compiler',
        'COMPILER NAME': 'data_compiler_contact_name',
        'COMPILER DESIGNATION': 'data_compiler_contact_designation',
        'COMPILER DEPARTMENT': 'data_compiler_contact_department',
        'COMPILER TELEPHONE NUMBER': 'data_compiler_contact_telephone_number',
        'COMPILER EMAIL ADDRESS': 'data_compiler_contact_email_address',
        'PUBLISH DATAGOVSG': 'publish_on_data_gov_sg',
        }

    headers = None
    datasets_created = 0
    datasets_failed = 0
    datasets_skipped = 0
    datasets_skipped_because_no_administrative_source = 0
    for row in csv.reader(open('3500_unclassified_metadata.csv', 'r')):
        if not headers:
            headers = []
            for header in row:
                header = header.strip()
                if header in header_translations:
                    header = header_translations[header]
                else:
                    if header.endswith('*'):
                        header = header[:-1]
                    header = header.replace(' ', '_')
                    header = header.lower()
                headers.append(header)
        else:
            data = {}
            for header, value in zip(headers, row):
                data[header] = value.strip()

            data['category'] = '{0}.{1:02}'.format(
                int(data['first_level_category']), int(data['second_level_category']))
            del data['first_level_category']
            del data['second_level_category']
            del data['third_level_category']

            for key in data.keys():
                if not data[key]:
                    del data[key]

            if 'zzz_administrative_source' not in data:
                print 'Skipping because no administrative source'
                datasets_skipped_because_no_administrative_source += 1
                continue

            if 'type_of_data_collection' in data:
                data['type_of_data_collection'] = {
                    'AD': 'Administrative Data Collection',
                    'SD': 'Survey Data Collection',
                    'MX': 'Mix of Survey and Administrative Data Collection',
                    'O': 'Others',
                    }[data['type_of_data_collection']]

            if 'frequency' in data:
                data['frequency'] = {
                    'A': 'Annually',
                    'O': 'Others',
                    'D': 'Daily',
                    'W': 'Weekly',
                    'M': 'Monthly',
                    'Q': 'Quarterly',
                    'H': 'Half Yearly',
                    'C': 'Ad-Hoc',
                    }[data['frequency']]

            if 'security_classification' in data:
                data['security_classification'] = {
                    'U': 'Unclassified',
                    'R': 'Restricted',
                    'C': 'Confidential',
                    'S': 'Secret',
                    }[data['security_classification']]

            if 'data_granularity' in data:
                data['data_granularity'] = {
                    'AD': 'Aggregated Data',
                    'IR': 'Individual Record',
                }[data['data_granularity']]

            if 'publish_on_data_gov_sg' in data:
                data['publish_on_data_gov_sg'] = {
                    '0': 'No',
                    '1': 'Yes - publish both metadata and data',
                    '2': 'Yes - publish metadata only',
                }[data['publish_on_data_gov_sg']]

            if 'status' in data:
                data['status'] = {
                    'A': 'Active',
                    'D': 'Discontinued',
                    'R': 'Replaced',
                    'TBC': 'To be Collected',
                    }[data['status']]

            def keyword_translate(keyword):
                '''Transform string into a valid CKAN tag name.'''
                translated_keyword = ''
                for char in keyword:
                    if char.isalnum() or char in '-._ ':
                        translated_keyword = translated_keyword + char
                return translated_keyword
            keywords = [keyword_translate(keyword.strip())
                        for keyword in data.get('keywords').split(',')
                        if keyword.strip()]
            data['tags'] = [{'name': keyword} for keyword in keywords]
            del data['keywords']

            data['name'] = data['sg_data_record_identifier'].lower().strip()

            data['owner_org'] = owner_org

            try:
                response = ckan.action.package_create(**data)
                datasets_created += 1
            except toolkit.ValidationError as err:
                if err.error_dict == {'URL': ['That URL is already in use.'],
                                    '__type': 'Validation Error'}:
                    datasets_skipped += 1
                else:
                    datasets_failed += 1
                    import ipdb; ipdb.set_trace()
            except ckanapi.errors.CKANAPIError as err:
                datasets_failed += 1
                import ipdb; ipdb.set_trace()

    print 'Created {0} datasets'.format(datasets_created)
    print 'Skipped {0} datasets'.format(datasets_skipped)
    print 'Skipped {0} datasets because no administrative source'.format(datasets_skipped_because_no_administrative_source)
    print '{0} failures'.format(datasets_failed)
