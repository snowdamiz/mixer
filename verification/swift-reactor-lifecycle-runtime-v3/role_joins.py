"""Join every sealed V2 role to its exact raw V2/V3 compiler occurrence."""
import collections, gzip
import collect as c
from finite_metadata import display_free

OLD = c.ROOT / 'verification/swift-reactor-lifecycle-runtime-v2'
ACCOUNTING = c.ROOT / 'verification/swift-reactor-lifecycle-accounting'

def packed(name):
    return c.read_json(OLD / name)

def build(positions, declarations, bodies):
    previous = packed('occurrence-complete-positions.json')
    old_roles = packed('occurrence-complete-role-joins.json')
    old_functions = packed('occurrence-complete-function-item-role-joins.json')
    raw = {(row['config'], tuple(row['occurrenceKey'])): row for row in positions}
    previous_raw = {(row['config'], tuple(row['occurrenceKey'])): row for row in previous}
    assert len(raw) == len(positions) == len(previous_raw) == len(previous) == 2744
    assert set(raw) == set(previous_raw)
    for key, row in raw.items():
        old = previous_raw[key]
        assert old['new'] == row['old']
        assert old['newRawRecordIndex'] == row['oldRawRecordIndex']
        assert old['newQuerySHA256'] == row['oldQuerySHA256']
    inventory = c.read_json(ACCOUNTING / 'inventory-final.json')
    inventory_by_field = {(x['config'], x['field']): x for x in inventory if x['config'].endswith('-unit')}
    assert len(inventory_by_field) == sum(x['config'].endswith('-unit') for x in inventory) == 11760
    joined, functions, witnesses = [], [], []
    counts = collections.Counter()
    for role in old_roles:
        key = (role['config'], tuple(role['occurrenceKey']))
        row = raw[key]
        prior = previous_raw[key]
        definition = inventory_by_field[(role['config'], role['field'])]
        before, after = row['old'], row['new']
        assert role['newRawRecordIndex'] == row['oldRawRecordIndex']
        assert role['bodyKindOrdinal'] == row['bodyKindOrdinal']
        assert definition['body'] == before['path']
        assert definition['promoted'] == before.get('promoted')
        if role['kind'] == 'constant-operand':
            assert before['kind'] == 'constant-operand'
            assert definition['binding'].rsplit(':', 1)[0] == before['location']
            assert int(definition['binding'].rsplit(':', 1)[1]) == row['bodyKindOrdinal']
            assert definition['source'] == prior['old']['constant']
            actual_old, actual_new = before['layout'], after['layout']
        else:
            assert before['kind'] == 'local'
            assert definition['local'] == before['local']
            assert definition['sourceInfo'] == prior['old']['sourceInfo']
            if role['kind'] == 'captured-alias':
                actual_old = before['captureLayout']['fields'][definition['capture']]
                actual_new = after['captureLayout']['fields'][definition['capture']]
            else:
                actual_old, actual_new = before['layout'], after['layout']
        assert display_free(actual_old) == display_free(actual_new)
        assert role['actualIdentity'] == definition['actualIdentity'] == actual_new['identity']
        assert (role['bytes'], role['alignment']) == (actual_new['bytes'], actual_new['alignment'])
        counts[key] += 1
        joined.append({'config': role['config'], 'occurrenceKey': role['occurrenceKey'], 'role': role['role'], 'field': role['field'], 'kind': role['kind'], 'bodyKindOrdinal': row['bodyKindOrdinal'], 'oldRawRecordIndex': row['oldRawRecordIndex'], 'newRawRecordIndex': row['newRawRecordIndex'], 'oldQuerySHA256': row['oldQuerySHA256'], 'newQuerySHA256': row['newQuerySHA256'], 'sealedV2Role': role, 'originalAccountingRole': definition, 'oldRawOccurrence': before, 'newRawOccurrence': after, 'oldActualFullLayout': actual_old, 'newActualFullLayout': actual_new, 'exactRawValueSpanIdentityLayoutJoin': True, 'noNumericCreditAdded': True})
    for key, row in raw.items():
        if row['old']['kind'] in ['local', 'constant-operand']:
            assert counts[key] >= 4 and counts[key] % 4 == 0
    fn_counts = collections.Counter()
    for role in old_functions:
        key = (role['config'], tuple(role['occurrenceKey']))
        row = raw[key]
        before, after = row['old'], row['new']
        assert before['kind'] == after['kind'] == 'FnDef'
        assert role['newRawRecordIndex'] == row['oldRawRecordIndex']
        assert role['newActualLayout'] == before['layout']
        assert before['layout']['bytes'] == after['layout']['bytes'] == 0
        assert role['calleeDefPathHash'] == before['calleeDefPathHash'] == after['calleeDefPathHash']
        assert display_free(before['layout']) == display_free(after['layout'])
        functions.append({'config': role['config'], 'occurrenceKey': role['occurrenceKey'], 'position': role['position'], 'oldRawRecordIndex': row['oldRawRecordIndex'], 'newRawRecordIndex': row['newRawRecordIndex'], 'oldQuerySHA256': row['oldQuerySHA256'], 'newQuerySHA256': row['newQuerySHA256'], 'sealedV2Role': role, 'oldRawOccurrence': before, 'newRawOccurrence': after, 'noNumericCreditAdded': True})
        fn_counts[key] += 1
    assert all(fn_counts[key] == 4 for key, row in raw.items() if row['old']['kind'] == 'FnDef')
    sealed_witnesses = {(x['config'], x['declaration'], x['field']): x for x in c.read_json(OLD / 'whole-retained-carrier-witnesses.json')}
    assert len(sealed_witnesses) == 176
    for row in declarations:
        declaration = row['new']
        if not declaration['path'].rsplit('::', 1)[-1].startswith(('LifecycleActivePositions','LifecyclePermanentPositions','LifecycleNeverActivePositions','LifecycleNeverPermanentPositions')):
            continue
        old_variant = row['old']['layout']['variants'][0]
        new_variant = declaration['layout']['variants'][0]
        assert old_variant['fieldNames'] == new_variant['fieldNames']
        for name, before, after in zip(old_variant['fieldNames'], old_variant['fields'], new_variant['fields']):
            witness_key = (row['config'], declaration['path'], name)
            if witness_key not in sealed_witnesses:
                continue
            assert sealed_witnesses[witness_key]['actualFullField'] == before
            assert display_free(before) == display_free(after)
            witnesses.append({'config': row['config'], 'field': name, 'declaration': declaration['path'], 'oldFullField': before, 'newFullField': after, 'exactActualIdentityFullLayout': display_free(before) == display_free(after)})
    assert len(joined) == 11760 and len(functions) == 1296 and len(witnesses) == 176
    summary = {'schema': 'mixer.swift-lifecycle.v3-occurrence-role-proof.1', 'completeRawOccurrences': len(raw), 'kinds': dict(collections.Counter(row['old']['kind'] for row in raw.values())), 'fourRoleJoins': len(joined), 'functionItemZeroByteRoleJoins': len(functions), 'rawOldAndNewMultisetsAndOrderedIndicesExact': True, 'dictionaryPositionDeduplicationUsed': False, 'additionalAccountingCredit': 0}
    return {'occurrence-complete-role-joins.json.gz': gzip.compress(c.enc(joined), mtime=0), 'occurrence-complete-function-item-role-joins.json.gz': gzip.compress(c.enc(functions), mtime=0), 'whole-retained-carrier-witnesses.json': c.enc(witnesses), 'role-reconciliation-summary.json': c.enc(summary)}
