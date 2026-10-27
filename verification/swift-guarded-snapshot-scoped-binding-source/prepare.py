#!/usr/bin/env python3
"""Reproduce a lifetime-only 146-member candidate from explicit frozen custody."""
import difflib
import hashlib
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRODUCER = ROOT/'verification/swift-guarded-snapshot-outer-parent-source'
INDEPENDENT = ROOT/'verification/swift-guarded-snapshot-outer-parent-independent'
STORAGE = ROOT/'verification/swift-guarded-snapshot-outer-parent-work-storage'
PROFILE = 'src/experimental_swift_reactor/cache/initial_profile_v1.rs'
ACCOUNT = 'src/experimental_swift_reactor/cache/initial_profile_v1/host_account_v1.rs'
ACCEPTED_TREE = '27deefde4b492bab2e2d5a28da9ae749cc4ae51094e0fca30154d044097988a3'
ACCEPTED_PROFILE = 'b19bca0a2f5ad193fc782061a2f345bd75b9414408643823b8f7691c89bc150f'

def sha(data): return hashlib.sha256(data).hexdigest()
def canonical(obj): return json.dumps(obj, sort_keys=True, separators=(',', ':')).encode()
def row(name, data): return dict(path=name, bytes=len(data), sha256=sha(data))
def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True)+'\n')
def manifest(source):
    members = [row(n, source[n]) for n in sorted(source, key=Path)]
    return dict(schema=1, member_count=len(members), members=members, tree_sha256=sha(canonical(members)))

def accepted_source():
    custody = json.loads((PRODUCER/'source-custody.json').read_bytes())
    expected = json.loads((PRODUCER/'source-manifest.json').read_bytes())
    assert len(custody) == len(expected['members']) == 146
    assert len({x['path'] for x in custody}) == 146
    source, effective = {}, []
    for member in custody:
        name = member['path']
        origin = ROOT/member['origin']
        if name == PROFILE:
            origin = PRODUCER/'overlay/vm'/PROFILE
        data = origin.read_bytes()
        expected_row = next(x for x in expected['members'] if x['path'] == name)
        assert row(name, data) == expected_row, name
        if name != PROFILE:
            assert row(name, data) == {k:member[k] for k in ['path','bytes','sha256']}
        source[name] = data
        effective.append(dict(row(name,data), origin=str(origin.relative_to(ROOT))))
    assert manifest(source) == expected
    assert expected['tree_sha256'] == ACCEPTED_TREE
    assert sha(source[PROFILE]) == ACCEPTED_PROFILE
    return source, effective

def transform(data):
    text = data.decode()
    edits = []
    replacements = [
        ('struct ReviewedFixtureBindingV1 {', "struct ReviewedFixtureBindingV1<'p0> {"),
        ("paths: [&'static Path; 5],", "paths: [&'p0 Path; 5],"),
        ("struct FrozenFixtureV1 { binding: &'static ReviewedFixtureBindingV1 }", "struct FrozenFixtureV1<'p0> { binding: &'p0 ReviewedFixtureBindingV1<'p0> }"),
        ("fixture: FrozenFixtureV1)", "fixture: FrozenFixtureV1<'_>)"),
        ('binding: &ReviewedFixtureBindingV1) -> SetupOutcomeV1', "binding: &ReviewedFixtureBindingV1<'_>) -> SetupOutcomeV1"),
        ('struct ImmutableIdentityPreimageV1 {', "struct ImmutableIdentityPreimageV1<'p0> {"),
        ("bytes: &'static [u8],", "bytes: &'p0 [u8],"),
        ('struct ImmutableFixtureIdentitiesV1 {', "struct ImmutableFixtureIdentitiesV1<'p0> {"),
        ('struct PreexistingImmutableBindingV1 {', "struct PreexistingImmutableBindingV1<'p0> {"),
        ('binding: ReviewedFixtureBindingV1,', "binding: ReviewedFixtureBindingV1<'p0>,"),
        ("native_path_bodies: [&'static [u8]; 5],", "native_path_bodies: [&'p0 [u8]; 5],"),
        ('identities: ImmutableFixtureIdentitiesV1,', "identities: ImmutableFixtureIdentitiesV1<'p0>,"),
        ('struct OneFixtureOuterRequestV1 {', "struct OneFixtureOuterRequestV1<'p0> {"),
        ("preexisting: &'static PreexistingImmutableBindingV1,", "preexisting: &'p0 PreexistingImmutableBindingV1<'p0>,"),
        ('fn selected_outer_request_v1()\n        -> Result<OneFixtureOuterRequestV1, BindingSelectionRefusalV1>', "fn selected_outer_request_v1<'p0>()\n        -> Result<OneFixtureOuterRequestV1<'p0>, BindingSelectionRefusalV1>"),
        ('request: OneFixtureOuterRequestV1) -> OuterResultV1', "request: OneFixtureOuterRequestV1<'_>) -> OuterResultV1"),
        ("// backing reachable through identities/claims. 'static is a lifetime only;\n    // it neither prices backing nor grants fixture/root authority. The five", "// backing reachable through identities/claims. Its owner outlives the entire\n    // consuming call and result; this neither prices backing nor grants fixture/root\n    // authority. The five"),
    ]
    for old,new in replacements:
        count = text.count(old)
        expected = 2 if old == 'fixture: FrozenFixtureV1)' else 1
        assert count == expected, (old, count, expected)
        text = text.replace(old,new)
        edits.append(dict(before=old, after=new, occurrences=count))
    old=': ImmutableIdentityPreimageV1,'
    assert text.count(old) == 12
    text=text.replace(old, ": ImmutableIdentityPreimageV1<'p0>,")
    edits.append(dict(before=old,after=": ImmutableIdentityPreimageV1<'p0>,",occurrences=12))
    return text.encode(), edits

