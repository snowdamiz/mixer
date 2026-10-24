#!/usr/bin/env python3
"""Root replay of exact V3 raw compiler bytes, multiplicities and original roles."""
import collections, datetime, gzip, hashlib, json, re, subprocess, sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
NEW=ROOT/'verification/swift-reactor-lifecycle-runtime-v3'
OLD=ROOT/'verification/swift-reactor-lifecycle-runtime-v2'
def sha(data):return hashlib.sha256(data).hexdigest()
def read(path):
 if path.is_file():return json.loads(path.read_bytes())
 return json.loads(gzip.decompress(path.with_name(path.name+'.gz').read_bytes()))
def packed(name):return json.loads(gzip.decompress((NEW/name).read_bytes()))
def enc(value):return (json.dumps(value,sort_keys=True,indent=2)+'\n').encode()
freeze_path=NEW/'pre-runtime-freeze.json'
assert len(sys.argv)==2 and sha(freeze_path.read_bytes())==sys.argv[1]
freeze=read(freeze_path)
for name,digest in freeze['files'].items():
 path=NEW/name
 assert not path.is_symlink() and sha(path.read_bytes())==digest,name
assert sha(enc(freeze['files']))==freeze['closureSHA256']
old_files={str(p.relative_to(OLD/'candidate')):sha(p.read_bytes())for p in sorted((OLD/'candidate').rglob('*'))if p.is_file()}
new_files={str(p.relative_to(NEW/'candidate')):sha(p.read_bytes())for p in sorted((NEW/'candidate').rglob('*'))if p.is_file()}
assert old_files.keys()==new_files.keys() and len(new_files)==132
changed=[k for k in old_files if old_files[k]!=new_files[k]]
assert changed==['src/experimental_swift_reactor/lifecycle_tests.rs']
left=(OLD/'candidate'/changed[0]).read_text();right=(NEW/'candidate'/changed[0]).read_text()
marker='fn swift_lifecycle_sl13_cumulative_instruction_host_and_cache_usage() {'
la,lb=left.split(marker);ra,rb=right.split(marker)
assert la==ra and lb.split('#[test]',1)[1]==rb.split('#[test]',1)[1]
assert sha(enc(new_files))=='93adb6ac2d00acab30c02df8d96e044452edc14d704a6738a58874b0968b5f38'
command=[sys.executable,'-B',str(NEW/'verify_pre_runtime.py')]
result=subprocess.run(command,cwd=ROOT,capture_output=True)
(HERE/'producer-verify.stdout').write_bytes(result.stdout)
(HERE/'producer-verify.stderr').write_bytes(result.stderr)
assert result.returncode==0,result.stderr.decode()
proof=read(NEW/'unchanged-runtime-proof.json')
contexts = {row['config']: row for row in proof['contexts']}
raw = {}
ordered_raw = {}
for config in contexts:
    for side, directory in [('old', OLD), ('new', NEW)]:
        query = read(directory / ('exact-query-' + config + '.json'))
        data = gzip.decompress((directory / query['attempt'] / 'exact-layouts.jsonl.gz').read_bytes())
        assert sha(data) == query['sha256'] == contexts[config][side + 'QuerySHA256']
        # Membership is joined to actual compiler rows, not producer booleans.
        ordered_raw[(config, side)] = [json.loads(line) for line in data.splitlines()]
        raw[(config, side)] = collections.Counter(enc(row) for row in ordered_raw[(config, side)])

def bound(row, key_old='old', key_new='new'):
    left = raw[(row['config'], 'old')][enc(row[key_old])]
    right = raw[(row['config'], 'new')][enc(row[key_new])]
    assert left > 0 and left == right

def allocations(text, mapping):
    tokens = set(re.findall(r'\balloc\d+\b', text))
    assert tokens <= mapping.keys()
    return re.sub(r'\balloc\d+\b', lambda match: mapping[match[0]], text)

def walk(before, after, field, config):
    assert type(before) is type(after)
    if isinstance(before, dict):
        assert before.keys() == after.keys()
        for key in before:
            walk(before[key], after[key], key, config)
    elif isinstance(before, list):
        assert len(before) == len(after)
        for left, right in zip(before, after):
            walk(left, right, field, config)
    elif isinstance(before, str):
        adjusted = before
        if field in ('sourceInfo', 'span'):
            mapping = config['finiteSourceHygieneIndexBijection']
            adjusted = re.sub(r'\(#(\d+)\)', lambda match: '(#' + mapping[match[1]] + ')', adjusted)
        if field == 'constant':
            adjusted = allocations(adjusted, config['finiteAllocationBijection'])
        # Numeric session DefIds are diagnostic indices, not stable DefPathHash.
        # Retain the complete displayed definition path and all stable identities.
        normalize = lambda value: re.sub(r'DefId\(\d+:\d+ ~ ', 'DefId(<session-index> ~ ', value)
        assert normalize(adjusted) == normalize(after), (field, before, after)
    else:
        assert before == after

for context in contexts.values():
    for key in ['finiteAllocationBijection', 'finiteSourceHygieneIndexBijection']:
        mapping = context[key]
        assert len(mapping) == len(set(mapping.values()))

bodies = packed('runtime-body-reconciliation.json.gz')
assert len(bodies) == 160
assert len({(r['config'], r['path'], r['promoted']) for r in bodies}) == len(bodies)
for row in bodies:
    bound(row, 'oldBody', 'newBody')
    assert row['oldBody']['defPathHash'] == row['newBody']['defPathHash']
    mapping = contexts[row['config']]['finiteAllocationBijection']
    assert allocations(row['oldBody']['mir'], mapping) == row['newBody']['mir']
    for allocation in row['allocationGraphProof']:
        assert allocations(allocation['oldFullAllocation'], mapping) == allocation['newFullAllocation']

