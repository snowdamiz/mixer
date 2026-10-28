#!/usr/bin/env python3
"""Synthetic parser/owned-process controls only. No subprocess and no layout evidence."""
import copy
import json
import os
from pathlib import Path
import signal
import subprocess
import time

from diagnostics import Rejected, parse, point, source_map
from run import stop_owned

D = Path(__file__).resolve().parent


def span(raw, name, loc, *, primary=True, expansion=None, label=None):
    sl, sc = point(raw, loc['byte_start']); el, ec = point(raw, loc['byte_end'])
    lines = raw.decode().splitlines()[sl-1:el]
    return {'file_name': name, 'byte_start': loc['byte_start'], 'byte_end': loc['byte_end'],
            'line_start': sl, 'line_end': el, 'column_start': sc, 'column_end': ec, 'is_primary': primary,
            'text': [{'text': text, 'highlight_start': sc if i == 0 else 1,
                      'highlight_end': ec if i == len(lines)-1 else len(text)+1} for i, text in enumerate(lines)],
            'expansion': expansion, 'label': label}


def fixture(plan, sources):
    """Arbitrary synthetic sizes are solely parser fixtures; never stored as observations."""
    objects = []
    for query in plan['diagnostics']['named_queries']:
        name = query['file']; raw = sources[name]
        expansion = {'span': span(raw, name, query['invocation'], primary=False), 'macro_decl_name': 'pair!', 'def_site_span': None}
        for kind in ['size', 'alignment']:
            primary = span(raw, name, query['macro_expressions'][kind], expansion=copy.deepcopy(expansion),
                           label='expected an array with a size of 0, found one with a size of ' + ('32' if kind == 'size' else '8'))
            objects.append({'$message_type': 'diagnostic', 'level': 'error', 'code': {'code': 'E0308'}, 'message': 'mismatched types', 'spans': [primary], 'children': []})
    closure = plan['diagnostics']['actual_closure']; name = closure['file']; raw = sources[name]; loc = closure['identity_span']
    identity = '{closure@' + name + ':' + str(loc['line_start']) + ':' + str(loc['column_start']) + ': ' + str(loc['line_end']) + ':' + str(loc['column_end']) + '}'
    for kind in ['size', 'alignment_wrapper']:
        shape = 'MaybeUninit<' + identity + '>'
        if kind == 'alignment_wrapper': shape = 'ClosureAlignmentProbeV1<' + shape + '>'
        notes = ['source type: `' + shape + '` (' + ('256' if kind == 'size' else '320') + ' bits)', 'target type: `[u8; 0]` (0 bits)']
        objects.append({'$message_type': 'diagnostic', 'level': 'error', 'code': {'code': 'E0512'},
            'message': 'cannot transmute between types of different sizes, or dependently-sized types',
            'spans': [span(raw, name, closure['queries'][kind])],
            'children': [{'level': 'note', 'code': None, 'message': note, 'spans': [], 'children': []} for note in notes]})
    return objects


def encoded(objects): return ('\n'.join(json.dumps(obj) for obj in objects) + '\n').encode()


