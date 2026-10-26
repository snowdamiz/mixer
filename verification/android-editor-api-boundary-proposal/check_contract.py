#!/usr/bin/env python3
"""Offline specification/bytecode controls. Never an Android or OTA authority."""
from pathlib import Path
import copy
import hashlib
import json
import re
import struct
import sys
import xml.etree.ElementTree as ET
import zipfile

HERE = Path(__file__).resolve().parent
COUNTS = {'checks': 0, 'negative_contract_controls': 0, 'state_model_cases': 0}


def check(value, message):
    COUNTS['checks'] += 1
    if not value:
        raise AssertionError(message)


def classfile(data):
    """Read real constant-pool/method metadata, not Java source tokens."""
    offset = 0

    def number(fmt):
        nonlocal offset
        value = struct.unpack_from(fmt, data, offset)[0]
        offset += struct.calcsize(fmt)
        return value

    check(number('>I') == 0xCAFEBABE, 'class magic')
    number('>H')
    major = number('>H')
    count = number('>H')
    pool = [None] * count
    index = 1
    while index < count:
        tag = number('>B')
        if tag == 1:
            size = number('>H')
            pool[index] = (tag, data[offset:offset + size].decode('utf-8'))
            offset += size
        elif tag in {3, 4}:
            pool[index] = (tag, number('>I'))
        elif tag in {5, 6}:
            pool[index] = (tag, number('>Q'))
            index += 1
        elif tag in {7, 8, 16, 19, 20}:
            pool[index] = (tag, number('>H'))
        elif tag in {9, 10, 11, 12, 17, 18}:
            pool[index] = (tag, number('>H'), number('>H'))
        elif tag == 15:
            pool[index] = (tag, number('>B'), number('>H'))
        else:
            raise AssertionError(('unknown pool tag', tag))
        index += 1

    def utf(index):
        return pool[index][1]

    def classname(index):
        return utf(pool[index][1])

    number('>H')
    own = classname(number('>H'))
    parent = classname(number('>H'))
    interfaces = [classname(number('>H')) for _ in range(number('>H'))]

    def attributes():
        nonlocal offset
        for _ in range(number('>H')):
            number('>H')
            size = number('>I')
            offset += size

    def members():
        result = []
        for _ in range(number('>H')):
            access = number('>H')
            name, descriptor = utf(number('>H')), utf(number('>H'))
            result.append({'access': access, 'name': name, 'descriptor': descriptor})
            attributes()
        return result

    fields, methods = members(), members()
    references = []
    types = set()
    for item in pool[1:]:
        if not item:
            continue
        if item[0] == 7:
            types.add(utf(item[1]))
        elif item[0] == 1:
            # Descriptors/signatures are classfile metadata, including generic
            # Signature attributes; no source-level matching authorizes support.
            types.update(re.findall(r'L(android/[A-Za-z0-9_$/]+)', item[1]))
        elif item[0] in {9, 10, 11}:
            nat = pool[item[2]]
            references.append({'tag': item[0], 'owner': classname(item[1]),
                               'name': utf(nat[1]), 'descriptor': utf(nat[2])})
    return {'class': own, 'super': parent, 'interfaces': interfaces, 'major': major,
            'fields': fields, 'methods': methods, 'class_references': sorted(types),
            'member_references': references}


def platform():
    roots = [ET.parse(HERE / f'official/sdk/platforms/android-{api}/data/api-versions.xml').getroot()
             for api in ['36', '37.0']]
    def roster(root):
        node = next(c for c in root.findall('class') if c.attrib['name'] == 'android/view/inputmethod/InputConnection')
        return {m.attrib['name']: int(m.attrib.get('since', node.attrib.get('since', 1)))
                for m in node.findall('method')}
    first, current = map(roster, roots)
    check(first == current, 'SDK36 and current SDK37 public InputConnection method roster differs')
    classes = {c.attrib['name']: float(c.attrib.get('since', '1')) for c in roots[1].findall('class')}
    return current, classes


