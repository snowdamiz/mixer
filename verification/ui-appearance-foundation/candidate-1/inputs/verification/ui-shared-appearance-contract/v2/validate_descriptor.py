#!/usr/bin/env python3
"""Executable design oracle for the closed descriptor, not a native install proof."""
from __future__ import annotations
import json
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent
MAX_BYTES, MAX_DEPTH, MAX_VALUES = 65536, 16, 4096

class DescriptorError(ValueError):
    pass

def require(condition, code):
    if not condition:
        raise DescriptorError(code)

def canonical(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(',', ':')) + '\n').encode('ascii')

def pairs(items):
    result = {}
    for key, value in items:
        require(key not in result, 'duplicate-key')
        result[key] = value
    return result

def uint(raw):
    require(0 < len(raw) <= 20 and all('0' <= c <= '9' for c in raw), 'unsigned-integer-token')
    require(raw == '0' or not raw.startswith('0'), 'unsigned-integer-token')
    result = int(raw)
    require(result <= (1 << 64) - 1, 'unsigned-integer-range')
    return result

def reject_number(_):
    raise DescriptorError('integer-token-required')

def raw_guard(text):
    depth, quoted, escaped = 0, False, False
    for c in text:
        if quoted:
            if escaped: escaped = False
            elif c == '\\': escaped = True
            elif c == '"': quoted = False
        elif c == '"': quoted = True
        elif c in '[{':
            depth += 1
            require(depth <= MAX_DEPTH, 'depth')
        elif c in ']}':
            depth -= 1
            require(depth >= 0, 'syntax')

def value_guard(value, depth=1, counter=None):
    if counter is None: counter = [0]
    counter[0] += 1
    require(depth <= MAX_DEPTH and counter[0] <= MAX_VALUES, 'value-bounds')
    if isinstance(value, dict):
        for key, child in value.items():
            require(all(ord(c) < 128 for c in key), 'ascii-key')
            value_guard(child, depth + 1, counter)
    elif isinstance(value, list):
        for child in value: value_guard(child, depth + 1, counter)
    elif isinstance(value, str):
        require(all(ord(c) < 128 for c in value), 'ascii-value')

def schema_check(value, schema, definitions, where='$'):
    if '$ref' in schema:
        return schema_check(value, definitions[schema['$ref'].split('/')[-1]], definitions, where)
    if 'oneOf' in schema:
        matches = 0
        for candidate in schema['oneOf']:
            try:
                schema_check(value, candidate, definitions, where)
                matches += 1
            except DescriptorError:
                pass
        require(matches == 1, where + ':oneOf')
        return
    if 'const' in schema:
        require(type(value) is type(schema['const']) and value == schema['const'], where + ':const')
    if 'enum' in schema:
        require(any(type(value) is type(v) and value == v for v in schema['enum']), where + ':enum')
    kind = schema.get('type')
    if kind == 'object':
        require(type(value) is dict, where + ':object')
        require(set(value) == set(schema['required']) == set(schema['properties']), where + ':closed-fields')
        require(schema['additionalProperties'] is False, 'oracle-schema-not-closed')
        for key, child in value.items(): schema_check(child, schema['properties'][key], definitions, where + '.' + key)
    elif kind == 'array':
        require(type(value) is list and schema['minItems'] <= len(value) <= schema['maxItems'], where + ':array')
        for index, child in enumerate(value): schema_check(child, schema['items'], definitions, where + f'[{index}]')
    elif kind == 'string':
        require(type(value) is str and schema['minLength'] <= len(value) <= schema['maxLength'], where + ':string')
        if 'pattern' in schema: require(re.fullmatch(schema['pattern'], value) is not None, where + ':pattern')
    elif kind == 'integer':
        require(type(value) is int and schema['minimum'] <= value <= schema['maximum'], where + ':integer')
    else:
        require(kind is None and ('const' in schema or 'enum' in schema), 'unsupported-oracle-schema')

def semantic_check(value):
    resources = value['resources']
    require(len({x['id'] for x in resources}) == len(resources), 'resource-id-duplicate')
    require(len({x['path'] for x in resources}) == len(resources), 'resource-path-duplicate')
    require(len({x['path'].lower() for x in resources}) == len(resources), 'resource-path-case-collision')
    require(sum(x['bytes'] for x in resources) <= 16 * 1024 * 1024, 'resource-total')
    require(sum(x['kind'] == 'fontSFNT' for x in resources) <= 16, 'font-resource-count')
    catalog = {x['id']: x for x in resources}
    for resource in resources:
        require(resource['provenance'].strip() == resource['provenance'] and bool(resource['provenance'].strip()), 'provenance')
    themes = [value['theme']] if value['mode'] == 'shared' else [value['iOS'], value['android']]
    if value['mode'] == 'platformSpecific':
        require(value['reason'].strip() == value['reason'] and bool(value['reason'].strip()), 'reason')
    for theme in themes:
        typography = theme['typography']
        for style in ('body', 'headline', 'title', 'caption'):
            require(typography[style]['minimumLineBox64'] >= typography[style]['size64'], 'line-box')
        font = typography['font']
        if font['kind'] == 'bundled':
            faces = font['faces']
            require(len({(f['weight'], f['style']) for f in faces}) == len(faces), 'duplicate-font-face')
            require({(typography[s]['weight'], 'normal') for s in ('body','headline','title','caption')}
                    <= {(f['weight'],f['style']) for f in faces}, 'required-font-weight')
            for face in faces:
                resource = catalog.get(face['resourceID'])
                require(resource is not None and resource['kind'] == 'fontSFNT', 'font-resource')
                require(resource['scale'] == 1 and resource['locale'] == 'und' and resource['direction'] == 'neutral', 'font-variant')
        toggle = theme['controls']['toggle']
        require(toggle['thumb64'] + 2 * toggle['inset64'] <= min(toggle['trackWidth64'], toggle['trackHeight64']), 'toggle-fit')
        require(toggle['minimumRow64'] >= toggle['trackHeight64'], 'toggle-row')

def decode(data):
    require(type(data) is bytes and 0 < len(data) <= MAX_BYTES, 'bytes')
    try:
        text = data.decode('utf-8', 'strict')
        raw_guard(text)
        value = json.loads(text, object_pairs_hook=pairs, parse_int=uint, parse_float=reject_number, parse_constant=reject_number)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as error:
        raise DescriptorError('invalid-json') from error
    value_guard(value)
    schema = json.loads((HERE / 'descriptor-schema.json').read_bytes())
    schema_check(value, schema, schema['$defs'])
    semantic_check(value)
    require(canonical(value) == data, 'noncanonical')
    return value

if __name__ == '__main__':
    import hashlib, sys
    path = pathlib.Path(sys.argv[1]) if len(sys.argv) == 2 else HERE / 'mixer-default-appearance-v1.json'
    data = path.read_bytes()
    value = decode(data)
    print(json.dumps({'scope': 'design-only descriptor shape/canonicalization', 'id': value['id'],
                      'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}))
