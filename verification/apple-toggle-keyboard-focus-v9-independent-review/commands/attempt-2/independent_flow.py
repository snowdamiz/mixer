#!/usr/bin/env python3
"""Independent synthetic inputs sent through sealed V9 Bridge/Session/replay.

This is not native, XCUI, screenshot, or keyboard qualification evidence.
The producer fixtures and verifier are not used to authorize any assertion.
"""
import base64
import copy
import hashlib
import http.client
import importlib.util
import json
import math
import os
import pathlib
import struct
import sys
import threading
import unittest
import zlib
from unittest import mock

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRODUCER = ROOT / 'verification/apple-toggle-keyboard-focus-v9-preparation'
sys.path.insert(0, str(PRODUCER))
spec = importlib.util.spec_from_file_location('independently_reviewed_v9', PRODUCER / 'run.py')
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)
t = p.settings_telemetry
spec = importlib.util.spec_from_file_location('independently_reviewed_v9_replay', PRODUCER / 'replay.py')
replay = importlib.util.module_from_spec(spec)
spec.loader.exec_module(replay)


def image():
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff)
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 2, 1, 8, 6, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(b'\x00' + b'\xff\x00\x00\xff' * 2)) + chunk(b'IEND', b'')


class Flow:
    count = 0
    def __init__(self, name='case'):
        Flow.count += 1
        self.root = HERE / 'host-scratch' / os.environ.get('MIXER_REVIEW_ATTEMPT', 'attempt-1') / (f'{Flow.count:04d}-' + name)
        self.root.mkdir(parents=True, exist_ok=False)
        docs = self.root / 'Documents'
        docs.mkdir()
        self.bridge = p.h.Bridge({'diagnostic': docs, 'comparator': docs}, self.root / 'captures', 'independent-synthetic-capability', {'scope': 'synthetic-host-only'}, allowed_cases=p.keyboard_oracle.CASES)
        self.http_requests = []
        self.host = 200.0
        self.now = 20.0
        self.bridge.settings.now = lambda: self.host
        self.bridge.settings.deadline = 500.0
        self.send(dict(kind='start', case=t.CASE, uptime=self.now))

    def send(self, record):
        # Match the public JSON boundary's ownership of decoded request objects.
        status, body = self.http(record)
        if status != 200:
            raise RuntimeError('Synthetic setup HTTP failed: ' + str((status, body)))
        return body

    def record(self, kind, **fields):
        self.now += .02
        self.host += .001
        return dict(kind=kind, case=t.CASE, generation=self.bridge.settings.token, sequence=self.bridge.settings.sequence + 1, uptime=self.now, **fields)

    def snap(self, *, kind='parent', value='0', observed=None):
        return dict(bundle='com.apple.Preferences', foreground=True, appState=4, observedUptime=self.now+.001 if observed is None else observed,
                    identifier='FKAEnabledSwitch' if kind == 'parent' else '', label='Full Keyboard Access' if kind == 'parent' else '', elementType=40,
                    exists=True, hittable=True, enabled=True, valueKind='string', value=value,
                    frame=dict(x=36, y=146.3333282470703, width=330, height=28) if kind == 'parent' else dict(x=305, y=146.3333282470703, width=63, height=28))

    def witness(self, parent):
        return dict(relation='immediate-child-switch', parentCount=1, leafCount=1, leafSwitchChildCount=0, leafSwitchDescendantCount=0,
                    leaf=self.snap(kind='leaf', value=parent['value'], observed=parent['observedUptime']+.0001), screen=dict(x=0, y=0, width=402, height=874), hitPoint=dict(x=336.5, y=160.3333282470703))

    def mark(self, stage, detail=None):
        r = self.record('mark', stage=stage, detail=detail or {})
        self.send(r)
        return r

    def observation(self, stage, value='0', index=3):
        self.now += .02
        start = self.now
        snap = self.snap(value=value)
        payloads = {} if stage == 'poll' else {'ax': b'Independent synthetic host AX; no native hierarchy\n'}
        if not stage.startswith('route-') and stage != 'poll':
            payloads['png'] = image()
        r = self.record('observe', stage=stage, routeIndex=index, attempt=0, captureStartedUptime=start, captureFinishedUptime=start+.004, snapshot=snap,
                        files={key: dict(bytes=len(data), sha256=t.sha(data)) for key, data in payloads.items()})
        if stage == 'route-search':
            snap.update(identifier=['com.apple.settings.accessibility', 'KEYBOARDS', 'FULL_KEYBOARD_ACCESS'][index], label=t.ROUTE[index], elementType=75, valueKind='unsupported', value='', frame=dict(x=10, y=100, width=300, height=60))
            target = {**copy.deepcopy(snap), 'identifier': '', 'elementType': 48, 'frame': dict(x=20, y=110, width=200, height=20)}
            r['routeWitness'] = dict(relation='descendant', target=target)
        elif stage == 'route-opened':
            snap.update(identifier='', label='', elementType=0, exists=False, hittable=False, enabled=False, valueKind='absent', value='', frame=dict(x=0, y=0, width=0, height=0))
            destination = {**self.snap(observed=start+.002), 'identifier': t.ROUTE[index], 'label': '', 'elementType': 21, 'valueKind': 'unsupported', 'value': '', 'frame': dict(x=0, y=10, width=402, height=44)}
            r['routeWitness'] = dict(destination=destination)
        else:
            r['switchWitness'] = self.witness(snap)
        return r, payloads

    def chunks(self, payloads):
        for slot in list(self.bridge.settings.pending):
            form = slot.rsplit('-', 1)[1]
            data = payloads[form]
            item = self.bridge.settings.uploads[slot]
            for index in range(item['count']):
                yield self.record('chunk', slot=slot, index=index, count=item['count'], bytes=len(data), sha256=t.sha(data), data=base64.b64encode(data[index*3072:(index+1)*3072]).decode())

    def upload(self, payloads):
        for chunk in self.chunks(payloads):
            self.send(chunk)

    def observe(self, stage, value='0', index=3, alter=None):
        r, payloads = self.observation(stage, value, index)
        if alter: alter(r)
        self.send(r)
        self.upload(payloads)
        return r

    def routes(self, suffix=None):
        self.mark('settings-launched')
        for i in range(3):
            r = self.observe('route-search', index=i, alter=(lambda r: r['snapshot'].update(label=suffix)) if i == 2 and suffix else None)
            target = copy.deepcopy(r['routeWitness']['target'])
            target['observedUptime'] = self.now+.001
            started, finished = self.now+.002, self.now+.003
            self.mark('route-tap', dict(routeIndex=i, searchSequence=r['sequence'], target=target, startedUptime=started, finishedUptime=finished))
            self.observe('route-opened', index=i)

    def before(self, initial='0', suffix=None):
        self.routes(suffix)
        self.observe('before-switch', initial)

    def action(self, initial='0', send=True):
        parent = copy.deepcopy(self.bridge.settings.before['snapshot'])
        parent['observedUptime'] = self.now+.001
        witness = self.witness(parent)
        started = self.now+.003
        finished = started+.001 if initial == '0' else started
        anchor = finished if initial == '0' else self.bridge.settings.before['snapshot']['observedUptime']
        r = self.record('mark', stage='switch-action', detail=dict(action='tap' if initial == '0' else 'no-tap', beforeSequence=self.bridge.settings.before['sequence'], parent=parent, switchWitness=witness,
                                                                  startedUptime=started, finishedUptime=finished, anchorUptime=anchor, deadlineUptime=anchor+3.0))
        if send: self.send(r)
        return r

    def complete(self, initial='0'):
        self.before(initial)
        self.action(initial)
        self.observe('after-switch', '1')
        self.observe('terminal', '1')
        for stage in ['terminate-before', 'terminate-after', 'test-case-finished', 'suite-finished', 'bundle-finished']:
            self.mark(stage)

    def state(self):
        return copy.deepcopy({key:value for key,value in self.bridge.settings.__dict__.items() if key not in ['persist', 'persist_file', 'now', 'transaction']})

    def journal(self):
        return {path.name:path.read_bytes() for path in self.bridge.output.glob('0000-settings-*.json')}



def _http(self, record):
    server = p.h.server_for(self.bridge)
    thread = threading.Thread(target=server.handle_request, daemon=True)
    thread.start()
    client = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=3)
    try:
        client.request('POST', '/evaluate', body=json.dumps({'settingsDiagnostic':record}).encode(), headers={'Content-Type':'application/json', 'X-Mixer-Capability':self.bridge.capability})
        response = client.getresponse()
        result = response.status, json.loads(response.read())
        self.http_requests.append({'status':result[0], 'body':result[1], 'record':record})
        return result
    finally:
        client.close()
        thread.join(3)
        server.server_close()
        if thread.is_alive(): raise AssertionError('Owned loopback HTTP thread did not terminate')

Flow.http = _http