def validate(contract, official):
    check(all(contract['guards'].values()), 'both SDK36 admission guards must remain')
    check(not contract['rendering_contexts_added'] and not contract['public_v2_selected']
          and not contract['source_profile_selected'], 'proposal cannot select rendering/public/profile')
    check(contract['platform_implementation_superclass'] == 'java/lang/Object', 'owned direct proxy')
    check(not contract['platform_wrapper_setTarget_exposed'], 'immutable delegate')
    routes = {m['descriptor']: m for m in contract['methods']}
    check(len(routes) == len(contract['methods']) == 38, 'exact unique 38-method roster')
    check(set(routes) == set(official), 'all current platform methods need explicit policy')
    for descriptor, floor in official.items():
        method = routes[descriptor]
        check(method['declared_class_floor'] == (28 if floor <= 28 else floor), descriptor)
        check(method['main_check_first'], descriptor + ' must check main first')
    for name in ['commitContent(', 'commitCorrection(', 'performPrivateCommand(', 'previewHandwritingGesture(', 'replaceText(']:
        check(all(m['route'] == 'existing_refusal' for d, m in routes.items() if d.startswith(name)), 'existing refusal ' + name)
    check(contract['auxiliary_async_policy_requires_explicit_selection'], 'new async refusal requires root choice')
    check(contract['native_close_policy_requires_explicit_root_amendment']
          and contract['implementation_selection_blocked_by_native_close_safety']
          and not contract['incarnation_only_patch_is_usable_editor_component'], 'cleanup safety blocks component selection')
    check(not contract['preflight']['accessibility_label_substitution'], 'native value is not a label')
    expected = lambda sdk: 'Api34' if sdk >= 34 else 'Api33' if sdk >= 33 else 'Api31' if sdk >= 31 else 'Connection28'
    check([m['sdk'] for m in contract['matrix']] == list(range(28, 38)), 'all SDK28..37 rows')
    for row in contract['matrix']:
        sdk = row['sdk']
        check(row['connection_class'] == expected(sdk), 'factory branch')
        check(not row['private_v2_admitted_by_this_proposal'], 'shape is not admission')
        check(row['api28_field_and_selectable_refusal_required'] == (sdk == 28), 'API28 authored appearance')
        check(row['required_value_refusal_required'] == (sdk < 30), 'pre30 value semantics')


class State:
    def __init__(self):
        self.main = self.owner = self.input = self.focus = self.attached = True
        self.terminal = self.changing = self.closed = False
        self.record = self.active_record = object()
        self.session = self.active_session = object()
        self.editable = object()
        self.presentation = object()
        self.selection = (1, 1)
        self.composition = (-1, -1)
        self.text = 'abc'
        self.native_calls = 0

    def admitted(self):
        if not self.main:
            raise RuntimeError('main first')
        return self.owner and self.input and self.focus and self.attached and not (
            self.terminal or self.changing or self.closed) and self.record is self.active_record and self.session is self.active_session

    def snapshot(self):
        return self.editable, self.selection, self.composition, self.text

    def valid_native_result(self):
        return all(pair == (-1, -1) or all(0 <= value <= len(self.text) for value in pair)
                   for pair in [self.selection, self.composition])


def dispatch(state, *, query=False, before_delegate=None, delegate=None, result=True):
    if not state.admitted():
        return False
    entry = (state.record, state.session, state.editable, state.presentation, state.snapshot())
    if before_delegate:
        before_delegate(state)
    if not state.admitted() or state.snapshot() != entry[4]:
        return False
    state.native_calls += 1
    if delegate:
        delegate(state)
    # Model only: a real implementation must retain its captured Mutation and
    # use the existing accepted-successor boolean rule, not replace this tuple
    # with a fresh production scope. This model never creates Mixer objects.
    if not state.admitted() or state.record is not entry[0] or state.session is not entry[1] or state.editable is not entry[2]:
        return False
    if not state.valid_native_result() or (query and state.snapshot() != entry[4]):
        return False
    if state.presentation is not entry[3]:
        return bool(result) and not query
    return result


def state_controls():
    # Bind defaults to avoid accidentally testing only the final loop condition.
    mutations = [lambda s, k=k, v=v: setattr(s, k, v) for k, v in [
        ('owner', False), ('input', False), ('focus', False), ('attached', False),
        ('terminal', True), ('changing', True), ('closed', True),
        ('active_record', object()), ('active_session', object())]]
    for alter in mutations:
        s = State(); alter(s)
        check(dispatch(s) is False and s.native_calls == 0, 'stale entry cannot delegate')
        COUNTS['state_model_cases'] += 1

    for stage in ['before', 'after']:
        for alter in mutations + [lambda s: setattr(s, 'editable', object()),
                                  lambda s: setattr(s, 'selection', (0, 0)),
                                  lambda s: setattr(s, 'composition', (0, 2))]:
            s = State()
            value = dispatch(s, query=True, **({'before_delegate': alter} if stage == 'before' else {'delegate': alter}))
            check(value is False and s.native_calls == (0 if stage == 'before' else 1), 'snapshot/fence reentry ' + stage)
            COUNTS['state_model_cases'] += 1
    s = State()
    try:
        s.main = False; s.terminal = True; dispatch(s)
        raise AssertionError('off-main hidden by stale state')
    except RuntimeError as failure:
        check(str(failure) == 'main first', 'off-main precedes all state checks')
    COUNTS['state_model_cases'] += 1
    for value in [True, False]:
        s = State()
        check(dispatch(s, delegate=lambda x: setattr(x, 'presentation', object()), result=value) is value
              and s.native_calls == 1, 'retained successor is result-only and cannot replay')
        COUNTS['state_model_cases'] += 1
    s = State()
    def own_native_edit(x):
        x.text = 'abcd'; x.selection = (4, 4); x.composition = (1, 4)
    check(dispatch(s, delegate=own_native_edit) is True, 'legitimate native selection/composition changes are not stale by equality')
    COUNTS['state_model_cases'] += 1
    s = State()
    check(dispatch(s, delegate=lambda x: setattr(x, 'composition', (0, 999))) is False, 'malformed returned composition')
    COUNTS['state_model_cases'] += 1
    class Fatal(BaseException):
        pass
    for failure in [RuntimeError('delegate original'), Fatal('fatal original')]:
        s = State()
        def fail(x):
            raise failure
        try:
            dispatch(s, delegate=fail)
            raise AssertionError('failure became ordinary rejection')
        except (RuntimeError, Fatal) as seen:
            check(seen is failure and s.native_calls == 1, 'original failure identity')
        COUNTS['state_model_cases'] += 1


