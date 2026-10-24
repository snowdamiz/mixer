"""Synthetic positive-fixture extension only. Never imported by runtime/oracle."""
import copy
import settings_telemetry as t


def adapt(value, session):
    record = copy.deepcopy(value)
    if record.get('kind') == 'observe' and record.get('stage') in ['route-search', 'route-opened'] and 'routeWitness' not in record and type(record.get('routeIndex')) is int and 0 <= record['routeIndex'] < 3:
        index = record['routeIndex']
        target = copy.deepcopy(record['snapshot'])
        target.update(identifier='', label=t.ROUTE[index], elementType=48, valueKind='unsupported', value='')
        if record['stage'] == 'route-search':
            record['routeWitness'] = {'target': target, 'relation': 'descendant' if record['snapshot']['elementType'] == 75 else 'self'}
        else:
            target.update(identifier=t.ROUTE[index], label='', elementType=21, exists=True, hittable=True, enabled=True, foreground=True, appState=4, frame=dict(x=0, y=10, width=100, height=44))
            record['routeWitness'] = {'destination': target}
    if record.get('kind') == 'mark' and record.get('stage') == 'route-tap' and type(record.get('detail')) is dict and set(record['detail']) == {'routeIndex'}:
        index = record['detail']['routeIndex']
        search = session.route_searches.get(index)
        if search is not None and 'routeWitness' in search:
            target = copy.deepcopy(search['routeWitness']['target'])
            target['observedUptime'] = record['uptime'] - .0003
            record['detail'].update(searchSequence=search['sequence'], target=target, startedUptime=record['uptime'] - .0002, finishedUptime=record['uptime'] - .0001)
    return record