POSITIVE = b'''// Inert metadata/MIR probe only. Never selected or called.
fn scoped_local_binding_compiles_v1<'p0>(
    preexisting: PreexistingImmutableBindingV1<'p0>,
) -> OuterResultV1 {
    let request = OneFixtureOuterRequestV1 { preexisting: &preexisting };
    consume_outer_request_v1(request)
}
'''
NEGATIVE = b'''// Combined inert production metadata-only rejected ownership probes.
fn reject_escaping_request_v1<'p0>(
    preexisting: PreexistingImmutableBindingV1<'p0>,
) -> OneFixtureOuterRequestV1<'p0> {
    OneFixtureOuterRequestV1 { preexisting: &preexisting }
}
fn reject_stack_identity_static_v1() -> ImmutableIdentityPreimageV1<'static> {
    let bytes = [0u8; 4];
    ImmutableIdentityPreimageV1 { bytes: &bytes, sha256: [0; 32] }
}
fn reject_mutation_live_identity_v1(bytes: &mut [u8]) {
    let identity = ImmutableIdentityPreimageV1 { bytes, sha256: [0; 32] };
    bytes[0] = 1;
    std::hint::black_box(identity.bytes);
}
fn reject_drop_live_identity_v1(bytes: Vec<u8>) {
    let identity = ImmutableIdentityPreimageV1 { bytes: &bytes, sha256: [0; 32] };
    drop(bytes);
    std::hint::black_box(identity.bytes);
}
fn reject_double_consume_request_v1(request: OneFixtureOuterRequestV1<'_>) {
    consume_outer_request_v1(request);
    consume_outer_request_v1(request);
}
'''

def query_source(source, mode):
    source=dict(source)
    assert source[PROFILE].endswith(b'\n}\n}\n')
    suffix = (HERE/'query-layout.inc.rs').read_bytes()
    suffix += b'\n'+(HERE/'query-result-layout.inc.rs').read_bytes()
    suffix += b'\n'+(HERE/('positive.inc.rs' if mode=='positive' else 'negative.inc.rs')).read_bytes()
    source[PROFILE] = source[PROFILE][:-4]+b'\n'+suffix+b'}\n}\n'
    source[ACCOUNT] += b'\n'+(HERE/'query-account-layout.inc.rs').read_bytes()
    return source

def main():
    assert sys.argv[1:] == ['--prepare']
    assert not (HERE/'source').exists(), 'Never replace prepared sources'
    source,custody=accepted_source()
    before=source[PROFILE]
    source[PROFILE], edits=transform(before)
    assert source[PROFILE].endswith(b'\n}\n}\n')
    for name,data in source.items():
        path=HERE/'source/vm'/name
        path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(data)
    write(HERE/'accepted-source-custody.json',custody)
    write(HERE/'accepted-source-manifest.json',manifest(dict(source,**{PROFILE:before})))
    write(HERE/'source-manifest.json',manifest(source))
    write(HERE/'exact-edits.json',edits)
    (HERE/'source-delta.patch').write_text(''.join(difflib.unified_diff(before.decode().splitlines(True),source[PROFILE].decode().splitlines(True),fromfile='accepted/'+PROFILE,tofile='candidate/'+PROFILE)))
    for name in ['query-layout.inc.rs','query-account-layout.inc.rs']:
        (HERE/name).write_bytes((INDEPENDENT/name).read_bytes())
    # The frozen work-storage tail intentionally used a wrong zero expected
    # array length to observe layout in an E0308 receipt. Here preserve the
    # same Result type expressions in an inert MIR-signature query instead.
    original=(STORAGE/'query-result-layout.inc.rs').read_bytes()
    (HERE/'accepted-result-layout.inc.rs').write_bytes(original)
    (HERE/'query-result-layout.inc.rs').write_bytes(b'''// Inert metadata/MIR signature for the two accepted Result observations.
fn scoped_result_layout_query_v1(
    _selection_result_size: [u8; std::mem::size_of::<Result<OneFixtureOuterRequestV1, BindingSelectionRefusalV1>>()],
    _selection_result_align: [u8; std::mem::align_of::<Result<OneFixtureOuterRequestV1, BindingSelectionRefusalV1>>()],
) {}
''')
    (HERE/'positive.inc.rs').write_bytes(POSITIVE)
    (HERE/'negative.inc.rs').write_bytes(NEGATIVE)
    for mode in ['positive','negative']:
        write(HERE/(mode+'-source-manifest.json'),manifest(query_source(source,mode)))
    print(json.dumps(dict(candidate_tree=manifest(source)['tree_sha256'],accepted_tree=ACCEPTED_TREE,members=len(source),changed_members=[PROFILE],runtime=False)))

if __name__=='__main__': main()