def attempt_controls():
    """Finite attempt-incarnation specification; no Android creation occurs."""
    class Fatal(BaseException):
        pass

    class Attempt:
        closed = False

    class Field:
        current = None
        def create(self, native):
            attempt = Attempt()
            self.current = attempt  # claim/revoke before any external call
            try:
                target = native()
            except BaseException:
                attempt.closed = True
                if self.current is attempt:
                    self.current = None
                raise
            if target is None or self.current is not attempt:
                attempt.closed = True
                if self.current is attempt:
                    self.current = None
                return None
            return attempt
        def close(self, attempt, external):
            if attempt.closed:
                return
            attempt.closed = True
            if self.current is not attempt:
                return
            self.current = None
            external()
        def revoke(self):
            if self.current is not None:
                self.current.closed = True
            self.current = None

    f = Field(); original = f.create(lambda: object())
    check(f.current is original and not original.closed, 'ordinary native create')
    COUNTS['state_model_cases'] += 1
    for outcome in ['success', 'null', 'ordinary', 'fatal']:
        f = Field(); nested = []
        def native_outer():
            def native_inner():
                if outcome == 'ordinary':
                    raise RuntimeError('inner')
                if outcome == 'fatal':
                    raise Fatal('inner')
                return None if outcome == 'null' else object()
            try:
                nested.append(f.create(native_inner))
            except (RuntimeError, Fatal):
                nested.append(None)  # mock native body catches; outer still must not resurrect
            return object()
        outer = f.create(native_outer)
        check(outer is None and f.current is nested[0], 'nested attempt ordering ' + outcome)
        COUNTS['state_model_cases'] += 1
    for failure in [RuntimeError('outer'), Fatal('outer')]:
        f = Field()
        def native_throw():
            raise failure
        try:
            f.create(native_throw)
            raise AssertionError('create failure swallowed')
        except (RuntimeError, Fatal) as seen:
            check(seen is failure and f.current is None, 'outer create throw revokes exact attempt')
        COUNTS['state_model_cases'] += 1
    f = Field(); old = f.create(lambda: object())
    check(f.create(lambda: None) is None and f.current is None, 'null create cannot restore previous connection')
    COUNTS['state_model_cases'] += 1
    f = Field(); old = f.create(lambda: object()); f.revoke(); newer = f.create(lambda: object())
    f.close(old, lambda: (_ for _ in ()).throw(AssertionError('stale close reached native')))
    check(f.current is newer and old.closed, 'focus-loss/refocus old close cannot revoke newer')
    COUNTS['state_model_cases'] += 1
    f = Field(); old = f.create(lambda: object()); nested = []
    f.close(old, lambda: nested.append(f.create(lambda: object())))
    check(old.closed and f.current is nested[0], 'close consumes before nested create')
    COUNTS['state_model_cases'] += 1
    f.close(old, lambda: (_ for _ in ()).throw(AssertionError('repeated close reached native')))
    check(f.current is nested[0], 'repeated close leaves successor')
    COUNTS['state_model_cases'] += 1
    f = Field(); old = f.create(lambda: object())
    binding_revision = object(); binding_revision = object()  # ordinary validated echo is not a revoke
    check(f.current is old and not old.closed and binding_revision is not None, 'validated bind keeps incarnation')
    COUNTS['state_model_cases'] += 1


