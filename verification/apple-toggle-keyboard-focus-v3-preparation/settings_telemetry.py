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


def snapshot(value):
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
        require(frame['width'] > 0 and frame['height'] > 0, 'Attached Settings geometry')
    return value


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
        self.sequence = 0
        self.events = []
        self.pending = []
        self.uploads = {}
        self.total = 0
        self.requests = 0
        self.routes = []
        self.opened_routes = []
        self.route_attempts = {}
        self.before = None
        self.after = None
        self.terminal = None
        self.anchor = None
        self.observation_deadline = None
        self.action = None
        self.terminate = []
        self.completions = []
        self.enabled_samples = []
        self.last_capture_finished = None

    def request(self, value):
        # Validate on a copy. An unsuccessful persistence/ACK preparation cannot
        # advance the accepted cursor or make a partial upload appear complete.
        draft = copy.copy(self)
        for key in ['events', 'pending', 'uploads', 'routes', 'opened_routes', 'route_attempts', 'terminate', 'completions', 'enabled_samples']:
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
            self.requests = 1
            self.start_runner = self.last_uptime = value['uptime']
            self.persist('settings-0000', {'receivedUptime': host, 'generation': self.token, 'sessionDeadlineUptime': self.deadline, 'diagnosticDeadlineUptime': min(self.deadline, host + MAX_DURATION), 'record': value})
            return {'generation': self.token, 'remainingSessionSeconds': min(MAX_DURATION, self.deadline - host), 'diagnosticOnly': True}
        require(self.start_host is not None and host - self.start_host <= MAX_DURATION, 'Diagnostic host duration')
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
            require(set(value) == FIELDS | {'stage', 'routeIndex', 'attempt', 'captureStartedUptime', 'captureFinishedUptime', 'snapshot', 'files'} and not self.pending, 'Observation shape/pending upload')
            require(self.terminal is None and not self.terminate, 'Observation after terminal/termination')
            require(len(self.events) < MAX_EVENTS, 'Event cap')
            stage = value['stage']
            require(stage in ['route-search', 'route-opened', 'before-switch', 'after-switch', 'poll', 'terminal'], 'Observation stage')
            require(integer(value['routeIndex'], 0, 3) and integer(value['attempt'], 0, 5), 'Route indices')
            snap = snapshot(value['snapshot'])
            require(all(number(value[k]) for k in ['captureStartedUptime', 'captureFinishedUptime']) and self.start_runner <= value['captureStartedUptime'] <= snap['observedUptime'] <= value['captureFinishedUptime'] <= value['uptime'], 'Capture ordering')
            require(self.last_capture_finished is None or value['captureStartedUptime'] >= self.last_capture_finished, 'Stale/reordered capture')
            self.last_capture_finished = value['captureFinishedUptime']
            files = value['files']
            require(type(files) is dict and set(files) in [{'ax'}, {'ax', 'png'}, set()], 'Observation files')
            if stage.startswith('route-'):
                require(set(files) == {'ax'} and self.before is None and value['routeIndex'] < 3, 'Route capture')
                index = value['routeIndex']
                require(index == len(self.routes) - (1 if stage == 'route-opened' else 0), 'Route progression')
                if stage == 'route-search':
                    require(self.routes == self.opened_routes, 'Prior route not observed opened')
                    require(value['attempt'] == self.route_attempts.get(index, -1) + 1, 'Route search attempts')
                    self.route_attempts[index] = value['attempt']
                else:
                    require(self.opened_routes == list(range(index)), 'Route opened order')
                    self.opened_routes.append(index)
            else:
                require(value['routeIndex'] == 3 and value['attempt'] == 0, 'Switch capture binding')
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
                    self.enabled_samples.append(value['sequence'])
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
                require(set(detail) == {'routeIndex'} and integer(detail['routeIndex'], 0, 2) and detail['routeIndex'] == len(self.routes) and detail['routeIndex'] in self.route_attempts and self.routes == self.opened_routes and self.before is None, 'Route tap order')
                self.routes.append(detail['routeIndex'])
            elif stage == 'switch-action':
                require(set(detail) == {'action', 'anchorUptime', 'deadlineUptime'} and self.before is not None and self.anchor is None, 'Switch action shape/order')
                initial = self.before['snapshot']
                require(initial['valueKind'] == 'string' and initial['value'] in ['0', '1'], 'Initial switch raw value')
                expected = 'tap' if initial['value'] == '0' else 'no-tap'
                require(detail['action'] == expected and number(detail['anchorUptime']) and number(detail['deadlineUptime']) and detail['deadlineUptime'] == detail['anchorUptime'] + 3.0, 'Anchored three second window')
                require(self.start_runner <= detail['anchorUptime'] <= value['uptime'], 'Action time')
                if expected == 'tap':
                    require(detail['anchorUptime'] >= self.before['captureFinishedUptime'], 'Tap after before capture')
                else:
                    require(detail['anchorUptime'] == initial['observedUptime'], 'Initial enabled anchor')
                    self.enabled_samples.append(self.before['sequence'])
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
        return {'accepted': True, 'sequence': self.sequence, 'diagnosticOnly': True, 'pending': list(self.pending)}

    def summary(self):
        required = [self.before, self.after, self.terminal]
        complete = all(required) and not self.pending and all(v['complete'] is True for v in self.uploads.values())
        metadata = all(snapshot and snapshot['snapshot']['identifier'] in ['FKAEnabledSwitch', 'Full Keyboard Access'] and snapshot['snapshot']['label'] == 'Full Keyboard Access' and snapshot['snapshot']['elementType'] == 40 and snapshot['snapshot']['appState'] == 4 and snapshot['snapshot']['exists'] is True and snapshot['snapshot']['hittable'] is True and snapshot['snapshot']['enabled'] is True and snapshot['snapshot']['foreground'] is True for snapshot in required)
        metadata = metadata and len({v['snapshot']['identifier'] for v in required if v is not None}) == 1
        enabled = bool(self.enabled_samples) and self.terminal is not None and self.terminal['snapshot']['valueKind'] == 'string' and self.terminal['snapshot']['value'] == '1'
        return {'status': 'DIAGNOSTIC_ONLY', 'settingsReportedEnabled': enabled, 'settingsEvidenceComplete': bool(complete), 'settingsMetadataExpected': bool(metadata), 'setupObservationSatisfied': bool(complete and metadata and enabled), 'routeTaps': self.routes, 'switchAction': self.action, 'anchorUptime': self.anchor, 'observationDeadlineUptime': self.observation_deadline, 'enabledWithinWindowSequences': self.enabled_samples, 'sequence': self.sequence, 'requests': self.requests, 'decodedBytesDeclared': self.total, 'pendingSlots': self.pending, 'uploads': {k: {a: b for a, b in v.items() if a != 'parts'} for k, v in self.uploads.items()}, 'terminationMarkers': self.terminate, 'completionMarkers': self.completions, 'applicationCasesExecuted': 0, 'nativeKeyboardQualification': False, 'runPassed': False}


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