counts = {}
covered_positions = collections.defaultdict(collections.Counter)
for name, expected in [('runtime-position-reconciliation.json.gz', 2744),
                       ('owner-carrier-layout-reconciliation.json.gz', 116),
                       ('actual-type-graph-reconciliation.json.gz', 2330)]:
    rows = packed(name)
    assert len(rows) == expected
    for row in rows:
        bound(row)
        walk(row['old'], row['new'], None, contexts[row['config']])
        if name == 'runtime-position-reconciliation.json.gz':
            for side in ['old', 'new']:
                assert ordered_raw[(row['config'], side)][row[side + 'RawRecordIndex']] == row[side]
                covered_positions[(row['config'], side)][enc(row[side])] += 1
    counts[name] = len(rows)

# A MIR statement may contain the same constant operand twice. Preserve and
# compare that multiplicity, and prove no actual selected position is omitted.
position_occurrences = {}
for config in contexts:
    body_keys = {(row['path'], row['promoted']) for row in bodies if row['config'] == config}
    for side in ['old', 'new']:
        selected = collections.Counter()
        for encoded, multiplicity in raw[(config, side)].items():
            record = json.loads(encoded)
            if record['kind'] in ['local', 'constant-operand', 'FnDef'] and (record.get('path'), record.get('promoted')) in body_keys:
                selected[encoded] = multiplicity
        assert selected == covered_positions[(config, side)]
        position_occurrences[config + '-' + side] = sum(selected.values())
    assert position_occurrences[config + '-old'] == position_occurrences[config + '-new']


prior_roles=read(OLD/'occurrence-complete-role-joins.json')
prior_by_field={(r['config'],r['field']):r for r in prior_roles}
roles=packed('occurrence-complete-role-joins.json.gz')
assert len(roles)==len(prior_by_field)==11760
assert len({(r['config'],r['field'])for r in roles})==11760
role_coverage=collections.Counter()
for row in roles:
 prior=prior_by_field[(row['config'],row['field'])]
 assert row['sealedV2Role']==prior
 before=ordered_raw[(row['config'],'old')][row['oldRawRecordIndex']]
 after=ordered_raw[(row['config'],'new')][row['newRawRecordIndex']]
 assert before==row['oldRawOccurrence'] and after==row['newRawOccurrence']
 assert prior['newRawRecordIndex']==row['oldRawRecordIndex']
 walk(before,after,None,contexts[row['config']])
 walk(row['oldActualFullLayout'],row['newActualFullLayout'],None,contexts[row['config']])
 assert row['noNumericCreditAdded'] is True
 role_coverage[(row['config'],row['newRawRecordIndex'])]+=1
positions=packed('runtime-position-reconciliation.json.gz')
for row in positions:
 if row['new']['kind'] in ['local','constant-operand']:
  assert role_coverage[(row['config'],row['newRawRecordIndex'])]>=4
fn_roles=packed('occurrence-complete-function-item-role-joins.json.gz')
assert len(fn_roles)==1296
prior_fn=read(OLD/'occurrence-complete-function-item-role-joins.json')
assert len(prior_fn)==len(fn_roles)
for row,prior in zip(fn_roles,prior_fn):
 assert row['sealedV2Role']==prior
 before=ordered_raw[(row['config'],'old')][row['oldRawRecordIndex']]
 after=ordered_raw[(row['config'],'new')][row['newRawRecordIndex']]
 assert before==row['oldRawOccurrence'] and after==row['newRawOccurrence']
 assert before['layout']['bytes']==after['layout']['bytes']==0
 walk(before,after,None,contexts[row['config']])
frozen=read(NEW/'frozen-identity-proof.json')
assert len(frozen['oldExpandedMethods'])==39 and frozen['oldExpandedMethods']==frozen['newExpandedMethods']
selection={'schema':'mixer.swift-lifecycle-test-repair-runtime-selection.1','observedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'sourceRevisionContext':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
 'candidateClosure':sha(enc(new_files)),'preRuntimeFreezeSHA256':sha(freeze_path.read_bytes()),'preRuntimeSealSHA256':sha((NEW/'seal.json').read_bytes()),
 'rootReviewScriptSHA256':sha(Path(__file__).read_bytes()),'producerCommand':command,'producerExitCode':result.returncode,
 'frozenFilesVerified':len(freeze['files']),'wholeRuntimeBodiesCompared':len(bodies),'rawCompilerRowsJoined':counts,
 'unitRoleRows':len(roles),'zeroByteFunctionItemRoles':len(fn_roles),'actualPositionOccurrences':position_occurrences,
 'finiteRepresentationAccepted':True,'additionalAccountingCredit':0,'runtimeResult':'pending',
 'reason':'Only SL13 body changed. Complete runtime MIR, allocation payloads/references, raw position multiplicities, stable identities and layouts remain equivalent under the previously accepted exact finite representation rules. No limits or ownership changed.',
 'limitations':['Full macro expansion chains not queried; no general normalization permission.','SL12 guest table mutation, complete original matrix, real full Swift reactor, live integration, native and GA remain pending.'],
 'selectedNext':['Run23authored lifecycle tests in Swift/all-feature Debug/Release.','If all pass, execute previously selected Frozen, complete Swift/all Debug/Release and default/span regressions with pinned compiler/Node.','Preserve failed attempts, stop dependent promotion on failure, retain source freeze and clean owned targets.']}
(HERE/'runtime-selection.json').write_bytes(enc(selection))
print(json.dumps({'accepted':True,'selectionSHA256':sha(enc(selection)),'bodies':len(bodies),'positions':len(positions),'roles':len(roles),'frozenFiles':len(freeze['files'])},indent=2))
