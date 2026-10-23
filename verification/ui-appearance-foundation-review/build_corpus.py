#!/usr/bin/env python3
"""Independent schema/semantic mutation generator. Never imports the design oracle."""
import base64
import copy
import gzip
import json
import math
import random
import re
from pathlib import Path


def build(archive: Path, output: Path):
    design = archive / 'verification/ui-shared-appearance-contract/v2'
    schema = json.loads((design / 'descriptor-schema.json').read_text())
    default_bytes = (design / 'mixer-default-appearance-v1.json').read_bytes()
    default = json.loads(default_bytes)
    cases = []

    def canonical(value):
        return (json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',', ':')) + '\n').encode()

    def resolve(s):
        return schema['$defs'][s['$ref'].split('/')[-1]] if '$ref' in s else s

    def shape(value, s):
        s = resolve(s)
        if 'oneOf' in s:
            return sum(shape(value, branch) for branch in s['oneOf']) == 1
        if 'const' in s and value != s['const']:
            return False
        if 'enum' in s and (type(value) is bool or value not in s['enum']):
            return False
        kind = s.get('type')
        if kind == 'object':
            return (type(value) is dict and set(value) == set(s['required']) and
                    all(shape(value[k], v) for k, v in s['properties'].items()))
        if kind == 'array':
            return (type(value) is list and s['minItems'] <= len(value) <= s['maxItems'] and
                    all(shape(v, s['items']) for v in value))
        if kind == 'integer':
            return type(value) is int and s['minimum'] <= value <= s['maximum']
        if kind == 'string':
            return (type(value) is str and s['minLength'] <= len(value) <= s['maxLength'] and
                    re.fullmatch(s['pattern'], value) is not None)
        return True

    def valid(value):
        if not shape(value, schema):
            return False
        resources = value['resources']
        if len({r['id'] for r in resources}) != len(resources):
            return False
        if len({r['path'].lower() for r in resources}) != len(resources):
            return False
        if sum(r['bytes'] for r in resources) > 16 * 1024 * 1024:
            return False
        fonts = [r for r in resources if r['kind'] == 'fontSFNT']
        if len(fonts) > 16 or any((r['scale'], r['locale'], r['direction']) != (1, 'und', 'neutral') for r in fonts):
            return False
        if any(r['provenance'] != r['provenance'].strip(' ') for r in resources):
            return False
        themes = [value['theme']] if value['mode'] == 'shared' else [value['iOS'], value['android']]
        if value['mode'] == 'platformSpecific' and value['reason'] != value['reason'].strip(' '):
            return False
        for theme in themes:
            typography = theme['typography']
            styles = [typography[k] for k in ('body', 'caption', 'headline', 'title')]
            if any(s['minimumLineBox64'] < s['size64'] for s in styles):
                return False
            font = typography['font']
            if font['kind'] == 'bundled':
                faces = font['faces']
                if len({(f['weight'], f['style']) for f in faces}) != len(faces):
                    return False
                if not {s['weight'] for s in styles} <= {f['weight'] for f in faces if f['style'] == 'normal'}:
                    return False
                if any(not any(r['id'] == f['resourceID'] and r['kind'] == 'fontSFNT' for r in resources) for f in faces):
                    return False
            toggle = theme['controls']['toggle']
            envelope = toggle['thumb64'] + 2 * toggle['inset64']
            if envelope > min(toggle['trackWidth64'], toggle['trackHeight64']) or toggle['minimumRow64'] < toggle['trackHeight64']:
                return False
        return len(canonical(value)) <= 65536

    def add_raw(name, raw, accepted=False, error=None):
        entry = dict(name=name, base64=base64.b64encode(raw).decode(), accepted=accepted)
        if error:
            entry['error'] = error
        cases.append(entry)

    def add(name, value):
        add_raw(name, canonical(value), valid(value))

    def changed(value, path, replacement=None, remove=False, unknown=False):
        v = copy.deepcopy(value)
        target = v
        for key in path[:-1]:
            target = target[key]
        if unknown:
            target[path[-1]]['unknown'] = 0
        elif remove:
            del target[path[-1]]
        else:
            target[path[-1]] = replacement
        return v

    def walk(base, value, s, path=()):
        s = resolve(s)
        if 'oneOf' in s:
            selected = [branch for branch in s['oneOf'] if shape(value, branch)]
            assert len(selected) == 1
            yield from walk(base, value, selected[0], path)
            return
        label = '/'.join(map(str, path)) or 'root'
        for replacement in [None, True, [], {}]:
            if path and replacement != value:
                add(f'{base}:type:{label}:{repr(replacement)}', changed(seeds[base], path, replacement))
        if type(value) is dict:
            if path:
                add(f'{base}:extra:{label}', changed(seeds[base], path, unknown=True))
            else:
                x = copy.deepcopy(seeds[base]); x['unknown'] = 0; add(f'{base}:extra:root', x)
            for key in value:
                add(f'{base}:missing:{label}/{key}', changed(seeds[base], path + (key,), remove=True))
                yield from walk(base, value[key], s['properties'][key], path + (key,))
        elif type(value) is list:
            for index, item in enumerate(value):
                yield from walk(base, item, s['items'], path + (index,))
        else:
            candidates = []
            if s.get('type') == 'integer':
                candidates += [s['minimum'] - 1, s['minimum'], s['maximum'], s['maximum'] + 1, 2**64-1, 2**64]
            if 'enum' in s:
                candidates += s['enum'] + ['UNKNOWN', 401]
            if 'const' in s:
                candidates += ['', s['const'] + 'x']
            if s.get('type') == 'string':
                candidates += ['', 'A' * s['maxLength'], 'A' * (s['maxLength'] + 1), 'é', '\x7f', '\n']
            for replacement in candidates:
                add(f'{base}:leaf:{label}:{repr(replacement)[:40]}', changed(seeds[base], path, replacement))
        yield None

    def resource(index, **extra):
        return dict(dict(id=f'r{index}', kind='iconPNG', path=f'icons/r{index}.png', sha256='a'*64,
                         bytes=1, provenance='Reviewer synthetic catalog metadata', scale=1,
                         locale='und', direction='neutral'), **extra)

    bundled = copy.deepcopy(default)
    bundled['resources'] = [resource(0, kind='fontSFNT', path='fonts/regular.ttf'), resource(1, kind='fontSFNT', path='fonts/semibold.ttf')]
    bundled['theme']['typography']['font'] = dict(kind='bundled', fallback='none', faces=[
        dict(resourceID='r0', postScriptName='Review-Regular', weight=400, style='normal'),
        dict(resourceID='r1', postScriptName='Review-Semibold', weight=600, style='normal')])
    platform = dict(format=default['format'], id='review.platform', mode='platformSpecific',
                    iOS=copy.deepcopy(bundled['theme']), android=copy.deepcopy(default['theme']),
                    reason='Explicit reviewer alternative', resources=copy.deepcopy(bundled['resources']))
    seeds = dict(shared=default, bundled=bundled, platformSpecific=platform)
    for name, value in seeds.items():
        assert valid(value)
        add(name, value)
        list(walk(name, value, schema))

    # Byte/parser corruption fixtures; successful alternatives must be byte-identical.
    for suffix in [b'', b'\n\n', b'\r\n', b' ', b'{}']:
        if suffix != b'\n':
            add_raw('trailing:' + repr(suffix), default_bytes[:-1] + suffix)
    for prefix in [b' ', b'\xef\xbb\xbf', b'\xff', b'\x00']:
        add_raw('prefix:' + repr(prefix), prefix + default_bytes)
    for number in ['-0', '+0', '00', '0512', '512.0', '512e0', '512E0', '18446744073709551615',
                   '18446744073709551616', '999999999999999999999', 'false', 'true', 'null', 'NaN', 'Infinity']:
        add_raw('numeric-token:' + number, default_bytes.replace(b'"stackGap64":512', ('"stackGap64":' + number).encode()))
    for escaped in ['m\\u006fde', '\\u006dode']:
        add_raw('decoded-duplicate:' + escaped, default_bytes.replace(b'"mode":"shared"', ('"mode":"shared","' + escaped + '":"shared"').encode()), error='duplicateKey')
    for escaped in ['mixer.default.v\\u0031', 'mixer.default.\\ud800', 'mixer.default.\\u00ff', 'mixer.default.\\u007f']:
        add_raw('string-token:' + escaped, default_bytes.replace(b'mixer.default.v1', escaped.encode()))
    add_raw('nested-decoded-duplicate', default_bytes.replace(b'"canvas":"#000000FF"', b'"canvas":"#000000FF","can\\u0076as":"#000000FF"'), error='duplicateKey')
    add_raw('depth16', ('{"a":'*15 + '0' + '}'*15).encode(), error='shape')
    add_raw('depth17', ('{"a":'*16 + '0' + '}'*16).encode(), error='depthLimit')
    for n in [4095, 4096]:
        add_raw(f'value-count:{n+1}', ('{' + ','.join(f'"k{i}":0' for i in range(n)) + '}').encode(), error='shape' if n == 4095 else 'valueLimit')
    add_raw('byte65536-whitespace', b' '*65536, error='syntax')
    add_raw('byte65537-whitespace', b' '*65537, error='byteLimit')
    for n in [512, 513]:
        add_raw(f'decoded-string:{n}', ('"' + '\\u0061'*n + '"').encode(), error='shape')
    for n in [64, 65]:
        add_raw(f'array-count:{n}', ('[' + ','.join('0' for _ in range(n)) + ']').encode(), error='shape')

    # All-font rule is deliberately stronger than the preserved design Python oracle.
    for field, values in [('scale', [1, 2, 4]), ('locale', ['und', 'en']), ('direction', ['neutral', 'leftToRight', 'rightToLeft'])]:
        for v in values:
            x = copy.deepcopy(default); x['resources'] = [resource(0, kind='fontSFNT', **{field: v})]
            add(f'unreferenced-font:{field}:{v}', x)
    for n in [16, 17, 64, 65]:
        x = copy.deepcopy(default); x['resources'] = [resource(i, kind='fontSFNT' if n < 20 else 'iconPNG') for i in range(n)]
        add(f'catalog-count:{n}', x)
    for n in [4, 5]:
        x = copy.deepcopy(default); x['resources'] = [resource(i, bytes=4194304) for i in range(n)]
        add(f'aggregate-mebibytes:{4*n}', x)
    x = copy.deepcopy(default); x['resources'] = [resource(0, path='icons/a.png'), resource(1, path='ICONS/A.PNG')]; add('path-ascii-fold-collision', x)
    for text in ['a/./b', 'a/../b', 'a//b', 'a/', '/a', '.hidden', 'a\\b', 'a b', 'a:b', 'a.../b', 'a/b..']:
        x = copy.deepcopy(default); x['resources'] = [resource(0, path=text)]; add('resource-path:' + text, x)
    for text in [' Leading', 'Trailing ', ' ', 'Quotation " and slash \\ are printable', 'a'*512]:
        x = copy.deepcopy(platform); x['reason'] = text; x['resources'][0]['provenance'] = text; add('printable:' + repr(text)[:40], x)
    for mutation in ['missingFace', 'duplicatePair', 'italicRequired', 'wrongKind', 'fallbackNotFace']:
        x = copy.deepcopy(bundled)
        f = x['theme']['typography']['font']
        if mutation == 'missingFace': f['faces'][1]['resourceID'] = 'missing'
        if mutation == 'duplicatePair': f['faces'].append(copy.deepcopy(f['faces'][0]))
        if mutation == 'italicRequired': f['faces'][1]['style'] = 'italic'
        if mutation == 'wrongKind': x['resources'][0]['kind'] = 'iconPNG'
        if mutation == 'fallbackNotFace': f['fallback'] = 'systemSans'; f['faces'] = f['faces'][:1]
        add('font-semantic:' + mutation, x)

    # Exact 64KiB acceptance and +1 canonical document rejection.
    x = copy.deepcopy(default)
    x['resources'] = [resource(i, path='a'*250 + str(i), provenance='p'*512, locale='e'*64) for i in range(64)]
    excess = len(canonical(x)) - 65536
    for r in x['resources']:
        remove = min(excess, 511); r['provenance'] = 'p'*(512-remove); excess -= remove
    assert excess == 0 and len(canonical(x)) == 65536 and valid(x)
    add('canonical-byte-boundary:65536', x)
    x['resources'][0]['provenance'] += 'p'
    # First entry might already be512; use the trimmed entry instead.
    if len(x['resources'][0]['provenance']) > 512:
        x['resources'][0]['provenance'] = x['resources'][0]['provenance'][:-1]
        next(r for r in x['resources'] if len(r['provenance']) < 512)['provenance'] += 'p'
    assert len(canonical(x)) == 65537
    add('canonical-byte-boundary:65537', x)

    randomizer = random.Random(0x4D49584552)
    for i in range(300):
        b = bytearray(default_bytes)
        b[randomizer.randrange(len(b))] = randomizer.randrange(256)
        try:
            obj = json.loads(b)
            accepted = valid(obj) and canonical(obj) == b
        except (ValueError, UnicodeError, TypeError):
            accepted = False
        add_raw(f'seeded-byte-mutation:{i}', b, accepted)
    path = output / '.build/independent-corpus.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cases, separators=(',', ':')) + '\n')
    packed = output / 'independent-corpus.json.gz'
    packed.write_bytes(gzip.compress(path.read_bytes(), mtime=0))
    return dict(cases=len(cases), accepted=sum(c['accepted'] for c in cases), rejected=sum(not c['accepted'] for c in cases),
                expected_error_cases=sum('error' in c for c in cases), corpus=str(path.relative_to(output)), packed_corpus=packed.name)


if __name__ == '__main__':
    import sys
    print(build(Path(sys.argv[1]), Path(sys.argv[2])))
