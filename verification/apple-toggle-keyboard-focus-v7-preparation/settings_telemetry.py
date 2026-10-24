"""Closed setup-only durable diagnostic telemetry; never an input command."""
import base64
import copy
import hashlib
import math
import os
import pathlib
import struct
import time
import uuid
import zlib

CASE = 'public-settings-full-keyboard-access'
ROUTE = ['Accessibility', 'Keyboards & Typing', 'Full Keyboard Access']
CHUNK = 3072
MAX_TOTAL = 7_000_000
MAX_REQUESTS = 2500
MAX_EVENTS = 100
MAX_UPLOADS = 32
MAX_DURATION = 29.0
FIELDS = {'kind', 'case', 'generation', 'sequence', 'uptime'}
sha = lambda data: hashlib.sha256(data).hexdigest()


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def number(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def integer(value, low, high):
    return type(value) is int and low <= value <= high


def digest(value):
    return type(value) is str and len(value) == 64 and all(c in '0123456789abcdef' for c in value)


def png(data):
    require(data[:8] == b'\x89PNG\r\n\x1a\n', 'PNG signature')
    offset = 8
    types = []
    while offset < len(data):
        require(offset + 12 <= len(data), 'PNG truncated chunk')
        size = struct.unpack('>I', data[offset:offset + 4])[0]
        kind = data[offset + 4:offset + 8]
        require(size <= 2_000_000 and offset + size + 12 <= len(data), 'PNG chunk bound')
        payload = data[offset + 8:offset + 8 + size]
        require(zlib.crc32(kind + payload) & 0xffffffff == struct.unpack('>I', data[offset + 8 + size:offset + 12 + size])[0], 'PNG CRC')
        if not types:
            require(kind == b'IHDR' and size == 13, 'PNG IHDR')
            width, height = struct.unpack('>II', payload[:8])
            require(0 < width <= 4096 and 0 < height <= 4096, 'PNG dimensions')
        types.append(kind)
        offset += size + 12
        if kind == b'IEND':
            require(size == 0 and offset == len(data), 'PNG trailing bytes')
            break
    require(types and types[-1] == b'IEND' and b'IDAT' in types, 'PNG incomplete')


def snapshot(value, diagnostic_search=False):
    require(type(value) is dict and set(value) == {'bundle', 'foreground', 'appState', 'observedUptime', 'identifier', 'label', 'elementType', 'exists', 'hittable', 'enabled', 'valueKind', 'value', 'frame'}, 'Snapshot fields')
    require(value['bundle'] == 'com.apple.Preferences' and type(value['foreground']) is bool and integer(value['appState'], 0, 4), 'Settings identity/state')
    require(number(value['observedUptime']), 'Snapshot time')
    require(all(type(value[k]) is bool for k in ['exists', 'hittable', 'enabled']), 'Snapshot booleans')
    require(all(type(value[k]) is str and len(value[k].encode()) <= 256 for k in ['identifier', 'label', 'value']), 'Snapshot strings')
    require(integer(value['elementType'], 0, 200), 'Element type')
    require(value['valueKind'] in ['string', 'absent', 'unsupported'] and (value['valueKind'] == 'string' or value['value'] == ''), 'Raw value kind')
    frame = value['frame']
    require(type(frame) is dict and set(frame) == {'x', 'y', 'width', 'height'} and all(type(v) in (int, float) and math.isfinite(v) and abs(v) <= 10000 for v in frame.values()), 'Frame shape')
    require(frame['width'] >= 0 and frame['height'] >= 0, 'Frame dimensions')
    if value['exists']:
        positive = frame['width'] > 0 and frame['height'] > 0
        raw_offscreen = diagnostic_search and value['hittable'] is False and all(v == 0 for v in frame.values())
        require(positive or raw_offscreen, 'Attached Settings geometry')
    return value


def expected_switch(value, identifier=None):
    return value['bundle'] == 'com.apple.Preferences' and value['identifier'] in ['FKAEnabledSwitch', 'Full Keyboard Access'] and (identifier is None or value['identifier'] == identifier) and value['label'] == 'Full Keyboard Access' and value['elementType'] == 40 and value['appState'] == 4 and all(value[key] is True for key in ['exists', 'hittable', 'enabled', 'foreground'])


def expected_row(value, index):
    identifiers = [('Accessibility', 'ACCESSIBILITY'), ('Keyboards & Typing', 'KEYBOARDS'), ('Full Keyboard Access', 'FULL_KEYBOARD_ACCESS')]
    return value['bundle'] == 'com.apple.Preferences' and value['identifier'] in identifiers[index] and value['label'] == ROUTE[index] and value['elementType'] in [48, 75] and value['appState'] == 4 and all(value[key] is True for key in ['exists', 'hittable', 'enabled', 'foreground'])


def absent_opened_row(value):
    # The old selector may disappear after navigation; this exception supplies
    # no evidence that any other present row is the selected public row.
    return value['bundle'] == 'com.apple.Preferences' and value['foreground'] is True and value['appState'] == 4 and value['identifier'] == value['label'] == value['value'] == '' and value['elementType'] == 0 and all(value[key] is False for key in ['exists', 'hittable', 'enabled']) and value['valueKind'] == 'absent' and all(v == 0 for v in value['frame'].values())


def route_target(container, witness, index):
    target = witness['target']
    ids = ['', ROUTE[index], ['com.apple.settings.accessibility', 'KEYBOARDS', 'FULL_KEYBOARD_ACCESS'][index]]
    actionable = target['bundle'] == 'com.apple.Preferences' and target['identifier'] in ids and target['label'] == ROUTE[index] and target['elementType'] in [9, 48] and target['appState'] == 4 and all(target[k] is True for k in ['exists', 'hittable', 'enabled', 'foreground']) and target['frame']['width'] > 0 and target['frame']['height'] > 0
    if not actionable:
        return False
    fields = set(target) - {'observedUptime'}
    if witness['relation'] == 'self':
        return all(container[k] == target[k] for k in fields)
    if witness['relation'] != 'descendant':
        return False
    context = container['elementType'] == 75 and container['identifier'] in ids and (container['label'] in ['', ROUTE[index]] or (index == 2 and container['identifier'] == 'FULL_KEYBOARD_ACCESS' and container['label'] in ['Full Keyboard Access, Off', 'Full Keyboard Access, On'])) and container['appState'] == 4 and all(container[k] is True for k in ['exists', 'enabled', 'foreground'])
    c, t = container['frame'], target['frame']
    contained = c['width'] > 0 and c['height'] > 0 and c['x'] <= t['x'] and c['y'] <= t['y'] and t['x'] + t['width'] <= c['x'] + c['width'] and t['y'] + t['height'] <= c['y'] + c['height']
    return context and contained


def frame(value):
    require(type(value) is dict and set(value) == {'x', 'y', 'width', 'height'} and all(type(v) in (int, float) and math.isfinite(v) and abs(v) <= 10000 for v in value.values()) and value['width'] > 0 and value['height'] > 0, 'Switch positive frame')
    return value


def inside(point, rect):
    return rect['x'] < point['x'] < rect['x'] + rect['width'] and rect['y'] < point['y'] < rect['y'] + rect['height']


def switch_witness(parent, witness, started, finished):
    require(type(witness) is dict and set(witness) == {'relation', 'parentCount', 'leafCount', 'leafSwitchChildCount', 'leafSwitchDescendantCount', 'leaf', 'screen', 'hitPoint'}, 'Switch witness fields')
    require(witness['relation'] == 'immediate-child-switch', 'Switch public query relation')
    for key, expected in [('parentCount', 1), ('leafCount', 1), ('leafSwitchChildCount', 0), ('leafSwitchDescendantCount', 0)]:
        require(type(witness[key]) is int and witness[key] == expected, 'Switch public query count')
    leaf = snapshot(witness['leaf'])
    require(expected_switch(parent, 'FKAEnabledSwitch'), 'Exact public switch parent')
    require(leaf['bundle'] == 'com.apple.Preferences' and leaf['identifier'] == leaf['label'] == '' and leaf['elementType'] == 40 and leaf['appState'] == 4 and all(leaf[k] is True for k in ['exists', 'hittable', 'enabled', 'foreground']), 'Exact public switch leaf')
    require(parent['valueKind'] == leaf['valueKind'] == 'string' and parent['value'] == leaf['value'] and parent['value'] in ['0', '1'], 'Switch parent leaf raw value agreement')
    require(started <= parent['observedUptime'] <= leaf['observedUptime'] <= finished, 'Switch fresh public snapshot timing')
    p, l, screen = frame(parent['frame']), frame(leaf['frame']), frame(witness['screen'])
    point = witness['hitPoint']
    require(type(point) is dict and set(point) == {'x', 'y'} and all(type(v) in (int, float) and math.isfinite(v) for v in point.values()), 'Switch hit point shape')
    require(point == {'x': l['x'] + l['width'] / 2, 'y': l['y'] + l['height'] / 2}, 'Switch leaf center')
    require(max(p['x'], l['x']) < min(p['x'] + p['width'], l['x'] + l['width']) and max(p['y'], l['y']) < min(p['y'] + p['height'], l['y'] + l['height']), 'Switch parent leaf overlap')
    require(all(inside(point, rect) for rect in [p, l, screen]), 'Switch strict interior hit point')
    return witness


def same_snapshot(a, b):
    return all(a[key] == b[key] for key in set(a) - {'observedUptime'})


def same_switch_binding(parent, witness, before):
    old = before['switchWitness']
    return same_snapshot(parent, before['snapshot']) and same_snapshot(witness['leaf'], old['leaf']) and all(witness[key] == old[key] for key in set(old) - {'leaf'})


def destination(value, index):
    return value['bundle'] == 'com.apple.Preferences' and value['elementType'] == 21 and value['identifier'] == ROUTE[index] and value['label'] in ['', ROUTE[index]] and value['appState'] == 4 and all(value[k] is True for k in ['exists', 'enabled', 'foreground']) and value['frame']['x'] >= 0 and value['frame']['y'] >= 0 and value['frame']['width'] > 0 and value['frame']['height'] > 0


class Session:
    def __init__(self, persist, persist_file, deadline, now=time.monotonic, token=None):
        self.persist = persist
        self.persist_file = persist_file
        self.deadline = deadline
        self.now = now
        self.token = token or str(uuid.uuid4())
        self.start_host = None
        self.start_runner = None
        self.last_uptime = None
        self.last_host = None
        self.sequence = 0
        self.events = []
        self.pending = []
        self.uploads = {}
        self.total = 0
        self.requests = 0
        self.routes = []
        self.opened_routes = []
        self.route_attempts = {}
        self.route_searches = {}
        self.route_bindings = []
        self.route_opened_bindings = []
        self.before = None
        self.after = None
        self.terminal = None
        self.anchor = None
        self.observation_deadline = None
        self.action = None
        self.action_binding = None
        self.terminate = []
        self.completions = []
        self.enabled_samples = []
        self.invalid_enabled_samples = []
        self.last_capture_finished = None

    def request(self, value):
        # Validate on a copy. An unsuccessful persistence/ACK preparation cannot
        # advance the accepted cursor or make a partial upload appear complete.
        draft = copy.copy(self)
        for key in ['events', 'pending', 'uploads', 'routes', 'opened_routes', 'route_attempts', 'route_searches', 'route_bindings', 'route_opened_bindings', 'terminate', 'completions', 'enabled_samples', 'invalid_enabled_samples']:
            setattr(draft, key, copy.deepcopy(getattr(self, key)))
        result = draft._request(value)
        self.__dict__.update(draft.__dict__)
        return result

    def _request(self, value):
        host = self.now()
        require(number(host) and host < self.deadline, 'Session deadline')
        require(type(value) is dict and type(value.get('kind')) is str, 'Diagnostic body')
        if value['kind'] == 'start':
            require(set(value) == {'kind', 'case', 'uptime'} and value['case'] == CASE and number(value['uptime']) and self.start_host is None, 'Setup start')
            self.start_host = host
            self.last_host = host
            self.requests = 1
            self.start_runner = self.last_uptime = value['uptime']
            self.persist('settings-0000', {'receivedUptime': host, 'generation': self.token, 'sessionDeadlineUptime': self.deadline, 'diagnosticDeadlineUptime': min(self.deadline, host + MAX_DURATION), 'record': value})
            return {'generation': self.token, 'remainingSessionSeconds': min(MAX_DURATION, self.deadline - host), 'diagnosticOnly': True}
        require(self.start_host is not None and self.last_host is not None and self.last_host <= host and 0 <= host - self.start_host <= MAX_DURATION, 'Diagnostic host receipt monotonicity/duration')
        require(FIELDS <= set(value) and value['case'] == CASE and value['generation'] == self.token, 'Diagnostic binding')
        require(integer(value['sequence'], 1, MAX_REQUESTS) and value['sequence'] == self.sequence + 1, 'Diagnostic sequence')
        require(number(value['uptime']) and self.last_uptime <= value['uptime'] <= self.start_runner + MAX_DURATION, 'Diagnostic monotonic time')
        self.requests += 1
        require(self.requests <= MAX_REQUESTS, 'Diagnostic request cap')
        kind = value['kind']
        if kind == 'chunk':
            require(set(value) == FIELDS | {'slot', 'index', 'count', 'bytes', 'sha256', 'data'} and self.pending, 'Unexpected upload')
            slot = self.pending[0]
            item = self.uploads[slot]
            require(value['slot'] == slot and integer(value['index'], 0, 651) and value['index'] == len(item['parts']), 'Chunk order/slot')
            require(value['count'] == item['count'] and type(value['count']) is int and value['bytes'] == item['bytes'] and type(value['bytes']) is int and value['sha256'] == item['sha256'], 'Chunk descriptor')
            require(type(value['data']) is str and len(value['data']) <= 4096, 'Chunk encoding bound')
            data = base64.b64decode(value['data'], validate=True)
            expected = min(CHUNK, item['bytes'] - value['index'] * CHUNK)
            require(len(data) == expected and expected > 0 and base64.b64encode(data).decode() == value['data'], 'Chunk length/canonical encoding')
            item['parts'].append(data)
            if len(item['parts']) == item['count']:
                payload = b''.join(item['parts'])
                require(len(payload) == item['bytes'] and sha(payload) == item['sha256'], 'Upload payload identity')
                if item['format'] == 'png':
                    png(payload)
                else:
                    text = payload.decode('utf-8')
                    require(text and '\x00' not in text, 'AX text payload')
                self.persist_file(slot, item['format'], payload)
                item['complete'] = True
                item['parts'] = []
                self.pending.pop(0)
        elif kind == 'observe':
            route_stage = value.get('stage') in ['route-search', 'route-opened']
            extra = {'routeWitness'} if route_stage else {'switchWitness'}
            require(set(value) == FIELDS | {'stage', 'routeIndex', 'attempt', 'captureStartedUptime', 'captureFinishedUptime', 'snapshot', 'files'} | extra and not self.pending, 'Observation shape/pending upload')
            require(self.terminal is None and not self.terminate, 'Observation after terminal/termination')
            require(len(self.events) < MAX_EVENTS, 'Event cap')
            stage = value['stage']
            require(stage in ['route-search', 'route-opened', 'before-switch', 'after-switch', 'poll', 'terminal'], 'Observation stage')
            require(integer(value['routeIndex'], 0, 3) and integer(value['attempt'], 0, 5), 'Route indices')
            snap = snapshot(value['snapshot'], diagnostic_search=stage == 'route-search')
            require(all(number(value[k]) for k in ['captureStartedUptime', 'captureFinishedUptime']) and self.start_runner <= value['captureStartedUptime'] <= snap['observedUptime'] <= value['captureFinishedUptime'] <= value['uptime'], 'Capture ordering')
            require(self.last_capture_finished is None or value['captureStartedUptime'] >= self.last_capture_finished, 'Stale/reordered capture')
            self.last_capture_finished = value['captureFinishedUptime']
            files = value['files']
            require(type(files) is dict and set(files) in [{'ax'}, {'ax', 'png'}, set()], 'Observation files')
            if stage.startswith('route-'):
                require(set(files) == {'ax'} and self.before is None and value['routeIndex'] < 3, 'Route capture')
                index = value['routeIndex']
                witness = value['routeWitness']
                require(type(witness) is dict and set(witness) == ({'target', 'relation'} if stage == 'route-search' else {'destination'}), 'Route witness fields')
                nested = witness['target'] if stage == 'route-search' else witness['destination']
                snapshot(nested, diagnostic_search=stage == 'route-search')
                require(value['captureStartedUptime'] <= nested['observedUptime'] <= value['captureFinishedUptime'], 'Route witness capture time')
                require(index == len(self.routes) - (1 if stage == 'route-opened' else 0), 'Route progression')
                if stage == 'route-search':
                    require(witness['relation'] in ['self', 'descendant'], 'Fixed route relation')
                    require(self.routes == self.opened_routes, 'Prior route not observed opened')
                    require(value['attempt'] == self.route_attempts.get(index, -1) + 1, 'Route search attempts')
                    self.route_attempts[index] = value['attempt']
                    self.route_searches[index] = value
                else:
                    require(self.opened_routes == list(range(index)), 'Route opened order')
                    require(len(self.route_bindings) == index + 1, 'Route opened tap binding')
                    tap = self.route_bindings[index]
                    require(tap['routeIndex'] == index and tap['tapSequence'] < value['sequence'], 'Route opened same-route tap sequence')
                    require(tap['finishedUptime'] <= value['captureStartedUptime'], 'Route opened capture precedes same-route tap completion')
                    self.opened_routes.append(index)
                    self.route_opened_bindings.append({'routeIndex': index, 'sequence': value['sequence'], 'tapSequence': tap['tapSequence'], 'tapFinishedUptime': tap['finishedUptime'], 'captureStartedUptime': value['captureStartedUptime'], 'destinationMatched': destination(nested, index), 'oldSelectorAbsent': absent_opened_row(snap)})
            else:
                require(value['routeIndex'] == 3 and value['attempt'] == 0, 'Switch capture binding')
                switch_witness(snap, value['switchWitness'], value['captureStartedUptime'], value['captureFinishedUptime'])
                if stage in ['after-switch', 'poll'] or (stage == 'terminal' and self.action_binding is not None):
                    require(self.action_binding is not None and self.action_binding['actionSequence'] < value['sequence'] and self.action_binding['finishedUptime'] <= value['captureStartedUptime'], 'Switch capture precedes action completion')
                    require(same_snapshot({**snap, 'value': self.before['snapshot']['value']}, self.before['snapshot']) and same_snapshot({**value['switchWitness']['leaf'], 'value': self.before['switchWitness']['leaf']['value']}, self.before['switchWitness']['leaf']) and all(value['switchWitness'][key] == self.before['switchWitness'][key] for key in set(value['switchWitness']) - {'leaf'}), 'Switch observation public binding changed')
                if stage != 'poll':
                    require(set(files) == {'ax', 'png'}, 'Required screenshot/AX')
                else:
                    require(not files and self.after is not None and self.terminal is None and len([e for e in self.events if e['stage'] == 'poll']) < 40, 'Poll stage/count')
                if stage == 'before-switch':
                    require(self.before is None and self.routes == self.opened_routes == [0, 1, 2], 'Before switch progression')
                    self.before = value
                elif stage == 'after-switch':
                    require(self.anchor is not None and self.after is None, 'After switch progression')
                    self.after = value
                elif stage == 'terminal':
                    require(self.terminal is None, 'Duplicate terminal')
                    self.terminal = value
                if self.anchor is not None and self.anchor <= snap['observedUptime'] <= self.observation_deadline and snap['valueKind'] == 'string' and snap['value'] == '1':
                    initial_id = None if self.before is None else self.before['snapshot']['identifier']
                    if self.before is not None and expected_switch(self.before['snapshot']) and expected_switch(snap, initial_id):
                        self.enabled_samples.append(value['sequence'])
                    else:
                        self.invalid_enabled_samples.append(value['sequence'])
            for form in ['ax', 'png']:
                if form not in files:
                    continue
                descriptor = files[form]
                require(type(descriptor) is dict and set(descriptor) == {'bytes', 'sha256'} and integer(descriptor['bytes'], 1, 2_000_000 if form == 'png' else 200_000) and digest(descriptor['sha256']), 'File descriptor')
                self.total += descriptor['bytes']
                require(self.total <= MAX_TOTAL and len(self.uploads) < MAX_UPLOADS, 'Aggregate upload bound')
                slot = f"settings-{value['sequence']:04d}-{form}"
                self.uploads[slot] = {**descriptor, 'format': form, 'count': (descriptor['bytes'] + CHUNK - 1) // CHUNK, 'parts': [], 'complete': False}
                self.pending.append(slot)
            self.events.append(value)
        elif kind == 'mark':
            require(set(value) == FIELDS | {'stage', 'detail'} and not self.pending and len(self.events) < MAX_EVENTS, 'Marker shape')
            stage, detail = value['stage'], value['detail']
            require(type(detail) is dict, 'Marker detail')
            require(self.terminal is None or stage in ['terminate-before', 'terminate-after', 'test-case-finished', 'suite-finished', 'bundle-finished'], 'Action after terminal')
            if stage == 'settings-launched':
                require(not self.events and not detail, 'Launch marker')
            elif stage == 'route-tap':
                require(set(detail) == {'routeIndex', 'searchSequence', 'target', 'startedUptime', 'finishedUptime'} and integer(detail['routeIndex'], 0, 2) and detail['routeIndex'] == len(self.routes) and detail['routeIndex'] in self.route_attempts and self.routes == self.opened_routes and self.before is None, 'Route tap order')
                self.routes.append(detail['routeIndex'])
                search = self.route_searches[detail['routeIndex']]
                require(type(detail['searchSequence']) is int and detail['searchSequence'] == search['sequence'], 'Tap search sequence binding')
                target = snapshot(detail['target'])
                require(all(number(detail[k]) for k in ['startedUptime', 'finishedUptime']) and search['captureFinishedUptime'] <= target['observedUptime'] <= detail['startedUptime'] <= detail['finishedUptime'] <= value['uptime'], 'Tap target timing')
                same_target = all(target[k] == search['routeWitness']['target'][k] for k in set(target) - {'observedUptime'})
                self.route_bindings.append({'routeIndex': detail['routeIndex'], 'searchSequence': search['sequence'], 'tapSequence': value['sequence'], 'finishedUptime': detail['finishedUptime'], 'samePublicTargetMetadata': same_target, 'rowMatched': same_target and route_target(search['snapshot'], search['routeWitness'], detail['routeIndex'])})
            elif stage == 'switch-action':
                require(set(detail) == {'action', 'anchorUptime', 'deadlineUptime', 'beforeSequence', 'parent', 'switchWitness', 'startedUptime', 'finishedUptime'} and self.before is not None and self.anchor is None and self.after is None, 'Switch action shape/order')
                require(type(detail['beforeSequence']) is int and detail['beforeSequence'] == self.before['sequence'], 'Switch before sequence binding')
                require(all(number(detail[k]) for k in ['startedUptime', 'finishedUptime']) and self.before['captureFinishedUptime'] <= detail['startedUptime'] <= detail['finishedUptime'] <= value['uptime'], 'Switch action completion timing')
                parent = snapshot(detail['parent'])
                switch_witness(parent, detail['switchWitness'], self.before['captureFinishedUptime'], detail['startedUptime'])
                require(same_switch_binding(parent, detail['switchWitness'], self.before), 'Switch action public binding changed')
                initial = self.before['snapshot']
                require(initial['valueKind'] == 'string' and initial['value'] in ['0', '1'], 'Initial switch raw value')
                expected = 'tap' if initial['value'] == '0' else 'no-tap'
                require(detail['action'] == expected and number(detail['anchorUptime']) and number(detail['deadlineUptime']) and detail['deadlineUptime'] == detail['anchorUptime'] + 3.0, 'Anchored three second window')
                require(self.start_runner <= detail['anchorUptime'] <= value['uptime'], 'Action time')
                if expected == 'tap':
                    require(detail['anchorUptime'] == detail['finishedUptime'], 'Tap completion anchor')
                else:
                    require(detail['anchorUptime'] == initial['observedUptime'] and detail['startedUptime'] == detail['finishedUptime'], 'Initial enabled anchor/no tap')
                    if expected_switch(initial):
                        self.enabled_samples.append(self.before['sequence'])
                    else:
                        self.invalid_enabled_samples.append(self.before['sequence'])
                self.action_binding = {'beforeSequence': detail['beforeSequence'], 'actionSequence': value['sequence'], 'startedUptime': detail['startedUptime'], 'finishedUptime': detail['finishedUptime'], 'parent': parent, 'switchWitness': detail['switchWitness']}
                self.action = expected
                self.anchor = detail['anchorUptime']
                self.observation_deadline = detail['deadlineUptime']
            elif stage in ['terminate-before', 'terminate-after']:
                require(not detail and self.terminate == ([] if stage == 'terminate-before' else ['terminate-before']), 'Terminate order')
                self.terminate.append(stage)
            elif stage in ['test-case-finished', 'suite-finished', 'bundle-finished']:
                expected = ['test-case-finished', 'suite-finished', 'bundle-finished'][len(self.completions)] if len(self.completions) < 3 else None
                require(not detail and stage == expected and self.terminate == ['terminate-before', 'terminate-after'], 'Completion order')
                self.completions.append(stage)
            else:
                raise ValueError('Unsupported marker')
            self.events.append(value)
        else:
            raise ValueError('Unsupported diagnostic kind')
        self.persist(f"settings-{value['sequence']:04d}", {'receivedUptime': host, 'record': value})
        self.sequence = value['sequence']
        self.last_uptime = value['uptime']
        self.last_host = host
        return {'accepted': True, 'sequence': self.sequence, 'diagnosticOnly': True, 'pending': list(self.pending)}

    def summary(self):
        required = [self.before, self.after, self.terminal]
        complete = all(required) and not self.pending and all(v['complete'] is True for v in self.uploads.values())
        metadata = all(value and expected_switch(value['snapshot'], self.before['snapshot']['identifier']) for value in required) if self.before is not None else False
        routes = len(self.route_bindings) == len(self.route_opened_bindings) == 3 and all(row['rowMatched'] for row in self.route_bindings) and all(row['destinationMatched'] for row in self.route_opened_bindings)
        enabled = bool(self.enabled_samples) and self.terminal is not None and self.terminal['snapshot']['valueKind'] == 'string' and self.terminal['snapshot']['value'] == '1'
        return {'status': 'DIAGNOSTIC_ONLY', 'settingsReportedEnabled': enabled, 'settingsEvidenceComplete': bool(complete), 'settingsMetadataExpected': bool(metadata), 'selectedRouteEvidenceExpected': routes, 'routeTapBindings': self.route_bindings, 'routeOpenedBindings': self.route_opened_bindings, 'setupObservationSatisfied': bool(complete and metadata and routes and enabled), 'routeTaps': [row['routeIndex'] for row in self.route_bindings if row['rowMatched']], 'claimedRouteTapIndices': self.routes, 'switchAction': self.action, 'switchActionBinding': self.action_binding, 'anchorUptime': self.anchor, 'observationDeadlineUptime': self.observation_deadline, 'enabledWithinWindowSequences': self.enabled_samples, 'invalidEnabledWithinWindowSequences': self.invalid_enabled_samples, 'lastAcceptedHostReceiptUptime': self.last_host, 'sequence': self.sequence, 'requests': self.requests, 'decodedBytesDeclared': self.total, 'pendingSlots': self.pending, 'uploads': {k: {a: b for a, b in v.items() if a != 'parts'} for k, v in self.uploads.items()}, 'terminationMarkers': self.terminate, 'completionMarkers': self.completions, 'applicationCasesExecuted': 0, 'nativeKeyboardQualification': False, 'runPassed': False}


def diagnostic_bridge(base):
    class DiagnosticBridge(base):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            def persist_file(slot, form, payload):
                path = self.output / (slot + ('.png' if form == 'png' else '.txt'))
                require(path.parent == self.output and not path.exists() and not path.is_symlink(), 'Fixed fresh telemetry artifact')
                with path.open('xb') as stream:
                    stream.write(payload)
                    stream.flush()
                    os.fsync(stream.fileno())
                fd = os.open(self.output, os.O_RDONLY)
                try:
                    os.fsync(fd)
                finally:
                    os.close(fd)
            def persist(suffix, value):
                self.save(suffix, {**value, 'ownedSimulatorIdentity': self.identity})
                fd = os.open(self.output, os.O_RDONLY)
                try:
                    os.fsync(fd)
                finally:
                    os.close(fd)
            self.settings = Session(persist, persist_file, self.deadline)

        def _request(self, op, body):
            if op == 'evaluate' and type(body) is dict and set(body) == {'settingsDiagnostic'}:
                require(self.current is None and self.generation == 0, 'Settings telemetry before app begin only')
                return self.settings.request(body['settingsDiagnostic'])
            if op == 'begin':
                raise ValueError('Setup-only diagnostic cannot begin application cases')
            return super()._request(op, body)
    return DiagnosticBridge
