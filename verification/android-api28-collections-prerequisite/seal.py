#!/usr/bin/env python3
"""Seal this bounded proposal only; no product, root metadata or Git operations."""
from pathlib import Path
import datetime, hashlib, json, shutil, sys
sys.dont_write_bytecode=True
import run as producer

def main():
    packet=Path(__file__).resolve().parent
    root=packet.parents[1]
    source_map=json.loads((packet/'source-map.json').read_text())
    for path,row in source_map.items():
        expected={key:row[key] for key in ('bytes','sha256')}
        assert producer.identity(root/row['snapshot'])==expected,path
        if path.endswith('.java'):assert producer.identity(root/path)==expected,path
    audit=json.loads((packet/'audit-receipt.json').read_text())
    assert audit['audited_Java_members']==170 and audit['audited_Java_types']==60
    assert audit['post28_or_unknown_java_members']==0 and audit['D8_helper_call_edges']==57
    assert audit['source_factory_calls']==43 and audit['source_Java_files_unchanged']==20
    assert len(audit['controls'])==4 and all(row['rejected'] for row in audit['controls'])
    run=json.loads((packet/'attempt-1/receipt.json').read_text())
    strict=json.loads((packet/'consumer-flags/receipt.json').read_text())
    mismatch=json.loads((packet/'empty-mutation-witness/receipt.json').read_text())
    disassembler=json.loads((packet/'attempt-1/dexdump-command.json').read_text())
    assert run['status'].startswith('passed') and strict['status'].startswith('passed') and mismatch['status'].startswith('passed')
    assert run['cleanup']['owned_children_reaped'] and run['cleanup']['owned_scratch_removed']
    assert strict['owned_scratch_removed'] and mismatch['owned_scratch_removed']
    assert all(row['owned_child_reaped'] for row in strict['commands']+mismatch['commands'])
    assert disassembler['exit_code']==0 and disassembler['owned_child_reaped']
    cache=packet/'__pycache__'
    if cache.exists():shutil.rmtree(cache)
    final={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'argv':sys.argv,'python':sys.version,
        'context_revision':producer.CONTEXT,'context_revision_is_inherited_not_live_git':True,
        'status':'frozen-source/compiler-proposal-for-independent-review',
        'recommendation':'Accept exact emitted-library/API-floor evidence for selected read-only private consumers; no product replacement required by current evidence.',
        'compiled_Java_sources':20,'adapter_Java_members':17,'adapter_projection_members':23,
        'source_factory_calls':43,'private_V2_factory_calls':41,'additional_V1_factory_calls':2,
        'Java_members_API28_or_earlier':170,'Java_types_API28_or_earlier':60,'relevant_D8_edges':57,
        'prototype_and_existing_pure_source_JVM_assertions':93,'separate_empty_exception_mismatch_JVM_assertions':8,
        'negative_metadata_controls':4,'exact_consumer_javac_and_D8_flags_repeat_passed':True,
        'implicit_JVM_options_cleared_for_tests':True,
        'source_Java_stability_verified':True,'owned_host_children_recorded_and_reaped':16,
        'owned_scratch_removed':True,'owned_Python_bytecode_cache_removed':not cache.exists(),
        'native_UI_capture_simulator_emulator_phone_or_process_inventory':False,
        'product_or_canonical_CLI_or_rootmetadata_or_Git_mutation':False,'new_dependencies':[],
        'unselected_prototype':True,'root_and_independent_selection_pending':True,
        'universal_Java17_factory_exception_equivalence':False,'Android_API28_runtime_proved':False,
        'public_V2_selected':False,'new_rendering_contexts_admitted':0,
        'retained_failed_audits':['audit-attempt-1-failure.json','audit-attempt-2-failure.json'],
        'pending':json.loads((packet/'proposed-contract.json').read_text())['pending']}
    (packet/'final-receipt.json').write_text(json.dumps(final,indent=2,sort_keys=True)+'\n')
    members={}
    for path in sorted(packet.rglob('*')):
        assert not path.is_symlink(),str(path)
        if path.is_dir() or path==packet/'manifest.json':continue
        assert '__pycache__' not in path.parts,str(path)
        members[str(path.relative_to(root))]=producer.identity(path)
    doc=root/'docs/android-api28-collections-prerequisite.md'
    members[str(doc.relative_to(root))]=producer.identity(doc)
    manifest={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'argv':sys.argv,
        'python':sys.version,'status':final['status'],'scope':final['recommendation'],
        'context_revision':producer.CONTEXT,'context_revision_is_inherited_not_live_git':True,
        'files':dict(sorted(members.items())),'members':len(members),
        'bytes':sum(row['bytes'] for row in members.values()),
        'new_profile_or_product_implementation_selected':False,'native_runtime_qualified':False,
        'universal_factory_exception_equivalence':False,'new_rendering_contexts_admitted':0}
    (packet/'manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'manifest':str((packet/'manifest.json').relative_to(root)),
        'identity':producer.identity(packet/'manifest.json'),'members':len(members),'bytes':manifest['bytes']},sort_keys=True))

if __name__=='__main__':main()