def main():
    start = time.monotonic(); plan = json.loads((D / 'plan.json').read_text()); sources = source_map(plan, D)
    objects = fixture(plan, sources); baseline = parse(encoded(objects), plan, sources)
    assert len(baseline['named']) == 28 and baseline['actual_closure']['alignment'] == 8
    controls = []
    def reject(name, mutate):
        data = copy.deepcopy(objects); mutate(data)
        try: parse(encoded(data), plan, sources)
        except (Rejected, ValueError, UnicodeError, KeyError, TypeError): controls.append({'name': name, 'rejected': True})
        else: raise AssertionError('adverse synthetic output accepted: ' + name)
    reject('missing-named-primary', lambda x: x.pop(0))
    reject('duplicate-named-primary', lambda x: x.append(copy.deepcopy(x[0])))
    reject('wrong-primary-code', lambda x: x[0]['code'].update(code='E0000'))
    reject('wrong-primary-source-file', lambda x: x[0]['spans'][0].update(file_name='/unfrozen/proxy.rs'))
    reject('wrong-macro-expansion', lambda x: x[0]['spans'][0]['expansion'].update(macro_decl_name='proxy!'))
    reject('wrong-expansion-invocation', lambda x: x[0]['spans'][0]['expansion'].update(span=copy.deepcopy(x[2]['spans'][0]['expansion']['span'])))
    reject('wrong-displayed-source-line', lambda x: x[0]['spans'][0]['text'][0].update(text='proxy'))
    reject('wrong-byte-coordinate', lambda x: x[0]['spans'][0].update(byte_start=x[0]['spans'][0]['byte_start']+1))
    reject('non-concrete-named-size', lambda x: x[0]['spans'][0].update(label='expected array, source size can vary'))
    reject('unexpected-warning', lambda x: x.append({'$message_type': 'diagnostic', 'level': 'warning', 'code': {'code': 'unused_imports'}, 'message': 'unused import', 'spans': [], 'children': []}))
    reject('unexpected-uncoded-error', lambda x: x.append({'$message_type': 'diagnostic', 'level': 'error', 'code': None, 'message': 'unexpected error', 'spans': [], 'children': []}))
    reject('unexpected-named-child-note', lambda x: x[0]['children'].append({'level': 'note', 'code': None, 'message': 'proxy source size: 32', 'spans': [], 'children': []}))
    reject('missing-closure-primary', lambda x: x.pop())
    reject('duplicate-closure-primary', lambda x: x.append(copy.deepcopy(x[-1])))
    reject('proxy-closure-type', lambda x: x[-1]['children'][0].update(message='source type: `ClosureAlignmentProbeV1<ProxyCaptures>` (320 bits)'))
    reject('dependently-sized-closure', lambda x: x[-1]['children'][0].update(message=x[-1]['children'][0]['message'].replace('(320 bits)', '(size can vary)')))
    reject('wrong-closure-identity', lambda x: x[-1]['children'][0].update(message=x[-1]['children'][0]['message'].replace('{closure@', '{closure@proxy/')))
    reject('inexact-closure-identity-endpoint', lambda x: x[-1]['children'][0].update(message=x[-1]['children'][0]['message'].replace(': ' + str(plan['diagnostics']['actual_closure']['identity_span']['line_end']) + ':' + str(plan['diagnostics']['actual_closure']['identity_span']['column_end']) + '}', ': ' + str(plan['diagnostics']['actual_closure']['expression']['line_end']) + ':' + str(plan['diagnostics']['actual_closure']['expression']['column_end']) + '}')))
    reject('non-byte-closure-size', lambda x: x[-2]['children'][0].update(message=x[-2]['children'][0]['message'].replace('(256 bits)', '(255 bits)')))
    reject('nonpositive-closure-size', lambda x: x[-2]['children'][0].update(message=x[-2]['children'][0]['message'].replace('(256 bits)', '(0 bits)')))
    reject('non-power-two-closure-alignment', lambda x: x[-1]['children'][0].update(message=x[-1]['children'][0]['message'].replace('(320 bits)', '(280 bits)')))
    reject('wrong-closure-transmute-site', lambda x: x[-1].update(spans=copy.deepcopy(x[-2]['spans'])))
    reject('wrong-closure-target-type', lambda x: x[-1]['children'][1].update(message='target type: `[u8; 1]` (8 bits)'))
    class FakeProcess:
        pid = 212121; returncode = None
        def wait(self, timeout): self.returncode = 1; return 1
    def gone(pid, sig): raise ProcessLookupError()
    failures = []; actions = []
    result = stop_owned(FakeProcess(), time.monotonic()+1, failures, actions, killpg=gone, kill=gone)
    assert result['child_reaped'] and result['exact_pid_absent'] and result['exact_group_absent'] and not failures
    controls.append({'name': 'synthetic-owned-success-reaped-and-absent', 'passed': True})
    class BrokenWait(FakeProcess):
        def wait(self, timeout): raise RuntimeError('injected wait failure')
    failures = []; actions = []
    result = stop_owned(BrokenWait(), time.monotonic()+1, failures, actions, killpg=gone, kill=gone, waitpid=lambda pid, flags: (pid, 256))
    assert result['child_reaped'] and result['exact_group_absent'] and failures[0]['classification'] == 'owned-wait-failure'
    controls.append({'name': 'synthetic-wait-failure-exact-waitpid-fallback', 'passed': True})
    class NeverReaped(FakeProcess):
        def wait(self, timeout): raise subprocess.TimeoutExpired('synthetic', timeout)
    ticks = [0.0]
    def clock(): return ticks[0]
    def pause(seconds): ticks[0] += max(seconds, .01)
    failures = []; actions = []
    result = stop_owned(NeverReaped(), .05, failures, actions, clock=clock, pause=pause, killpg=lambda p,s: None, kill=lambda p,s: None)
    assert not result['child_reaped'] and result['exact_pid_absent'] is False and result['exact_group_absent'] is False
    controls.append({'name': 'synthetic-unreaped-present-group-forbids-cleanup', 'passed': True})
    failures = []; actions = []
    result = stop_owned(None, 1, failures, actions, killpg=lambda p,s: (_ for _ in ()).throw(AssertionError('must not signal')))
    assert not result['child_started'] and actions == ['no-child-started'] and not failures
    controls.append({'name': 'synthetic-no-spawn-failure-no-signal', 'passed': True})
    def denied(pid, sig): raise PermissionError('synthetic absence denied')
    failures = []; actions = []
    result = stop_owned(FakeProcess(), time.monotonic()+1, failures, actions, killpg=denied, kill=gone)
    assert result['exact_group_absent'] is None and failures
    controls.append({'name': 'synthetic-absence-ambiguity-preserved', 'passed': True})
    report = {'schema': 1, 'status': 'synthetic-offline-controls-passed', 'controls': controls,
              'synthetic_sizes_are_not_product_observations': True, 'actual_layout_strategy_qualified': False,
              'compiler_runtime_or_child_processes_started': 0, 'elapsed_seconds': time.monotonic()-start}
    with (D / 'controls-result.json').open('x') as handle: json.dump(report, handle, indent=2); handle.write('\n')
    print(json.dumps({'status': report['status'], 'controls': len(controls), 'compiler_or_child_processes': 0}))


if __name__ == '__main__': main()
