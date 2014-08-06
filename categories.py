#!/usr/bin/env python2
'''Produce a categories.json filed from a categories.csv file.'''

import csv
import json

categories = {}
f = open('categories.csv', 'rt')
try:
    reader = csv.reader(f)
    for row in reader:
        (top_level_value, top_level_label, second_level_value,
            second_level_label) = row

        if top_level_value not in categories:
            categories[top_level_value] = {'value': top_level_value,
                                           'label': top_level_label,
                                           'categories': {}}

        if second_level_value not in categories[top_level_value]['categories']:
            categories[top_level_value]['categories'][second_level_value] = {
                'value':  second_level_value,
                'label': second_level_label,
                'parent_label': top_level_label}
finally:
    f.close()

open('categories.json', 'w').write(json.dumps(categories))
