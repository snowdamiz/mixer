"""Create the isolated source144 constants-only funding candidate once."""
from pathlib import Path
import difflib
import hashlib
import json
import shutil

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / 'swift-guarded-snapshot-scope-authority-correction'
RECIPE = HERE.parent / 'swift-guarded-snapshot-owner-storage-alias-correction'
AUTHORITY_SEAL = '351caf4860621989119d16b474dbb53c496a688c4efb0cbb3abb918825b79e6c'
AUTHORITY_TREE = '575b55d3391729749039dc2badccc9107449cb2c9a021d8ef67282c39b2e1896'
RECIPE_SEAL = 'cd6e7596559b604a0915353c694526ba02d6fd05d4ad2baddf92a4f3bea523ee'
CONTROL = 'src/experimental_swift_reactor/control.rs'
PROFILE = 'src/experimental_swift_reactor/cache/initial_profile_v1.rs'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()

def members(root):
    return [dict(path=p.relative_to(root).as_posix(), bytes=p.stat().st_size,
                 sha256=sha(p.read_bytes())) for p in sorted(root.rglob('*')) if p.is_file()]

def write(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')

def verify_seal(root, expected):
    seal_path = root / 'seal.json'
    assert sha(seal_path.read_bytes()) == expected
    seal = json.loads(seal_path.read_text())
    for row in seal['members']:
        path = root / row['path']
        assert path.stat().st_size == row['bytes'] and sha(path.read_bytes()) == row['sha256'], row['path']
    return dict(path=str(seal_path), sha256=expected, members=len(seal['members']))

FUNDING_CONSTANTS = '''// Exact logical source-place recipe bound to the separately frozen owner
// correction. Every addition is const-evaluated; no runtime helper, local,
// iterable, allocation or second foundation is introduced by this recipe.
const COMMON_ADOPTION_SOURCE_EXTRA_BYTES_V1: usize = 78_240;
const SELECTED_SNAPSHOT_SOURCE_EXTRA_BYTES_V1: usize = 941_467;
pub(super) const SNAPSHOT_ADMITTED_SOURCE_EXTRA_BYTES_V1: usize = 430_175;
#[cfg(test)]
const SNAPSHOT_HOST_CALLER_SOURCE_EXTRA_BYTES_V1: usize = 81_327;
const COMMON_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    match FOUNDATION_CONSTRUCTION_BYTES {
        Some(original) => original.checked_add(COMMON_ADOPTION_SOURCE_EXTRA_BYTES_V1),
        None => None,
    };
const SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    match COMMON_FOUNDATION_CONSTRUCTION_BYTES_V1 {
        Some(common) => common.checked_add(SELECTED_SNAPSHOT_SOURCE_EXTRA_BYTES_V1),
        None => None,
    };
#[cfg(not(test))]
const SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1;
#[cfg(test)]
const SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1: Option<usize> =
    match SNAPSHOT_SELECTED_FOUNDATION_CONSTRUCTION_BYTES_V1 {
        Some(selected) => selected.checked_add(SNAPSHOT_HOST_CALLER_SOURCE_EXTRA_BYTES_V1),
        None => None,
    };
// cfg(test) conservatively reserves the concrete future caller's H at selected
// Construction admission. This does not prove ownership/funding of arguments
// already live before ingress or of the independent external test harness.
'''

def main():
    assert not (HERE / 'seal.json').exists()
    authority = verify_seal(BASE, AUTHORITY_SEAL)
    recipe = verify_seal(RECIPE, RECIPE_SEAL)
    before = members(BASE / 'source/vm')
    assert len(before) == 144 and sha(canonical(before)) == AUTHORITY_TREE
    formula = json.loads((RECIPE / 'formula.json').read_text())
    assert [formula[k] for k in ['common_extra', 'selected_unconditional_extra',
                                'admitted_only_extra', 'host_caller_extra']] == [78240, 941467, 430175, 81327]
    target = HERE / 'source/vm'
    assert not target.exists()
    shutil.copytree(BASE / 'source/vm', target)
    changes = []

    def change(name, old, new, reason):
        path = target / name
        text = path.read_text()
        assert text.count(old) == 1, (name, old)
        path.write_text(text.replace(old, new))
        changes.append(dict(path=name, old=old, new=new, reason=reason))

    old = '''/// Conservative named-object foundation envelope. Composition enlarges this
/// same ticket before creating additional wrappers. This is not physical stack/RSS.
pub(crate) fn foundation_construction_bytes() -> Option<usize> {
    FOUNDATION_CONSTRUCTION_BYTES
}'''
    new = FUNDING_CONSTANTS + '''
/// Common named-source foundation: the unchanged Original F0 plus C once.
/// Composition enlarges the same ticket; this is not physical stack/RSS.
pub(crate) fn foundation_construction_bytes() -> Option<usize> {
    COMMON_FOUNDATION_CONSTRUCTION_BYTES_V1
}'''
    change(CONTROL, old, new, 'Fund shared common source roles from F0+C at sole initial Construction admission.')
    old = '''fn snapshot_scope_candidate_foundation_v1()->Option<usize>{
    // Original common-core funding is separately pending selection. These are
    // intentionally conservative additional named source roles, not RSS.
    foundation_construction_bytes()?.checked_add(size_of::<CommonAdoptionPlacesV1>())?
        .checked_add(size_of::<SnapshotScopePlacesV1>())?
        .checked_add(super::cache::SNAPSHOT_FOUNDATION_PLACES_V1)
}'''
    new = '''fn snapshot_scope_candidate_foundation_v1()->Option<usize>{
    // Exact selected source recipe, with no placeholder type aggregates.
    // The original selected-finalizer conservative charge remains unchanged.
    SNAPSHOT_SCOPE_FOUNDATION_CONSTRUCTION_BYTES_V1
}'''
    change(CONTROL, old, new, 'Copy const Fcommon+S, plus conservative cfg(test) H; retain old removed-role charge.')
    old = 'const SNAPSHOT_PHASE_PLACES_V1:usize=size_of::<SnapshotPhasePlacesV1<\'static>>();'
    new = 'const SNAPSHOT_PHASE_PLACES_V1:usize=super::super::control::SNAPSHOT_ADMITTED_SOURCE_EXTRA_BYTES_V1;'
    change(PROFILE, old, new, 'Preflight and same-ticket conditional commit use exact A, without adding the placeholder inventory.')
    after = members(target)
    assert len(after) == 144
    changed_names = sorted({row['path'] for row in changes})
    patch = []
    for name in changed_names:
        patch.extend(difflib.unified_diff((BASE / 'source/vm' / name).read_text().splitlines(True),
                     (target / name).read_text().splitlines(True),
                     fromfile='authority144/' + name, tofile='funding144/' + name))
    (HERE / 'source-delta.patch').write_text(''.join(patch))
    (HERE / 'funding-constants.inc.rs').write_text(FUNDING_CONSTANTS)
    write('source-manifest.json', dict(schema=1, members=after, source_tree_sha256=sha(canonical(after))))
    write('preparation.json', dict(schema=1, authority=authority, recipe=recipe,
        baseline_source_tree_sha256=AUTHORITY_TREE, source_members=144,
        candidate_source_tree_sha256=sha(canonical(after)), changed_files=changed_names,
        exact_replacements=changes, source_binding='immutable authority source144, not mutable Git checkout',
        root_coordination=dict(approach='constants-only; conservative cfg(test) H; preserve selected completion',
            approval='Parent root explicitly approved source preparation and metadata/pure arithmetic controls.'),
        recipe_status='provisional until independent owner correction acceptance is supplied by root',
        runtime_selected=False, engine_or_writer_executed=False, canonical_changed=False,
        outstanding=['cfg(test) H at selected Construction admission does not prove pre-ingress host ownership',
            'Preserved admitted-A completion narrowing needs independent survivor/lifetime review before writer release',
            'WorkAuditPending remains; no writer/delegation/delivery release']))
    print(json.dumps(dict(source_members=144, changed_files=changed_names,
                         source_tree_sha256=sha(canonical(after))), sort_keys=True))

if __name__ == '__main__':
    main()
