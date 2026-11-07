"""Observation-only side-channel adapter. Standard library; no runtime imports.

This module is new diagnostic support, not a replacement keyboard oracle. The
prepared bridge calls strip_and_retain once, then executes its original closed
keyboardWitness branch with the exact original witness object.
"""
import copy
import json
import math

SCHEMA = 'mixer.apple-toggle.focus-diagnostic.1'
IDS = ('authored-toggle', 'plain-uibutton-reference', 'next-focus')
MAX_RECORD_BYTES = 4096
MAX_OBSERVATIONS = 4
MAX_CONTEXTS = 128


def number(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def strip_and_retain(body, binding, save):
    """Retain bounded telemetry; it can neither choose nor rewrite a witness.

    An invalid diagnostic becomes an explicitly incomplete receipt. Persistence
    failure propagates fail-closed; no success verdict is manufactured here.
    """
    if type(body) is not dict or set(body) != {'keyboardWitness', 'focusDiagnostic'}:
        return body
    value = body['focusDiagnostic']
    try:
        raw = json.dumps(value, allow_nan=False, separators=(',', ':')).encode()
        valid = (len(raw) <= MAX_RECORD_BYTES and type(value) is dict
                 and value.get('schema') == SCHEMA
                 and type(value.get('case')) is str
                 and type(value.get('generation')) is int and type(value.get('actionIndex')) is int
                 and all(value.get(key) == binding[key] for key in ('case', 'generation', 'actionIndex'))
                 and value.get('authoritative') is False)
    except (KeyError, TypeError, ValueError, OverflowError):
        valid = False
    record = (copy.deepcopy(value) if valid else
              {'schema': SCHEMA, **binding, 'authoritative': False,
               'captureStatus': 'incomplete-invalid-or-oversize-diagnostic'})
    save('focus-diagnostic-' + str(binding['actionIndex']), record)
    return {'keyboardWitness': body['keyboardWitness']}


def endpoint(item):
    """Host schema model of the public UIKit endpoint, including explicit null."""
    if item is None:
        return {'state': 'null', 'identifier': None, 'class': None,
                'identity': None, 'frame': None, 'frameInWindow': None,
                'attachedToWindow': None}
    return {'state': 'item', 'identifier': item.get('identifier'),
            'class': item['class'], 'identity': item['identity'],
            'frame': item['frame'], 'frameInWindow': item.get('frameInWindow'),
            'attachedToWindow': item.get('attachedToWindow')}


def endpoint_scope(value):
    if value['state'] == 'null':
        return 'explicit-null'
    return 'fixed-id' if value['identifier'] in IDS else 'outside-fixed-ids'


class ContextBuffer:
    """Host model of the separately bounded Swift context trace."""
    def __init__(self):
        self.entries = []
        self.dropped = 0
        self.revision = 0

    def append(self, source, previous, next_item, heading, uptime):
        self.revision += 1
        if len(self.entries) >= MAX_CONTEXTS:
            self.dropped += 1
            return
        self.entries.append({'sequence': self.revision, 'uptime': uptime,
                             'source': source, 'heading': heading,
                             'previous': endpoint(previous), 'next': endpoint(next_item)})


def observation_status(rows, started, finished):
    """Do not collapse sequential per-property reads into one atomic instant."""
    if not number(started) or not number(finished) or finished < started:
        raise ValueError('Invalid collection interval')
    prior = started
    for row in rows:
        if (not number(row['startedUptime']) or not number(row['finishedUptime'])
                or not prior <= row['startedUptime'] <= row['finishedUptime'] <= finished):
            raise ValueError('Nonmonotonic row interval')
        prior = row['finishedUptime']
    return {'atomic': False, 'rowCount': len(rows), 'startedUptime': started,
            'finishedUptime': finished}


def focus_only_once(read, clock, action_deadline, allowance=.250):
    """Host model: one pass, no wait/retry, deadline never later than original.

    Like a public synchronous XCUI read, read() cannot be preempted. A read that
    returns late is retained as incomplete and stops further observations.
    """
    start = clock()
    deadline = min(action_deadline, start + allowance)
    rows = []
    for identifier in IDS:
        if clock() >= deadline:
            break
        row_start = clock()
        has_focus = read(identifier)
        row_end = clock()
        rows.append({'identifier': identifier, 'hasFocus': has_focus,
                     'startedUptime': row_start, 'finishedUptime': row_end})
        if row_end >= deadline:
            break
    finished = clock()
    return {'atomic': False, 'startedUptime': start, 'finishedUptime': finished,
            'deadlineUptime': deadline, 'rows': rows,
            'captureStatus': 'complete' if len(rows) == len(IDS) and finished <= deadline else 'incomplete-budget'}
