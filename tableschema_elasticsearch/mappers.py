# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

from copy import copy

# Module API


class MappingGenerator(object):

    def __init__(self, base={}):
        self._mapping = base

    @classmethod
    def _convert_date_format(cls, fmt):
        if fmt is not None and fmt.startswith('fmt:'):
            fmt = fmt[4:]
            fmt = fmt.replace('%d', 'dd')
            fmt = fmt.replace('%m', 'MM')
            fmt = fmt.replace('%y', 'yy')
            fmt = fmt.replace('%Y', 'yyyy')
            fmt = fmt.replace('%H', 'HH')
            fmt = fmt.replace('%M', 'mm')
            fmt = fmt.replace('%S', 'ss')
            fmt = fmt.replace('%f', 'SSS')
            assert '%' not in fmt
            return fmt
        else:
            return 'strict_date_optional_time'

    @classmethod
    def _convert_type(cls, schema_type, field, prefix):
        enabled = field.get('es:index', True)
        if enabled and schema_type == 'object':
            try:
                subschema = field['es:schema']
            except KeyError:
                raise ValueError('Must define es:schema for object fields'
                                 ' (or disable them using es:index=False)')

        else:
            subschema = {'fields': []}

        prop = {
            'integer': {'type': 'long',
                        'ignore_malformed': True,
                        'index': False},
            'number': {'type': 'scaled_float',
                       'scaling_factor': 100,
                       'ignore_malformed': True,
                       'index': False},
            'string': {'type': 'text'},
            'boolean': {'type': 'boolean'},
            'date': {'type': 'date',
                     'ignore_malformed': True,
                     'format': cls._convert_date_format(field.get('format'))},
            'datetime': {'type': 'date',
                         'ignore_malformed': True,
                         'format': cls._convert_date_format(field.get('format'))},
            'time': {'type': 'date',
                     'ignore_malformed': True,
                     'format': cls._convert_date_format(field.get('format'))},
            'object': {'properties':
                       cls._update_properties({}, subschema,
                                              prefix + field['name'] + '.')
                       if enabled else {},
                       'enabled': enabled,
                       'dynamic': False}
            }[schema_type]
        return prop

    @classmethod
    def _convert_field(cls, field, prefix):
        schema_type = field['type']
        if schema_type == 'array':
            field = copy(field)
            try:
                field['type'] = field['es:itemType']
            except KeyError:
                raise ValueError('Must define es:itemType for array fields')
            return cls._convert_field(field, prefix)

        prop = cls._convert_type(schema_type, field, prefix)
        return field['name'], prop

    @classmethod
    def _update_properties(cls, properties, schema, prefix=''):
        fields = schema['fields']
        properties.update(
            dict(
                cls._convert_field(f, prefix)
                for f in fields
            )
        )
        return properties

    def generate_from_schema(self, schema):
        properties = {}
        self._mapping['properties'] = properties
        self._update_properties(properties, schema)

    def get_mapping(self):
        return self._mapping


def descriptor_to_mapping(descriptor, mapping_generator_cls=None):
    """Convert descriptor to ElasticSearch Mapping.
    """
    if mapping_generator_cls is None:
        mapping_generator_cls = MappingGenerator
    mapping_gen = mapping_generator_cls()
    mapping_gen.generate_from_schema(descriptor)
    # print(mapping_gen.get_mapping())
    return mapping_gen.get_mapping()


def field_mapping_properties_to_descriptor(field_mapping_properties):
    """Convert ElasticSearch Mapping propertries to descriptor."""
    def get_schema_field_type(es_field_type):
        print(es_field_type)
        es_to_schema_field_mapping = {
            'long': {'type': 'integer'},
            'scaled_float': {'type': 'number'},
            'text': {'type': 'string'},
            'boolean': {'type': 'boolean'},
            'date': {'type': 'date'},
            'object': {'type': 'object'}
        }
        # return the schema type, or default to 'string'
        return es_to_schema_field_mapping.get(
            es_field_type, es_to_schema_field_mapping['text'])

    fields = []
    for prop_name, prop_value in field_mapping_properties.items():
        field = get_schema_field_type(prop_value.get('type'))
        field['name'] = prop_name
        print(field)
        fields.append(field)
    return {'fields': fields}
