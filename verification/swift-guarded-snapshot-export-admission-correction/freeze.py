"""Freeze this exact bounded packet after checking its recorded expectations."""
import hashlib,json,pathlib
HERE=pathlib.Path(__file__).resolve().parent
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,value):p.write_text(json.dumps(value,indent=2)+'\n')
assert not (HERE/'seal.json').exists()
results=json.loads((HERE/'results.json').read_text())
assert len(results['configurations'])==4
for unit in [False,True]:
    contexts=[v for v in results['configurations'] if v['configuration'].startswith('unit-' if unit else 'production-')]
    assert len(contexts)==2 and contexts[0]['layouts']==contexts[1]['layouts']
assert results['negative_direct_guard']==[dict(mode='debug',errors=['E0502']),dict(mode='optimized',errors=['E0502'])]
assert results['post_construction_healthy_cleanup_qualified'] is False
assert results['full_conditional_admission_implemented'] is False
commands=[]
for p in sorted((HERE/'commands').glob('*/receipt.json')):
    r=json.loads(p.read_text());folder=p.parent
    assert digest(folder/'stdout')==r['stdout_sha256'] and digest(folder/'stderr')==r['stderr_sha256']
    negative=folder.name.startswith('negative-')
    assert (r['exit_code']!=0) if negative else (r['exit_code']==0)
    commands.append(dict(name=folder.name,receipt_sha256=digest(p),exit_code=r['exit_code']))
assert len(commands)==13,len(commands)
cleanup=json.loads((HERE/'cleanup.json').read_text())
assert cleanup['owned_scratch_removed'] and cleanup['all_children_reaped']
manifest=HERE/'compile-source-manifest.json'
source=json.loads(manifest.read_text())
assert len(source['members'])==144
# Canonical definition of the recorded compiler-source digest: UTF-8 lines of
# relative path, NUL, decimal bytes, NUL, lowercase content hash, then newline.
tree_bytes=''.join(f"{m['path']}\0{m['bytes']}\0{m['sha256']}\n" for m in source['members']).encode()
revision=(HERE/'commands/source-revision/stdout').read_text().strip()
dump(HERE/'receipt.json',dict(schema=1,status='ready-for-fresh-independent-design-source-proof-review',
    exact_runner_command='python3 -B verification/swift-guarded-snapshot-export-admission-correction/run_correction.py',
    source_revision_context=revision,accepted_source_tree='9fbdabbc5122f71809483b3b0a0e95a71b9813def61572f366bcebc8ac6d08fb',
    compiler_source_manifest_sha256=digest(manifest),compiler_source_tree_sha256=hashlib.sha256(tree_bytes).hexdigest(),
    compiler_source_tree_digest_format='path NUL decimal-bytes NUL sha256 newline in manifest order',
    runner_sha256=digest(HERE/'run_correction.py'),commands=commands,
    command_count=13,positive_compile_configurations=4,expected_negative_compilations=2,
    host_methods_per_unit_mode=4,host_boundary_cases_per_unit_mode=8,
    initial_new_probe_failures=0,original_findings_preserved_in_immutable_review=True,
    f1='conservative charge and cleanup invariant retained; healthy post-Construction cleanup unqualified',
    f2='sum ownership and sole original guard shared reborrow typechecked; wrapper not executed',
    scope='Rust1.99.0 aarch64 Apple host source/signature probes only',
    operational_admission=False,full_writer=False,canonical_changes=False,git_changes=False,
    native_runtime_ui_capture_process_inventory=False,independent_review_required=True))
members=[]
for p in sorted(HERE.rglob('*')):
    assert not p.is_symlink(),p
    if p.is_file() and p.name!='seal.json':members.append(dict(path=str(p.relative_to(HERE)),bytes=p.stat().st_size,sha256=digest(p)))
tree=''.join(f"{m['path']}\0{m['bytes']}\0{m['sha256']}\n" for m in members).encode()
seal=dict(schema=1,member_count=len(members),bytes=sum(m['bytes'] for m in members),members=members,
    tree_sha256=hashlib.sha256(tree).hexdigest(),tree_digest_format='path NUL decimal-bytes NUL sha256 newline in roster order',
    scope='F1/F2 bounded admission design/source-proof correction; conservative retained-charge limit; no integrated admission')
dump(HERE/'seal.json',seal)
print(json.dumps(dict(member_count=seal['member_count'],bytes=seal['bytes'],tree_sha256=seal['tree_sha256'],seal_sha256=digest(HERE/'seal.json')),indent=2))