def main():
    official, classes = platform()
    root = ET.parse(HERE / 'official/sdk/platforms/android-37.0/data/api-versions.xml').getroot()
    api_classes = {c.attrib['name']: c for c in root.findall('class')}
    contract = json.loads((HERE / 'contract.json').read_text())
    validate(contract, official)
    controls = [lambda c: c['guards'].update(observer_sdk_below_36_refuses=False),
                lambda c: c['methods'].pop(),
                lambda c: c.update(platform_implementation_superclass='android/view/inputmethod/InputConnectionWrapper'),
                lambda c: c.update(public_v2_selected=True),
                lambda c: c.update(auxiliary_async_policy_requires_explicit_selection=False),
                lambda c: c['preflight'].update(accessibility_label_substitution=True),
                lambda c: c['matrix'][0].update(connection_class='Api34'),
                lambda c: next(m for m in c['methods'] if m['descriptor'].startswith('replaceText(')).update(route='mutate'),
                lambda c: c.update(incarnation_only_patch_is_usable_editor_component=True)]
    for mutate in controls:
        candidate = copy.deepcopy(contract); mutate(candidate)
        try:
            validate(candidate, official)
            raise RuntimeError('negative control was accepted')
        except AssertionError:
            COUNTS['negative_contract_controls'] += 1
    artifacts = []
    with zipfile.ZipFile(HERE / 'cross-compile/signature-shape.jar') as archive:
        for name in archive.namelist():
            record = classfile(archive.read(name))
            floor = 36 if '$Api36' in name else 35 if '$Api35' in name else 34 if '$Api34' in name else 33 if '$Api33' in name else 31 if '$Api31' in name else 28
            check(record['major'] == 61, 'Java17 class version')
            check(record['super'] != 'android/view/inputmethod/InputConnectionWrapper', 'no platform forwarding superclass')
            for reference in record['class_references']:
                if reference.startswith('android/'):
                    check(classes[reference] <= floor, (record['class'], reference, classes[reference], floor))
            for reference in record['member_references']:
                if reference['owner'] == 'android/view/inputmethod/InputConnection':
                    check(official[reference['name'] + reference['descriptor']] <= floor, reference)
                elif reference['owner'].startswith('android/'):
                    node = api_classes[reference['owner']]
                    name = reference['name'] if reference['tag'] == 9 else reference['name'] + reference['descriptor']
                    tag = 'field' if reference['tag'] == 9 else 'method'
                    member = next((m for m in node.findall(tag) if m.attrib['name'] == name), None)
                    check(member is not None, ('unresolved Android reference', reference))
                    check(float(member.attrib.get('since', node.attrib.get('since', '1'))) <= floor,
                          ('member above declared floor', reference, floor))
            own_methods = {m['name'] + m['descriptor'] for m in record['methods'] if m['name'] != '<init>' and not m['name'].startswith('lambda$')}
            if 'SignatureShape$' in record['class']:
                expected = {m['descriptor'] for m in contract['methods'] if m['declared_class_floor'] == floor}
                check(own_methods == expected, 'emitted exact per-class declaration roster')
            artifacts.append(record | {'declared_api_floor': floor})
    (HERE / 'bytecode-inventory.json').write_text(json.dumps(artifacts, indent=2) + '\n')
    # Named source history is documentary evidence only, never an ART check.
    defaults = []
    for api in range(28, 37):
        path = HERE / f'official/aosp/{api}/InputConnection.java'
        source = path.read_text()
        declarations = [{'line': source.count('\n', 0, match.start()) + 1, 'declaration': match.group(0)}
                        for match in re.finditer(r'(?m)^    default [^{]+\{', source)]
        count = 0 if api < 31 else 3 if api < 33 else 8 if api == 33 else 12
        check(len(declarations) == count, ('official default roster', api, len(declarations), count))
        wrapper = (HERE / f'official/aosp/{api}/InputConnectionWrapper.java').read_text()
        has_snapshot_override = bool(re.search(r'public TextSnapshot takeSnapshot\(', wrapper))
        check(has_snapshot_override == (api >= 34), 'wrapper snapshot history')
        defaults.append({'api': api, 'defaults': declarations, 'wrapper_declares_takeSnapshot': has_snapshot_override})
    (HERE / 'official-defaults.json').write_text(json.dumps(defaults, indent=2) + '\n')
    state_controls()
    attempt_controls()
    receipt = {'schema': 1, 'python': sys.version, **COUNTS,
               'official_methods': len(official), 'signature_classes': len(artifacts),
               'statement': 'Contract/model/compiled-symbol controls only. No product implementation or Android runtime proof.',
               'source_revision_is_context_only': True,
               'no_OTA_or_rendering_or_public_or_native_authorization': True}
    (HERE / 'controls.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
