'''Paster commands provided by this extension.'''

import csv
import datetime

import ckanapi
import requests

import ckan.plugins.toolkit as toolkit
import ckan.lib.cli


class SGDataImportCommand(ckan.lib.cli.CkanCommand):

    '''Import datasets from 3500_unclassified_metadata.csv into CKAN.

    Usage:

     paster sgdataimport <command> <url> <apikey> <organisation> [start_from]

    The possible commands are:

     import - Post each dataset from the CSV file to CKAN's package_create
              API. Dataset's that already exist in CKAN will be skipped.

     verify - For each dataset in the CSV file, verify that it exists in the
              CKAN site. Fetches the dataset from the CKAN API and checks that
              its fields match the values from the CSV file. Also fetches the
              dataset's HTML page just to check that it doesn't crash.

     import-and-verify - Import and verify each dataset.

     verify-api - Like verify, but does the API verification only.

     verify-html - Like verify, but does the HTML page verification only.

    <apikey> is the API key of the user who will be used to post the datasets.

    <organisation> is the name of the organisation that the datasets will be
    added to.

    [start_from] (optional, default: 0) is the row in the CSV file to start
    from (where 0 is the first row). This can be useful to continue a job where
    it left off.

    Example:

     paster sgdataimport import 'http://127.0.0.1:5000' aa1577ac-f19c-4a83-beb1-fe091caeace4 test-agency 840

    '''

    summary = __doc__.split('\n')[0]
    usage = __doc__
    min_args = 4
    max_args = 5

    def command(self):
        '''Run the import datasets command.'''
        command = self.args[0]
        url = self.args[1]
        apikey = self.args[2]
        owner_org = self.args[3]
        if len(self.args) == 5:
            start_from = int(self.args[4])
        else:
            start_from = 0

        site = ckanapi.RemoteCKAN(url, apikey=apikey)
        datasets = read_datasets_from_csv_file(
            '3500_unclassified_metadata.csv', owner_org)

        datasets = datasets[start_from:]

        def post(site, dataset):
            try:
                post_dataset(site, dataset)
                print("Created dataset {0}: {1}".format(start_from+i,
                                                        dataset['title']))
            except DatasetAlreadyExistsError:
                print("Dataset already exists {0}: {1}".format(
                    start_from+i, dataset['title']))

        if command == 'import':
            for (i, dataset) in enumerate(datasets):
                post(site, dataset)
        elif command == 'verify':
            for (i, dataset) in enumerate(datasets):
                verify_dataset_via_api(site, dataset)
                verify_dataset_via_web_ui(dataset)
                print("Verified dataset {0}: {1}".format(start_from+i,
                                                         dataset['title']))
        elif command == 'import-and-verify':
            for (i, dataset) in enumerate(datasets):
                post(site, dataset)
                verify_dataset_via_api(site, dataset)
                verify_dataset_via_web_ui(dataset)
                print("Verified dataset {0}: {1}".format(start_from+i,
                                                         dataset['title']))
        elif command == 'verify-api':
            for (i, dataset) in enumerate(datasets):
                verify_dataset_via_api(site, dataset)
                print("Verified dataset {0}: {1}".format(start_from+i,
                                                         dataset['title']))
        elif command == 'verify-html':
            for (i, dataset) in enumerate(datasets):
                verify_dataset_via_web_ui(dataset)
                print("Verified dataset {0}: {1}".format(start_from+i,
                                                         dataset['title']))

        else:
            print('Unknown command: {0}'.format(command))


def read_headers_from_csv_fow(row):
    header_translations = {
        'SG-DATA RECORD IDENTIFIER': 'sg_data_record_identifier',
        'REFERENCE PERIOD FROM': 'reference-period-start',
        'REFERENCE PERIOD TO': 'reference-period-end',
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
        'METADATA AVAILABILITY DATE': 'available-from',
        'DATA PROVIDER EMAIL*': 'data_provider_contact_email_address',
        }
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
    return headers


def read_datasets_from_csv_file(path, owner_org):

    print("Reading CSV file...")
    datasets = []
    headers = None
    datasets_skipped_because_no_administrative_source = 0
    datasets_skipped_because_invalid_category = 0
    for row in csv.reader(open(path, 'r')):
        if not headers:
            headers = read_headers_from_csv_fow(row)
        else:
            data = {}
            for header, value in zip(headers, row):
                data[header] = value.strip()

            data['category'] = '{0}.{1:02}'.format(
                int(data['first_level_category']),
                int(data['second_level_category']))
            del data['first_level_category']
            del data['second_level_category']
            del data['third_level_category']

            if data['category'] in ('10.10', '13.23', '16.16'):
                datasets_skipped_because_invalid_category += 1
                continue

            for key in data.keys():
                if not data[key]:
                    del data[key]

            if 'zzz_administrative_source' not in data:
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

            data['title'] = data['title'].replace('\xc2\xa0', '').replace(
                '\xc2\xbf', '')

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
            data['tags'] = [{'name': keyword} for keyword in set(keywords)]
            del data['keywords']

            data['name'] = data['sg_data_record_identifier'].lower().strip()
            del data['sg_data_record_identifier']

            data['owner_org'] = owner_org

            # We're not using resources/data file URLs on this site.
            if 'data_provider_url' in data:
                del data['data_provider_url']

            for key in ('reference-period-start', 'reference-period-end',
                        'available-from'):
                if key in data:
                    data[key] = datetime.datetime.strptime(data[key], '%Y%m%d').strftime('%m/%d/%Y')

            datasets.append(data)

    print('Skipped {0} datasets because no administrative source'.format(
        datasets_skipped_because_no_administrative_source))
    print('Skipped {0} datasets because invalid category'.format(
        datasets_skipped_because_invalid_category))
    return datasets


class DatasetAlreadyExistsError(Exception):
    pass


def post_dataset(site, dataset):
    try:
        site.action.package_create(**dataset)
    except toolkit.ValidationError as err:
        if err.error_dict == {'URL': ['That URL is already in use.'],
                              '__type': 'Validation Error'}:
            raise DatasetAlreadyExistsError
        else:
            print("Dataset creation failed: {0}".format(dataset['title']))
            import ipdb; ipdb.set_trace()
    except ckanapi.errors.CKANAPIError as err:
        print("Dataset creation failed: {0}".format(dataset['title']))
        import ipdb; ipdb.set_trace()


def verify_dataset_via_api(site, dataset):

    dataset_from_api = site.action.package_show(id=dataset['name'])
    for key in dataset.keys():

        if key == 'tags':
            tags_from_api = [{'name': tag['name']}
                             for tag in dataset_from_api['tags']]
            tags_from_api.sort()
            dataset['tags'].sort()
            if tags_from_api != dataset['tags']:
                import ipdb; ipdb.set_trace()

        elif key == 'owner_org':
            pass

        elif key == 'title':
            if dataset['title'] != dataset_from_api['title']:
                import ipdb; ipdb.set_trace()

        elif key == 'sg_data_record_identifier':
            pass

        else:
            try:
                if dataset_from_api[key] != dataset[key]:
                    import ipdb; ipdb.set_trace()
            except KeyError as err:
                import ipdb; ipdb.set_trace()


def verify_dataset_via_web_ui(dataset):
    response = requests.get('http://127.0.0.1:5000/dataset/{0}'.format(
        dataset['name']))
    assert response.status_code == 200
