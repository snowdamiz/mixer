#!/usr/bin/env python3
"""V8 synthetic journal emitter through the actual Bridge/Session. No native evidence."""
import base64
import copy
import hashlib
import http.client
import importlib.util
import json
import pathlib
import shutil
import struct
import sys
import tempfile
import threading
import unittest
import zlib
from unittest import mock

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRODUCER = HERE
sys.path.insert(0, str(PRODUCER))
spec = importlib.util.spec_from_file_location('reviewed_v8_run', PRODUCER / 'run.py')
producer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(producer)
t = producer.settings_telemetry
spec = importlib.util.spec_from_file_location('reviewed_v8_replay', PRODUCER / 'replay.py')
replay = importlib.util.module_from_spec(spec)
spec.loader.exec_module(replay)
SCRATCH = HERE / '.scratch'
SCRATCH.mkdir(exist_ok=True)


def image():
    def chunk(name, data):
        return struct.pack('>I', len(data)) + name + data + struct.pack('>I', zlib.crc32(name + data) & 0xffffffff)
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 6, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(b'\x00\x00\x00\x00\xff')) + chunk(b'IEND', b'')


class Flow:
    def __init__(self):
        self.root = pathlib.Path(tempfile.mkdtemp(prefix='real-v8-', dir=SCRATCH))
        docs = self.root / 'Documents'
        docs.mkdir()
        self.bridge = producer.h.Bridge({'diagnostic': docs, 'comparator': docs}, self.root / 'captures', 'independent-review-capability', {'scope': 'synthetic-host-only'}, allowed_cases=producer.keyboard_oracle.CASES)
        self.clock = 100.0
        self.runner = 10.0
        self.bridge.settings.now = lambda: self.clock
        self.bridge.settings.deadline = 500.0
        self.send({'kind': 'start', 'case': t.CASE, 'uptime': self.runner})
        self.searches = {}
        self.taps = {}

    def close(self):
        pass  # Retain every synthetic attempt for the sealed evidence archive.

    def send(self, record):
        return self.bridge.request('evaluate', {'settingsDiagnostic': record})

    def record(self, kind, **fields):
        self.runner += .01
        self.clock += .001
        return {'kind': kind, 'case': t.CASE, 'generation': self.bridge.settings.token, 'sequence': self.bridge.settings.sequence + 1, 'uptime': self.runner, **fields}

    def mark(self, stage, detail=None):
        r = self.record('mark', stage=stage, detail={} if detail is None else detail)
        self.send(r)
        return r

    def snap(self, **fields):
        return {'bundle': 'com.apple.Preferences', 'foreground': True, 'appState': 4, 'observedUptime': self.runner + .001, 'identifier': 'FKAEnabledSwitch', 'label': 'Full Keyboard Access', 'elementType': 40, 'exists': True, 'hittable': True, 'enabled': True, 'valueKind': 'string', 'value': '0', 'frame': {'x': 10, 'y': 100, 'width': 300, 'height': 50}, **fields}

    def observe(self, stage, index=3, attempt=0, value='0', alter=None, upload=True):
        self.runner += .01
        started = self.runner
        raw = self.snap(value=value)
        if not stage.startswith('route-'):raw['frame']=dict(x=36,y=146.3333282470703,width=330,height=28)
        witness = None
        if stage == 'route-search':
            raw.update(identifier='', label='', elementType=75, valueKind='unsupported', value='')
            target = self.snap(identifier='', label=t.ROUTE[index], elementType=48, valueKind='unsupported', value='', frame=dict(x=20, y=110, width=200, height=20))
            witness = {'relation': 'descendant', 'target': target}
        elif stage == 'route-opened':
            raw.update(identifier='', label='', elementType=75, hittable=False, valueKind='unsupported', value='', frame=dict(x=-105, y=100, width=300, height=50))
            witness = {'destination': self.snap(identifier=t.ROUTE[index], label='', elementType=21, valueKind='unsupported', value='', frame=dict(x=0, y=10, width=320, height=44))}
        payloads = {} if stage == 'poll' else {'ax': b'Independent synthetic AX text; not a native hierarchy\n'}
        if stage in ['before-switch', 'after-switch', 'terminal']:
            payloads['png'] = image()
        files = {form: {'bytes': len(data), 'sha256': t.sha(data)} for form, data in payloads.items()}
        r = self.record('observe', stage=stage, routeIndex=index, attempt=attempt, captureStartedUptime=started, captureFinishedUptime=started+.002, snapshot=raw, files=files)
        if witness is not None:
            r['routeWitness'] = witness
        else:
            r['switchWitness'] = self.switch_witness(raw)
        if alter:
            alter(r)
        if upload:
            self.send(r)
            self.upload(payloads)
        if stage == 'route-search':
            self.searches[index] = r
        return r, payloads

    def upload(self, payloads):
        for slot in list(self.bridge.settings.pending):
            form = slot.rsplit('-', 1)[1]
            data = payloads[form]
            item = self.bridge.settings.uploads[slot]
            for index in range(item['count']):
                r = self.record('chunk', slot=slot, index=index, count=item['count'], bytes=len(data), sha256=t.sha(data), data=base64.b64encode(data[index*t.CHUNK:(index+1)*t.CHUNK]).decode())
                self.send(r)

    def tap(self, index, alter=None):
        target = copy.deepcopy(self.searches[index]['routeWitness']['target'])
        target['observedUptime'] = self.runner+.001
        r = self.record('mark', stage='route-tap', detail={'routeIndex': index, 'searchSequence': self.searches[index]['sequence'], 'target': target, 'startedUptime': self.runner+.002, 'finishedUptime': self.runner+.003})
        # Python evaluates keyword arguments before record advances the clock.
        if alter:
            alter(r)
        self.send(r)
        self.taps[index] = r
        return r

    def routes(self, search_alter=None, tap_alter=None, opened_alter=None):
        self.mark('settings-launched')
        for index in range(3):
            self.observe('route-search', index=index, alter=(lambda r: search_alter(r)) if search_alter else None)
            self.tap(index, (lambda r: tap_alter(r)) if tap_alter else None)
            self.observe('route-opened', index=index, alter=(lambda r: opened_alter(r)) if opened_alter else None)

    def before(self, initial='0', **options):
        self.routes(**options)
        self.observe('before-switch', value=initial)

    def switch_witness(self, parent):
        leaf=copy.deepcopy(parent)
        leaf.update(identifier='',label='',observedUptime=parent['observedUptime']+.0001,frame=dict(x=305,y=146.3333282470703,width=63,height=28))
        return dict(relation='immediate-child-switch',parentCount=1,leafCount=1,leafSwitchChildCount=0,leafSwitchDescendantCount=0,leaf=leaf,screen=dict(x=0,y=0,width=402,height=874),hitPoint=dict(x=336.5,y=160.3333282470703))

    def action_record(self, initial='0'):
        parent=copy.deepcopy(self.bridge.settings.before['snapshot']);parent['observedUptime']=self.runner+.001
        witness=self.switch_witness(parent)
        started=self.runner+.002;finished=started+.001 if initial=='0' else started
        anchor=finished if initial=='0' else self.bridge.settings.before['snapshot']['observedUptime']
        return self.record('mark',stage='switch-action',detail=dict(action='tap' if initial=='0' else 'no-tap',anchorUptime=anchor,deadlineUptime=anchor+3.0,beforeSequence=self.bridge.settings.before['sequence'],parent=parent,switchWitness=witness,startedUptime=started,finishedUptime=finished))

    def action(self, initial='0'):
        r=self.action_record(initial);self.send(r);return r

    def completion(self):
        for stage in ['terminate-before', 'terminate-after', 'test-case-finished', 'suite-finished', 'bundle-finished']:
            self.mark(stage)

    def finish(self, initial='0', **options):
        self.before(initial, **options)
        self.action(initial)
        self.observe('after-switch', value='1')
        self.observe('terminal', value='1')
        self.completion()

    def witness(self, name, detail):
        out = HERE / 'witnesses' / name
        out.mkdir(parents=True, exist_ok=True)
        shutil.copytree(self.bridge.output, out/'captures', dirs_exist_ok=True)
        (out/'witness.json').write_text(json.dumps({'syntheticHostOnly': True, 'nativeExecuted': False, 'detail': detail, 'settingsDiagnostic': self.bridge.settings.summary(), 'replayed': replay.replay(self.bridge.output)}, indent=2, sort_keys=True)+'\n')

