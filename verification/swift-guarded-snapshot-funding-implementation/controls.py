"""Exact source differential/ordering controls; no release authorization by syntax."""
from collections import Counter
from pathlib import Path
import json
import re
import sys

sys.dont_write_bytecode = True
from prepare import HERE, BASE, RECIPE, CONTROL, PROFILE, AUTHORITY_TREE, canonical, members, sha, write
from verify import ACCEPTANCE, ACCEPTANCE_SHA, custody

def body(text, start, end):
    first = text.index(start)
    return text[first:text.index(end, first)]

def main():
    binding = custody()
    preparation = json.loads((HERE/'preparation.json').read_text())
    baseline = BASE/'source/vm'
    candidate = HERE/'source/vm'
    checks = []
    def check(label, ok):
        assert ok, label
        checks.append(dict(name=label, passed=True))
    check('accepted source144 recipe receipt', sha(ACCEPTANCE.read_bytes()) == ACCEPTANCE_SHA)
    check('frozen authority source tree', sha(canonical(members(baseline))) == AUTHORITY_TREE)
    check('candidate source count', len(members(candidate)) == 144)
    changed = []
    for entry in members(baseline):
        name = entry['path']
        if (candidate/name).read_bytes() != (baseline/name).read_bytes():
            changed.append(name)
    check('exact two changed files', changed == [PROFILE, CONTROL])
    inverse = {name:(candidate/name).read_text() for name in changed}
    for row in reversed(preparation['exact_replacements']):
        check('unique exact inverse replacement '+row['reason'], inverse[row['path']].count(row['new']) == 1)
        inverse[row['path']] = inverse[row['path']].replace(row['new'],row['old'])
    for name in changed:
        check('full file restored by declared replacement '+name, inverse[name] == (baseline/name).read_text())
    new_control = (candidate/CONTROL).read_text()
    old_control = (baseline/CONTROL).read_text()
    new_profile = (candidate/PROFILE).read_text()
    old_profile = (baseline/PROFILE).read_text()
    original_const = body(old_control, 'const FOUNDATION_CONSTRUCTION_BYTES:', '\n/// Conservative named-object foundation envelope.')
    check('original F0 initializer preserved byte-for-byte', original_const in new_control)
    check('exact source constants fragment installed once',new_control.count((HERE/'funding-constants.inc.rs').read_text()) == 1)
    check('C once in const block',new_control.count('const COMMON_ADOPTION_SOURCE_EXTRA_BYTES_V1: usize = 78_240;') == 1)
    check('S once in const block',new_control.count('const SELECTED_SNAPSHOT_SOURCE_EXTRA_BYTES_V1: usize = 941_467;') == 1)
    check('A once in const block',new_control.count('const SNAPSHOT_ADMITTED_SOURCE_EXTRA_BYTES_V1: usize = 430_175;') == 1)
    check('H once in cfg(test) const block',new_control.count('const SNAPSHOT_HOST_CALLER_SOURCE_EXTRA_BYTES_V1: usize = 81_327;') == 1)
    boundaries = [
        (CONTROL,'    pub(crate) fn finish_owned_cleanup','\n// Isolated source preparation.'),
        (CONTROL,'impl SnapshotRunV1 {','\n#[derive(Clone,Copy,Debug,PartialEq,Eq)]'),
        (PROFILE,'impl SnapshotAccessV1<\'_> {','\nstruct SnapshotShapeV1'),
        (PROFILE,'fn proposed_emission_work_v1(','\nfn begin_snapshot_access_v1'),
        (PROFILE,'fn begin_snapshot_access_v1','\n#[derive(Clone,Copy)]'),
        (PROFILE,'#[cfg(test)]\nmod future_genuine_composition_v1','\n    }\n}'),
    ]
    preserved = []
    for name,start,end in boundaries:
        a=body((baseline/name).read_text(),start,end)
        b=body((candidate/name).read_text(),start,end)
        check('preserved exact boundary '+start,a==b)
        preserved.append(dict(path=name,source_start=start,sha256=sha(a.encode()),bytes=len(a.encode())))
    begin=body(new_profile,'fn begin_snapshot_access_v1','\n#[derive(Clone,Copy)]')
    order=['cache.snapshot_pair_v1(control,wasi)?;', 'let additional=SNAPSHOT_PHASE_PLACES_V1;',
           'control.snapshot_storage_preflight_v1(additional)?;', 'control.snapshot_debit_v1(planning)?;',
           'let shape=snapshot_shape_v1(cache.proof().snapshot_counts_v1())?;',
           'let emission=proposed_emission_work_v1(&shape)?;', 'control.snapshot_debit_v1(emission)?;',
           'let previous=control.snapshot_commit_storage_v1(additional)?;',
           'transfer:Some([0;4096])']
    positions=[begin.index(text) for text in order]
    check('pairing then preflight then work then commit then transfer ordering',positions==sorted(positions))
    check('fail-closed original WorkAuditPending', 'Err(AError::WorkAuditPending)' in body(new_profile,'fn proposed_emission_work_v1(','\nfn begin_snapshot_access_v1'))
    check('conditional A constant replaces placeholder once',new_profile.count('const SNAPSHOT_PHASE_PLACES_V1:usize=super::super::control::SNAPSHOT_ADMITTED_SOURCE_EXTRA_BYTES_V1;')==1)
    check('conditional A not placeholder plus exact amount', 'const SNAPSHOT_PHASE_PLACES_V1:usize=size_of' not in new_profile)
    check('placeholder scope aggregates not read by selected foundation', 'size_of' not in body(new_control,'fn snapshot_scope_candidate_foundation_v1()','\n#[cfg(mixer_snapshot_composition_layout)]'))
    # Fresh compiler evidence establishes runtime places. Source comparisons
    # above support provenance/invariance only, never OTA/writer admission.
    contexts=[]
    for mode in ['production','unit']:
        receipt=json.loads((HERE/'commands'/('metadata-'+mode)/'receipt.json').read_text())
        check('metadata/MIR success '+mode,receipt['expectation_met'] and receipt['exit_code']==0)
        for name in ['foundation_construction_bytes','snapshot_scope_candidate_foundation_v1']:
            roles=receipt['funding_function_summary'][name]['declared_locals']
            check('only existing Option return place '+mode+' '+name,roles==[dict(name='_0',type='std::option::Option<usize>')])
        contexts.append(dict(mode=mode,source_binding=receipt['source_binding'],
            compiler_sha256=receipt['compiler_sha256'],funding_function_summary=receipt['funding_function_summary']))
    old_raw=json.loads((HERE.parent/'swift-guarded-snapshot-owner-storage-closure/raw-inventory.json').read_text())
    old_fn=next(f for f in old_raw['functions'] if f['name']=='snapshot_scope_candidate_foundation_v1')
    funding=json.loads((RECIPE/'funding.json').read_text())
    retained=[r for r in funding['roles'] if r['id'].startswith('owner::snapshot_scope_candidate_foundation_v1::')]
    retained_sum=sum(sum(r['funding'].values()) for r in retained)
    check('entire old selected-floor charge retained',retained_sum==200)
    check('no optional or removed-role credits',json.loads((RECIPE/'formula.json').read_text())['common_extra']==78240)
    write('source-delta-accounting.json',dict(schema=1,source_binding=binding,
        accepted_recipe=dict(C=78240,S=941467,A=430175,H=81327),
        F0_initializer_sha256=sha(original_const.encode()),F0_added_again=False,
        changed_runtime_functions=['foundation_construction_bytes','snapshot_scope_candidate_foundation_v1'],
        fresh_compiler_contexts=contexts,added_runtime_roles=0,added_runtime_storage_bytes=0,
        new_runtime_helper_functions=0,new_runtime_calls=0,new_type_or_field_layouts=0,
        delta_rule='All added arithmetic and cfg selection is evaluated in constants; fresh compiler MIR floor bodies have only the existing Option<usize> return place.',
        old_selected_floor_roles=len(old_fn['roles']),retained_old_charge_bytes=retained_sum,
        removed_role_credits_selected=False,optional_2192_byte_credit_selected=False,
        layout_scope='No declared type/field or argument/return type changes. Existing Option<usize> return is 16 bytes in the accepted source144 target inventory. No physical stack/RSS bound is claimed.',
        placeholder_type_inventories='Retained for historical/layout probes, never added to exact recipe grants.',
        preserved_boundaries=preserved))
    write('ordering-controls.json',dict(schema=1,source_binding=binding,controls=checks,
        passed=len(checks),order=[dict(source=text,position=n) for text,n in zip(order,positions)],
        runtime_or_writer_executed=False,syntax_authorizes_release=False,
        scope='Source provenance/differential/ordering plus fresh compiler-MIR reconciliation only'))
    write('accepted-recipe-input.json',dict(schema=1,path=str(ACCEPTANCE),sha256=ACCEPTANCE_SHA,
        accepted_scope='Corrected isolated logical source144 recipe only',
        receipt=json.loads(ACCEPTANCE.read_text()),source_integration_independent_review_pending=True))
    print(json.dumps(dict(passed=len(checks),runtime_roles_added=0,retained_removed_role_bytes=200,
                         compiler_contexts=2,writer_dispatched=False),sort_keys=True))

if __name__=='__main__':
    main()
