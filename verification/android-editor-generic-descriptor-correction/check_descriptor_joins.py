"""Additive, data-only descriptor facets over accepted immutable observations.

This utility neither executes Java nor imports an auditor. Accepted raw/compact
consistency is a separately pinned premise. No subject is qualified by a facet.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import math
from pathlib import Path
import struct
import sys
import types

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
STATE = Path('verification/android-editor-membership-compiled-boundary-qualification/state-qualification')
RUN = STATE / 'full-candidate-v1/run-33'
MANIFEST = STATE / 'canonical-query-offline-addendum-v1/input-manifest.json'
LEDGER = STATE / 'offline-reconciler-run3/complete-proved-unresolved-ledger.json'
REFERENCE = Path('verification/android-editor-membership-compiled-boundary-qualification/semantic-review-candidate-v1')
SELECTION = Path('verification/android-editor-boundary-root-review/generic-descriptor-join-selection.json')
ACCEPTANCE = Path('verification/android-editor-boundary-root-review/finite-observation-consistency-acceptance.json')
CORRECTION_SELECTION = Path('verification/android-editor-boundary-root-review/generic-descriptor-correction-selection.json')
PINS = {
    str(CORRECTION_SELECTION): '453b246bc9999b38d89f907c48e476119e7ac4a689094901e209f8ba7612cc08',
    str(SELECTION): 'fc6cc81691b63c7bf2c8c87854e30e101fb71715c4f28dc768788c0f8d7ee90e',
    str(ACCEPTANCE): '65c6d0a51a21ef10a4ea9c814ab9c4223f2fc7ca79157fcec673555ed41dcd85',
    str(STATE / 'offline-reconciler-v3/seal.json'): '969fb9ce4b3dbe806debb2b5124b6c0d9b176e89b55955b3c0fd72eda78d0c1f',
    str(STATE / 'offline-reconciler-run3/seal.json'): '58ae832a2c8f42ca84c2646f7068a9c21a6841abb914dfda95f6614a7671597d',
    str(STATE / 'canonical-query-offline-addendum-v1/seal.json'): '10665c5e5efb5e93d6534eda17e57d2c7a239cca08a55c5508d87185087aa4b7',
    str(STATE / 'canonical-query-offline-run1/seal.json'): '47440523b4cd892ef47a4a4b4c2b7d6f2680d58871049c2d6cb5c319f1566d8a',
}
SPEC_SHA = 'b3b7353c6482618593de11d6b6e5fb2d51faa7787e68deef37ec339f90dd7087'
PARSER = STATE / 'offline-reconciler-v3/code/classfile.py'
DIRECT = {
    'performContextMenuAction': ('performContextMenuAction', '(I)Z', 570),
    'reportFullscreenMode': ('reportFullscreenMode', '(Z)Z', 580),
    'requestCursorUpdates': ('requestCursorUpdates', '(I)Z', 590),
    'requestCursorUpdatesFiltered': ('requestCursorUpdates', '(II)Z', 601),
    'beginBatchEdit': ('beginBatchEdit', '()Z', 610),
    'endBatchEdit': ('endBatchEdit', '()Z', 619),
    'clearMetaKeyStates': ('clearMetaKeyStates', '(I)Z', 629),
    'commitText': ('commitText', '(Ljava/lang/CharSequence;I)Z', 641),
    'commitTextWithAttributes': ('commitText', '(Ljava/lang/CharSequence;ILandroid/view/inputmethod/TextAttribute;)Z', 660),
    'setComposingText': ('setComposingText', '(Ljava/lang/CharSequence;I)Z', 672),
    'setComposingTextWithAttributes': ('setComposingText', '(Ljava/lang/CharSequence;ILandroid/view/inputmethod/TextAttribute;)Z', 691),
    'setComposingRegion': ('setComposingRegion', '(II)Z', 702),
    'setComposingRegionWithAttributes': ('setComposingRegion', '(IILandroid/view/inputmethod/TextAttribute;)Z', 720),
    'finishComposingText': ('finishComposingText', '()Z', 729),
    'deleteSurroundingText': ('deleteSurroundingText', '(II)Z', 740),
    'deleteSurroundingTextInCodePoints': ('deleteSurroundingTextInCodePoints', '(II)Z', 751),
    'setSelection': ('setSelection', '(II)Z', 762),
    'performEditorAction': ('performEditorAction', '(I)Z', 773),
    'setImeConsumesInput': ('setImeConsumesInput', '(Z)Z', 783),
    'commitCompletion': ('commitCompletion', '(Landroid/view/inputmethod/CompletionInfo;)Z', 803),
}
QUERY = {
    'getCursorCapsMode': ('getCursorCapsMode', '(I)I', 218),
    'getSelectedText': ('getSelectedText', '(I)Ljava/lang/CharSequence;', 231),
    'getTextBeforeCursor': ('getTextBeforeCursor', '(II)Ljava/lang/CharSequence;', 242),
    'getTextAfterCursor': ('getTextAfterCursor', '(II)Ljava/lang/CharSequence;', 253),
    'getExtractedText': ('getExtractedText', '(Landroid/view/inputmethod/ExtractedTextRequest;I)Landroid/view/inputmethod/ExtractedText;', 270),
    'getSurroundingText': ('getSurroundingText', '(III)Landroid/view/inputmethod/SurroundingText;', 282),
    'takeSnapshot': ('takeSnapshot', '()Landroid/view/inputmethod/TextSnapshot;', 291),
}
SPECIAL_FRAME = ('dev/mixer/android/NativeEditorConnectionV2$Api33', 'lambda$setComposingRegion$4', '(IILandroid/view/inputmethod/TextAttribute;)Ljava/lang/Boolean;', 7)
SPECIAL_PAIR = ['(II)Z', '(IILandroid/view/inputmethod/TextAttribute;)Z']


class Refusal(ValueError):
    pass


def need(condition, message):
    if not condition:
        raise Refusal(message)


def same(a, b):
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(same(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    return a == b


def pairs(values):
    result = {}
    for key, value in values:
        need(key not in result, 'duplicate JSON key: ' + key)
        result[key] = value
    return result


def loads(data):
    def nonfinite(value):
        raise Refusal('nonstandard JSON number: ' + value)
    return json.loads(data, object_pairs_hook=pairs, parse_constant=nonfinite)


def identity(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def descriptor(text, *, receiver_units=None):
    """JVMS17 grammar; optional exact receiver context adds its parameter unit.

    With no receiver context this is only syntactic parsing, never a contextual
    invocation/declaration qualification. descriptor_context exposes that limit.
    """
    need(receiver_units is None or type(receiver_units) is int and receiver_units in (0, 1), 'receiver context must be exact zero/static or one/instance unit')
    need(type(text) is str and text.startswith('(') and len(text) <= 65535, 'method descriptor opening/size')
    pos = 1

    def field():
        nonlocal pos
        start = pos
        dims = 0
        while pos < len(text) and text[pos] == '[':
            dims += 1
            pos += 1
        need(dims <= 255 and pos < len(text), 'array descriptor dimension/element')
        token = text[pos]
        pos += 1
        if token == 'L':
            end = text.find(';', pos)
            need(end > pos, 'object descriptor terminator/name')
            name = text[pos:end]
            # JVMS17 4.2.1/4.2.2 excludes only . ; [ / from each nonempty
            # unqualified class-name segment. Parentheses and whitespace are
            # permitted ClassName characters, even though Java source is stricter.
            need(all(part and not any(c in '.;[' for c in part) for part in name.split('/')), 'object descriptor internal class grammar')
            pos = end + 1
        else:
            need(token in 'BCDFIJSZ', 'field descriptor primitive')
        return text[start:pos]

    args = []
    while pos < len(text) and text[pos] != ')':
        args.append(field())
    need(pos < len(text) and text[pos] == ')', 'method descriptor closing')
    pos += 1
    if pos < len(text) and text[pos] == 'V':
        result = 'V'
        pos += 1
    else:
        result = field()
    need(pos == len(text), 'method descriptor trailing content')
    explicit_units = sum(2 if x in ('D', 'J') else 1 for x in args)
    need(explicit_units <= 255, 'method descriptor explicit parameter units')
    if receiver_units is not None:
        need(explicit_units + receiver_units <= 255, 'method parameter units include retained instance/interface receiver')
    return args, result


def descriptor_context(text, *, access=None, opcode=None):
    """Context from retained declaration access/invocation opcode, not names."""
    receiver_units = None
    evidence = {}
    if access is not None:
        need(type(access) is int and access >= 0, 'retained method access flags')
        receiver_units = 0 if access & 8 else 1
        evidence['access'] = access
    if opcode is not None:
        need(type(opcode) is int, 'retained invocation opcode integer')
        if opcode not in (182, 183, 184, 185):
            args, result = descriptor(text)
            return {'status': 'unresolved-receiver-context', 'reason': 'unsupported invocation opcode for selected contextual check', 'opcode': opcode, 'receiver_units': None, 'evidence': {**evidence, 'opcode': opcode}, 'explicit_parameter_units': sum(2 if x in ('D', 'J') else 1 for x in args), 'result': result}
        invoked_units = 0 if opcode == 184 else 1
        need(receiver_units is None or receiver_units == invoked_units, 'retained access/opcode receiver context agrees')
        receiver_units = invoked_units
        evidence['opcode'] = opcode
    args, result = descriptor(text, receiver_units=receiver_units)
    explicit_units = sum(2 if x in ('D', 'J') else 1 for x in args)
    return {'status': 'passed' if receiver_units is not None else 'unresolved-receiver-context', 'reason': None if receiver_units is not None else 'retained access/invocation receiver context absent; grammar only', 'explicit_parameter_units': explicit_units, 'receiver_units': receiver_units, 'total_parameter_units': None if receiver_units is None else explicit_units + receiver_units, 'evidence': evidence, 'result': result, 'scope': 'retained method descriptor parameter budget only; no execution qualification'}


def constant_strings(data):
    """Read only CONSTANT_String entries; no class loading or product execution."""
    pos = 10
    count = int.from_bytes(data[8:10], 'big')
    cp = [None]
    while len(cp) < count:
        tag = data[pos]
        pos += 1
        if tag == 1:
            size = int.from_bytes(data[pos:pos + 2], 'big')
            pos += 2
            # Classfile UTF8 uses the modified UTF8 NUL and UTF16-surrogate form.
            # Retain those exact code units; only exact ASCII descriptor/hook
            # literals are used by this utility's compiled declaration check.
            cp.append((tag, data[pos:pos + size].replace(b'\xc0\x80', b'\x00').decode('utf-8', errors='surrogatepass')))
            pos += size
        elif tag in (7, 8, 16, 19, 20):
            cp.append((tag, int.from_bytes(data[pos:pos + 2], 'big')))
            pos += 2
        elif tag in (3, 4, 9, 10, 11, 12, 17, 18):
            cp.append((tag, None))
            pos += 4
        elif tag in (5, 6):
            cp.extend([(tag, None), None])
            pos += 8
        elif tag == 15:
            cp.append((tag, None))
            pos += 3
        else:
            raise Refusal('constant pool tag')
    return {i: cp[x[1]][1] for i, x in enumerate(cp) if x is not None and x[0] == 8}


class Inputs:
    def __init__(self):
        self.allowed = {}
        self.used = {}
        for path, sha in PINS.items():
            data = self.pinned(path, sha)
            if path.endswith('/seal.json'):
                for member in loads(data)['members']:
                    self.allowed[str(Path(path).parent / member['path'])] = {k: member[k] for k in ('bytes', 'sha256')}
        manifest = self.json(MANIFEST)
        for member in manifest['files']:
            path = Path(member['path'])
            need(not path.is_absolute() and '..' not in path.parts, 'bounded manifest member')
            current = {k: member[k] for k in ('bytes', 'sha256')}
            need(str(path) not in self.allowed or self.allowed[str(path)] == current, 'manifest member identity conflict')
            self.allowed[str(path)] = current
        self.json(ACCEPTANCE, pinned=True)

    def pinned(self, relative, sha):
        path = ROOT / relative
        need(not path.is_symlink(), 'no substituted input symlink')
        data = path.read_bytes()
        need(identity(data)['sha256'] == sha, 'exact selected SHA: ' + str(relative))
        self.used[str(relative)] = identity(data)
        return data

    def read(self, relative):
        name = str(relative)
        need(name in self.allowed, 'unreleased input: ' + name)
        data = (ROOT / name).read_bytes()
        need(identity(data) == self.allowed[name], 'immutable input identity: ' + name)
        self.used[name] = identity(data)
        return data

    def json(self, relative, pinned=False):
        return loads(self.pinned(relative, PINS[str(relative)]) if pinned else self.read(relative))


class Joiner:
    def __init__(self, inputs):
        self.inputs = inputs
        parser_data = inputs.read(PARSER)
        need(identity(parser_data)['sha256'] == '211ad86c8b0ffd9048d322efbb9e93bc3fc6606dcf745788bb36ec6052adfd2d', 'sealed classfile reader source')
        # Execute only the exact already-hashed reader source as a data parser.
        # No importlib cache loader, module search or bytecode cache is consulted.
        parser = types.ModuleType('_sealed_data_classfile_reader')
        parser.__file__ = str(ROOT / PARSER)
        exec(compile(parser_data, str(ROOT / PARSER), 'exec'), parser.__dict__)
        self.classmap = inputs.json(RUN / 'class-map.json')
        self.freeze = inputs.json(RUN / 'source-freeze.json')
        self.sources = {}
        for member in self.freeze['sources']:
            path = RUN / Path(member['path']).name
            data = inputs.read(path)
            need(identity(data) == {k: member[k] for k in ('bytes', 'sha256')}, 'compiled source identity')
            self.sources[path.name] = identity(data)
        self.classes = {}
        self.methods = {}
        self.instructions = {}
        for relative, expected in self.classmap.items():
            data = inputs.read(RUN / 'classes' / relative)
            need(identity(data) == expected, 'full compiled host class-map identity')
            value = parser.parse(data)
            need(value['class'] + '.class' == relative, 'exact class internal identity')
            self.classes[value['class']] = value
            strings = constant_strings(data)
            for method in value['methods']:
                method['parameter_context'] = descriptor_context(method['descriptor'], access=method['access'])
                key = (value['class'], method['name'], method['descriptor'])
                self.methods[key] = method
                method['literal_strings'] = set()
                for ins in method['instructions']:
                    self.instructions[key + (ins['bci'],)] = ins
                    raw = bytes.fromhex(ins['bytes'])
                    index = raw[1] if ins['opcode'] == 0x12 else int.from_bytes(raw[1:3], 'big') if ins['opcode'] == 0x13 else None
                    if index in strings:
                        method['literal_strings'].add(strings[index])
        spec_data = (HERE / 'spec/string-java-se17.json').read_bytes()
        need(identity(spec_data)['sha256'] == SPEC_SHA, 'exact root-approved two-edge String specification evidence')
        self.spec_edges = {tuple(edge) for edge in loads(spec_data)['allowed_nominal_edges']}
        need(self.spec_edges == {('java/lang/String', 'java/lang/CharSequence'), ('java/lang/String', 'java/lang/Object')}, 'only root-approved spec nominal edges')
        self.ledger = inputs.json(LEDGER)
        self.contract = self.public_contract()

    def resolve(self, owner, name, desc):
        visited = set()
        while owner in self.classes and owner not in visited:
            visited.add(owner)
            if (owner, name, desc) in self.methods:
                return owner, self.methods[(owner, name, desc)]
            owner = self.classes[owner]['super']
        return None

    def assignable(self, actual, declared):
        if actual == declared:
            return {'status': 'passed', 'basis': 'exact-nominal-class', 'path': [actual]}
        if (actual, declared) in self.spec_edges:
            return {'status': 'passed', 'basis': 'official-JavaSE17-specification', 'path': [actual, declared], 'spec_sha256': SPEC_SHA}
        if actual.startswith('[') or declared.startswith('['):
            return {'status': 'unresolved', 'reason': 'array covariance or standard array supertype specification is outside selected evidence'}
        queue = [(actual, [actual])]
        seen = set()
        unknown = []
        while queue:
            current, path = queue.pop(0)
            if current in seen:
                continue
            seen.add(current)
            if current == declared:
                return {'status': 'passed', 'basis': 'retained-compiled-class-hierarchy', 'path': path, 'class_sha256': {k: self.classmap[k + '.class']['sha256'] for k in path[:-1]}}
            if current not in self.classes:
                if current != 'java/lang/Object':
                    unknown.append(current)
                continue
            node = self.classes[current]
            queue.extend((parent, path + [parent]) for parent in [node['super'], *node['interfaces']] if parent)
        if unknown or actual not in self.classes or declared not in self.classes:
            return {'status': 'unresolved', 'reason': 'unretained nominal hierarchy', 'unknown': sorted(set(unknown))}
        return {'status': 'failed', 'reason': 'retained class hierarchy has no assignable relation'}

    def value(self, value, result, native=False):
        need(type(value) is dict and type(value.get('kind')) is str, 'typed actual value object')
        kind = value['kind']
        if kind == 'exception':
            need(set(value) == {'kind', 'class', 'identity'} and type(value['class']) is str and bool(value['class']) and type(value['identity']) is str and value['identity'].startswith(value['class'] + '@'), 'original observed exception identity/class')
            descriptor('()L' + value['class'].replace('.', '/') + ';')
            need(bool(value['identity'].split('@', 1)[1]), 'exception identity suffix')
            return {'status': 'observed-exception', 'normal_return': 'pending', 'actual': value}
        if result == 'V':
            need(value == {'kind': 'null' if native else 'void'}, 'void outcome serialization')
        elif result == 'Z':
            need(set(value) == {'kind', 'value'} and kind == 'boolean' and type(value['value']) is bool, 'JVM boolean return')
        elif result in ('B', 'S', 'I', 'J'):
            bits = {'B': 8, 'S': 16, 'I': 32, 'J': 64}[result]
            need(set(value) == {'kind', 'value'} and kind == 'integer' and type(value['value']) is int and -(2 ** (bits - 1)) <= value['value'] < 2 ** (bits - 1), 'JVM signed integer kind/range')
        elif result in ('F', 'D'):
            need(set(value) == {'kind', 'value'} and kind == 'floating' and type(value['value']) is float and math.isfinite(value['value']), 'JVM finite floating return')
            need(result != 'F' or abs(value['value']) <= 3.4028234663852886e38, 'JVM float32 range')
        elif result == 'C':
            need(set(value) == {'kind', 'value'} and kind == 'character' and type(value['value']) is str and len(value['value']) == 1 and ord(value['value']) <= 0xffff, 'JVM char is one UTF16 code unit')
        else:
            need(result.startswith(('L', '[')), 'reference result descriptor')
            if kind == 'null':
                need(set(value) == {'kind'}, 'exact null value fields')
                return {'status': 'passed', 'basis': 'nullable-reference'}
            if kind == 'string':
                actual = 'java/lang/String'
                need(set(value) == {'kind', 'value', 'identity'} and type(value['value']) is str, 'immutable String snapshot')
            else:
                need(kind in ('reference', 'typed-snapshot') and set(value) == ({'kind', 'class', 'identity'} if kind == 'reference' else {'kind', 'class', 'identity', 'fields'}), 'actual reference tag/fields')
                need(type(value['class']) is str and bool(value['class']), 'runtime reference class')
                actual = value['class'].replace('.', '/')
                if kind == 'typed-snapshot':
                    need(type(value['fields']) is list, 'retained typed snapshot fields')
            need(type(value['identity']) is str and value['identity'].startswith(actual.replace('/', '.') + '@'), 'reference identity agrees with runtime class')
            descriptor('()' + (actual if actual.startswith('[') else 'L' + actual + ';'))
            relation = self.assignable(actual, result[1:-1] if result.startswith('L') else result)
            need(relation['status'] != 'failed', 'actual runtime reference is not assignable to declared return')
            return relation
        return {'status': 'passed', 'basis': 'exact-primitive-kind-and-range'}

    def public_contract(self):
        reference = self.inputs.json(REFERENCE / 'reference-obligations.json')
        interface = self.classes['android/view/inputmethod/InputConnection']
        actual = {m['name'] + m['descriptor'] for m in interface['methods'] if not m['name'].startswith('<') and not m['access'] & 8}
        need(actual == set(reference['exact38_descriptors']) and len(actual) == 38, 'exact immutable SDK-facing38 set')
        result = {}
        for method in interface['methods']:
            name, desc = method['name'], method['descriptor']
            if name + desc not in actual:
                continue
            found = self.resolve('dev/mixer/android/NativeEditorConnectionV2$Api34', name, desc)
            need(found is not None, 'concrete public method resolution')
            owner, concrete = found
            need(concrete['access'] & 1 and not concrete['access'] & (8 | 1024), 'concrete public instance method')
            family = name
            if (name, desc) in {(v[0], v[1]) for k, v in DIRECT.items() if k.endswith('WithAttributes')}:
                family += 'WithAttributes'
            if (name, desc) == ('requestCursorUpdates', '(II)Z'):
                family = 'requestCursorUpdatesFiltered'
            need(family not in result, 'unique exact family mapping')
            result[family] = {'family': family, 'name': name, 'descriptor': desc, 'declaring_class': owner, 'class_sha256': self.classmap[owner + '.class']['sha256'], 'source_sha256': self.sources[self.classes[owner]['source_file']]['sha256']}
            result[family]['parameter_context'] = descriptor_context(desc, access=concrete['access'])
        need(len(result) == 38, 'all38 public family records')
        for label, table, returns in [('DirectBoundaryStates', DIRECT, 'Z'), ('QueryBoundaryStates', QUERY, 'Ljava/lang/Object;')]:
            owner = 'dev/mixer/android/' + label
            desc = '(Landroid/view/inputmethod/InputConnection;Ljava/lang/String;)' + returns
            method = self.methods[(owner, 'operation', desc)]
            calls = [x for x in method['instructions'] if x.get('target', {}).get('owner') == 'android/view/inputmethod/InputConnection']
            need(len(calls) == len(table), 'exact source-selected operation dispatch set')
            for family, (name, signature, bci) in table.items():
                ins = self.instructions[(owner, 'operation', desc, bci)]
                need(ins['mnemonic'] == 'invokeinterface' and ins['target'] == {'owner': 'android/view/inputmethod/InputConnection', 'name': name, 'descriptor': signature}, 'exact producer dispatch BCI/opcode/callee')
                need(result[family]['name'] == name and result[family]['descriptor'] == signature, 'source family matches exact public contract')
                result[family]['producer_dispatch'] = {'class': owner, 'method': 'operation', 'descriptor': desc, 'bci': bci, 'opcode': ins['mnemonic'], 'callee': ins['target'], 'class_sha256': self.classmap[owner + '.class']['sha256'], 'source_sha256': self.sources[label + '.java']['sha256']}
        old = {x['descriptor']: x for x in self.ledger['exact38_compiled_bindings']}
        for item in result.values():
            known = old[item['name'] + item['descriptor']]
            need(all(item[k] == known[k] for k in ('declaring_class', 'class_sha256', 'source_sha256')), 'unchanged accepted exact38 binding')
        close_key = ('dev/mixer/android/CloseBoundaryStates', 'run', '(Ljava/lang/String;)Ljava/util/Map;', 292)
        close_ins = self.instructions[close_key]
        need(close_ins['mnemonic'] == 'invokeinterface' and close_ins['target'] == {'owner': 'android/view/inputmethod/InputConnection', 'name': 'closeConnection', 'descriptor': '()V'}, 'exact close producer public invocation')
        result['closeConnection']['producer_dispatch'] = {'class': close_key[0], 'method': close_key[1], 'descriptor': close_key[2], 'bci': close_key[3], 'opcode': close_ins['mnemonic'], 'callee': close_ins['target'], 'class_sha256': self.classmap[close_key[0] + '.class']['sha256'], 'source_sha256': self.sources['CloseBoundaryStates.java']['sha256']}
        return result

    def compiled_call(self, frame):
        need(type(frame) is dict and type(frame.get('bci')) is int and frame['bci'] >= 0, 'exact caller BCI integer')
        key = (frame['class'].replace('.', '/'), frame['method'], frame['descriptor'], frame['bci'])
        need(key in self.instructions, 'actual compiled caller method/descriptor/BCI')
        descriptor_context(frame['descriptor'], access=self.methods[key[:3]]['access'])
        ins = self.instructions[key]
        need(ins['opcode'] in (182, 183, 184, 185) and type(frame['line']) is int and ins['line'] == frame['line'], 'compiled invocation opcode/source line')
        target = ins['target']
        found = self.resolve(target['owner'], target['name'], target['descriptor'])
        need(found is not None, 'actual callee descriptor has retained compiled declaration')
        owner, method = found
        descriptor_context(target['descriptor'], access=method['access'], opcode=ins['opcode'])
        need(bool(method['access'] & 8) == (ins['opcode'] == 184), 'callee instance/static invocation contract')
        return key, ins, owner, method

    def completion(self, row, item):
        frames = item['production_frames']
        need(type(frames) is list and 0 < len(frames) <= 128, 'selected completion frames')
        key, ins, owner, method = self.compiled_call(frames[0])
        target = ins['target']
        if ins['opcode'] == 184:
            need(item['receiver_identity'] is None, 'static callee receiver')
            receiver = {'status': 'passed', 'basis': 'static-no-receiver'}
        else:
            matches = [x for x in row['native_receiver_bindings'] if x['global_identity'] == item['receiver_identity']]
            need(len(matches) == 1, 'exact observed global native receiver')
            receiver = self.assignable(matches[0]['class'].replace('.', '/'), target['owner'])
            need(receiver['status'] != 'failed', 'actual native receiver not assignable to compiled owner')
            if ins['opcode'] in (182, 185):
                actual = self.resolve(matches[0]['class'].replace('.', '/'), target['name'], target['descriptor'])
                if actual is None:
                    return {'status': 'unresolved-native-dispatch', 'caller': {'class': key[0], 'method': key[1], 'descriptor': key[2], 'bci': key[3], 'opcode': ins['mnemonic']}, 'compiled_callee': target, 'receiver': receiver, 'original_completion': item, 'reason': 'unretained actual receiver method resolution; no normal-return credit'}
                need(not actual[1]['access'] & (8 | 1024), 'exact observed receiver resolves a retained concrete instance callee')
                owner, method = actual
        result = {'caller': {'class': key[0], 'method': key[1], 'descriptor': key[2], 'bci': key[3], 'opcode': ins['mnemonic'], 'class_sha256': self.classmap[key[0] + '.class']['sha256']}, 'compiled_callee': target, 'resolved_declaring_class': owner, 'resolved_class_sha256': self.classmap[owner + '.class']['sha256'], 'receiver': receiver, 'original_completion': item, 'parameter_contexts': {'caller': descriptor_context(key[2], access=self.methods[key[:3]]['access']), 'symbolic_callee': descriptor_context(target['descriptor'], access=self.resolve(target['owner'], target['name'], target['descriptor'])[1]['access'], opcode=ins['opcode']), 'resolved_callee': descriptor_context(target['descriptor'], access=method['access'], opcode=ins['opcode'])}}
        if item['completion'] == 'exception':
            need(item['descriptor'] == 'hook-exception' and item['value'] == {'kind': 'null'}, 'hook exception is not a normal return descriptor/value')
            value = {'kind': 'exception', 'class': item['original_exception_class'], 'identity': item['original_exception_identity']}
            result['value'] = self.value(value, descriptor(target['descriptor'], receiver_units=0 if ins['opcode'] == 184 else 1)[1])
            result['status'] = 'joined-observed-hook-exception; normal-body-return-pending' if receiver['status'] == 'passed' else 'unresolved-hook-exception-receiver; normal-body-return-pending'
            return result
        need(item['completion'] == 'return' and item['original_exception_class'] is None and item['original_exception_identity'] is None, 'normal completion original exception fields')
        descriptor(item['descriptor'], receiver_units=0 if ins['opcode'] == 184 else 1)
        special = row.get('family') == 'setComposingRegionWithAttributes' and key == SPECIAL_FRAME and target == {'owner': 'android/view/inputmethod/InputConnection', 'name': 'setComposingRegion', 'descriptor': SPECIAL_PAIR[1]} and owner == 'android/view/inputmethod/BaseInputConnection'
        if item['descriptor'] != target['descriptor']:
            need(special and item['descriptor'] == SPECIAL_PAIR[0] and item['native_outcome_association'] == 'original-own-hook-event' and 'delegated_leaf_descriptor_pair' not in item, 'completion descriptor differs from exact compiled callee')
            need((owner, 'setComposingRegion', SPECIAL_PAIR[0]) in self.methods, 'exact delegated inner compiled declaration')
            result['adapter'] = 'root-selected-composing-attributes-inner-return; accepted-raw-association-composed'
            method = self.methods[(owner, 'setComposingRegion', SPECIAL_PAIR[0])]
        elif item['native_outcome_association'] == 'selected-original-delegated-overload-return':
            need(special and item.get('delegated_leaf_descriptor_pair') == SPECIAL_PAIR, 'only exact selected composing-attributes delegated pair')
            result['adapter'] = 'root-selected-composing-attributes-outer-return; accepted-raw-association-composed'
        else:
            need(item['native_outcome_association'] == 'original-own-hook-event' and 'delegated_leaf_descriptor_pair' not in item, 'normal completion own-hook association')
        need(item['descriptor'] in method['literal_strings'] and item['method'] in method['literal_strings'], 'compiled native declaration contains exact outcome descriptor and hook label literals')
        result['value'] = self.value(item['value'], descriptor(item['descriptor'])[1], native=True)
        result['status'] = 'joined-normal-return' if receiver['status'] == result['value']['status'] == 'passed' else 'unresolved-reference-assignability'
        return result

    def row(self, row, prior, filename):
        need(type(row) is dict and row.get('complete_raw_trace_retained') is True, 'accepted compact projection with retained raw backing')
        need(row.get('state') == prior['state'] and row.get('family') == prior['family'] and row.get('historical_id') == prior['historical_id'], 'unchanged exact accepted row locator/identity')
        points = row['selected_immutable_event_points']
        completions = row['selected_actual_native_completions']
        need(len(points) == prior['selected_events'] and len(completions) == prior['selected_native_completions'], 'accepted selected event/completion counts unchanged')
        missing = bool(points) and not completions
        need(missing == prior['missing_selected_native_completion'], 'missing native observations preserved')
        need(bool(points) or not completions, 'zero-selected rows receive no native credit')
        result = {'state': row['state'], 'family': row.get('family'), 'historical_id': row.get('historical_id'), 'public_result': None, 'native_completions': [], 'missing_selected_native_completion': missing, 'qualification_status': 'pending-original-required-cases-and-outcomes'}
        if row.get('historical_id'):
            need(row['enclosing_actual_outcome']['kind'] in ('void', 'exception'), 'historical enclosing scenario separate from public/helper result')
            result['historical_enclosing_outcome'] = row['enclosing_actual_outcome']
        elif row.get('family'):
            family = row['family']
            table = QUERY if filename.startswith('query-') else DIRECT
            prefix = 'query-' if table is QUERY else 'direct-'
            need(family in table and filename == prefix + family + '.rows.jsonl.gz', 'exact public producer family source/file')
            binding = self.contract[family]
            result['public_result'] = {'binding': binding, 'actual': row['actual_operation_outcome'], 'value': self.value(row['actual_operation_outcome'], descriptor(binding['descriptor'], receiver_units=1)[1])}
        else:
            need(filename == 'direct-close.rows.jsonl.gz' and 'original_attempt_close' in row, 'known exact close producer')
            result['public_result'] = {'binding': self.contract['closeConnection'], 'actual': row['actual_enclosing_outcome'], 'value': self.value(row['actual_enclosing_outcome'], 'V'), 'scope': 'direct close enclosing outcome only; missing native completion remains missing'}
        allowed = {}
        bindings = {x['row_identity']: x['global_identity'] for x in row['native_receiver_bindings']}
        for point in points:
            need(type(point['sequence_index']) is int, 'selected exact event index')
            event = point['native_event']
            allowed[point['sequence_index']] = (event['method'], bindings.get(event['receiver_identity']), point['production_frames'])
        for pair in row['selected_actual_call_pairs']:
            index = pair['same_invocation_before_return_sequence_index']
            if index is not None:
                need(type(index) is int, 'paired exact return event index')
                allowed[index] = (pair['method'], bindings.get(pair['receiver_identity']), pair['production_frames'])
        for item in completions:
            index = item['native_event_sequence_index']
            need(type(index) is int and index in allowed, 'completion belongs to selected exact invocation')
            method, receiver, frames = allowed[index]
            need(item['method'] == method and item['receiver_identity'] == receiver and same(item['production_frames'], frames), 'completion exact selected method/receiver/caller frames')
            result['native_completions'].append(self.completion(row, item))
        if row.get('family') == 'setComposingRegionWithAttributes' and any(x['completion'] == 'return' for x in completions):
            need([x['descriptor'] for x in completions] == SPECIAL_PAIR and same(completions[0]['value'], completions[1]['value']), 'exact selected inner/outer composing return pair/order/value')
        expected = [({'kind': 'exception', 'class': x['original_exception_class'], 'identity': x['original_exception_identity'], 'observation': 'hook exception; normal native body outcome pending'} if x['completion'] == 'exception' else {'kind': 'void'} if descriptor(x['descriptor'])[1] == 'V' else x['value']) for x in completions]
        need(same(expected, prior['actual_selected_native_typed_outcomes']), 'exact accepted native typed observations unchanged')
        return result


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=True) + '\n')


def run(output):
    inputs = Inputs()
    joiner = Joiner(inputs)
    source_seal = loads((HERE / 'source-seal.json').read_bytes())
    for item in source_seal['members']:
        need(identity((HERE / item['path']).read_bytes()) == {k: item[k] for k in ('bytes', 'sha256')}, 'frozen new utility source')
    expected_inputs = loads((HERE / 'prepared-input-manifest.json').read_bytes())
    need(same(expected_inputs['validated_prepass_inputs'], inputs.used), 'same exact prepared sources/inputs before streaming pass')
    files = []
    findings = []
    counts = collections.Counter()
    for file in joiner.ledger['files']:
        if 'input_path' not in file:
            continue
        raw_path = file['input_path']
        compact_path = raw_path + '.compact.jsonl'
        need(inputs.allowed[raw_path] == {k: file[k] for k in ('bytes', 'sha256')} and inputs.allowed[compact_path] == file['compact'], 'accepted raw/compact immutable identity reference')
        rows = []
        digest = hashlib.sha256()
        size = 0
        with (ROOT / compact_path).open('rb') as stream:
            for number, line in enumerate(stream, 1):
                need(len(line) <= 128 * 1024 * 1024, 'bounded compact row')
                digest.update(line)
                size += len(line)
                need(number <= len(file['rows']), 'no extra compact rows')
                observed = loads(line)
                counts['recorded_selected_native_completions'] += len(observed['selected_actual_native_completions'])
                counts['selected_events'] += len(observed['selected_immutable_event_points'])
                counts['no_selected_rows'] += not observed['selected_immutable_event_points']
                try:
                    result = joiner.row(observed, file['rows'][number - 1], file['file'])
                except (Refusal, KeyError, TypeError, IndexError) as failure:
                    result = {'state': file['rows'][number - 1]['state'], 'status': 'finding', 'reason': str(failure), 'qualification_status': 'pending', 'original_selected_native_completions_retained': observed['selected_actual_native_completions']}
                    findings.append({'file': compact_path, 'row': number, **result})
                rows.append(result)
                counts['rows'] += 1
                if result.get('missing_selected_native_completion'):
                    counts['missing_selected_native_completion'] += 1
                if result.get('public_result'):
                    counts['public_result_rows'] += 1
                    counts['public_' + result['public_result']['value']['status']] += 1
                for completion in result.get('native_completions', []):
                    counts['native_completion_rows'] += 1
                    counts[completion['status']] += 1
        actual = {'bytes': size, 'sha256': digest.hexdigest()}
        need(actual == inputs.allowed[compact_path] and len(rows) == len(file['rows']), 'exact streamed compact file hash/row count')
        inputs.used[compact_path] = actual
        files.append({'file': file['file'], 'raw_input': {'path': raw_path, **inputs.allowed[raw_path], 'basis': 'accepted-v3-raw/compact-identity; not-rehashed-by-this-utility'}, 'compact_input': {'path': compact_path, **actual}, 'unchanged_accepted_row_report_count': len(rows), 'rows': rows})
    originals = [{'original_subject': x['original_subject'], 'original_required_cases_retained': x['original_required_cases_retained'], 'qualification_status': x['qualification_status']} for x in joiner.ledger['subjects']]
    history = [{'historical_id': x['historical_id'], 'original_binding': x['original_binding'], 'status': x['status']} for x in joiner.ledger['historical189']]
    need(len(originals) == 280 and sum(len(x['original_required_cases_retained']) for x in originals) == 2705 and len(history) == 189, 'unchanged original280subject/2705case/189historical records')
    need(counts['recorded_selected_native_completions'] == 665 and counts['no_selected_rows'] == 108 and counts['selected_events'] == 1503, 'all665 observations and108 no-selected rows retained without inference')
    if not findings:
        need(counts['missing_selected_native_completion'] == 844, 'original missing844 selected completion rows remain missing')
    output.mkdir(parents=True, exist_ok=False)
    report = {'schema': 1, 'status': 'findings' if findings else 'passed-additive-descriptor-consistency-only; not-qualified', 'counts': dict(counts), 'findings': findings, 'public_contract38': joiner.contract, 'subjects280': originals, 'historical189': history, 'files': files, 'specification_evidence': {'path': str((HERE / 'spec/string-java-se17.json').relative_to(ROOT)), 'sha256': SPEC_SHA, 'edges': sorted(joiner.spec_edges)}, 'limits': ['Accepted v3 raw/compact and receiver facets are composed, not rerun.', 'Only 20 direct families, 7 query families and direct close rows have observed public outcome joins; all38 mappings are retained.', 'Observed hook exceptions do not imply a normal body result.', 'Missing844 selected native completions stay missing; no-selected rows receive no native credit.', 'Original280subject/2705case/189historical obligations remain pending; finite facets never qualify whole subjects.', 'Unknown/unretained nominal relations remain unresolved; two explicit String edges use official JavaSE17 specification only.', 'No Java, product, native, device, simulator, emulator, UI, capture, process inventory, execution-closure, OTA or GA validation.'], 'execution_closure_native_OTA_GA_accepted': False}
    report['selected_correction'] = {'selection': {'path': str(CORRECTION_SELECTION), 'sha256': PINS[str(CORRECTION_SELECTION)]}, 'F1': 'unresolved receiver propagates through observed hook-exception join; original exception retained and normal body pending', 'F2': 'JVMS17 4.2.1/4.2.2 class-name exclusions only; parentheses and whitespace permitted', 'F3': 'retained access/opcode receiver context included in parameter-unit budget; absent context explicitly grammar-only/unresolved', 'source_only_classfile_reader': {'sha256': '211ad86c8b0ffd9048d322efbb9e93bc3fc6606dcf745788bb36ec6052adfd2d', 'cache_loader_used': False}, 'jvms_evidence': [{'path': 'spec/jvms17-class-name-grammar-evidence.json', 'sha256': '95a0105b630a8efa200c1a203c4b6ad21f077c602efd7161ce324f703d96ee86'}, {'path': 'spec/jvms4-se17-retrieval.json', 'sha256': 'd9e35354b084880fbf5089d2d9350ff43fe5776d43ca2a5a502986736c0ee958'}], 'independent_review': 'pending'}
    write_json(output / 'descriptor-facets.json', report)
    write_json(output / 'input-manifest.json', {'schema': 1, 'validated_inputs': inputs.used, 'raw_references_from_accepted_ledger': {x['raw_input']['path']: {k: x['raw_input'][k] for k in ('bytes', 'sha256')} for x in files}, 'source_seal': identity((HERE / 'source-seal.json').read_bytes()), 'prepared_manifest': identity((HERE / 'prepared-input-manifest.json').read_bytes())})
    print(json.dumps({'status': report['status'], 'counts': dict(counts), 'findings': len(findings), 'output': str(output)}))
    return 1 if findings else 0


def prepare():
    inputs = Inputs()
    joiner = Joiner(inputs)
    write_json(HERE / 'public-contract-investigation.json', {'schema': 1, 'public_contract38': joiner.contract, 'host_classes464': len(joiner.classes), 'source_identity': inputs.used, 'uncertainties': ['unretained hierarchy except exact nominal equality and two root-approved JavaSE17 String edges'], 'qualification': False})
    write_json(HERE / 'prepared-input-manifest.json', {'schema': 1, 'validated_prepass_inputs': inputs.used, 'selected_compact_files': [{'path': x['input_path'] + '.compact.jsonl', **inputs.allowed[x['input_path'] + '.compact.jsonl']} for x in joiner.ledger['files'] if 'input_path' in x], 'single_streaming_pass_required': True})
    print(json.dumps({'prepared': True, 'public_mappings': len(joiner.contract), 'host_classes': len(joiner.classes), 'sources': len(joiner.sources), 'raw_compact_pairs': sum('input_path' in x for x in joiner.ledger['files'])}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--prepare', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.prepare:
        prepare()
    else:
        need(args.output is not None and args.output.resolve().is_relative_to(HERE), 'owned output directory required')
        sys.exit(run(args.output))
