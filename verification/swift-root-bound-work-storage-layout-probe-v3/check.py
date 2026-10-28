#!/usr/bin/env python3
"""Read-only preparation custody check. No child processes and no compiler."""
from pathlib import Path
import hashlib
import json
import sys
import time
from strict_json import loads

D = Path(__file__).resolve().parent
R = D.parents[1]
O = R / 'verification/swift-root-bound-work-storage-layout-probe'
V = R / 'verification/swift-root-bound-work-storage-layout-probe-v2'


def sha(raw): return hashlib.sha256(raw).hexdigest()
def canonical(obj): return json.dumps(obj, sort_keys=True, separators=(',', ':')).encode()
def require(value, why):
    if not value: raise ValueError(why)
def hash_file(path, deadline=None):
    require(path.is_file() and not path.is_symlink(), 'not a regular non-symlink file: ' + str(path))
    digest = hashlib.sha256(); total = 0
    with path.open('rb') as handle:
        while True:
            if deadline is not None: require(time.monotonic() < deadline, 'hash deadline')
            raw = handle.read(262144)
            if not raw: break
            digest.update(raw); total += len(raw)
    return {'bytes': total, 'sha256': digest.hexdigest()}
def pinned(row, base=R, deadline=None):
    path = Path(row['path']); path = path if path.is_absolute() else base / path
    require(hash_file(path, deadline) == {key: row[key] for key in ['bytes', 'sha256']}, 'pin mismatch: ' + str(path))
    return path
def tree(base, members, deadline=None):
    require(base.is_dir() and not base.is_symlink(), 'source directory absent/symlink')
    actual = []
    for path in base.rglob('*'):
        if deadline is not None: require(time.monotonic() < deadline, 'source inventory deadline')
        require(not path.is_symlink(), 'source symlink')
        if path.is_file(): actual.append(str(path.relative_to(base)))
    require(set(actual) == {row['path'] for row in members} and len(actual) == 146, 'source146 membership changed')
    for row in members: pinned(row, base, deadline)
def check(plan_sha=None, deadline=None, transient_build_allowed=False):
    raw = (D / 'plan.json').read_bytes()
    if plan_sha is not None: require(sha(raw) == plan_sha, 'root-selected plan changed')
    plan = loads(raw)
    require(plan['status'] == 'PREPARED_V3_FROZEN_AWAITING_ROOT_INTERNAL_COMPILER_RELEASE', 'wrong preparation state')
    pinned(plan['original_packet']['seal'], R, deadline)
    original_seal = loads((O / 'seal.json').read_text())
    require(len(original_seal['members']) == 173, 'original sealed membership changed')
    for item in original_seal['members']: pinned(item, O, deadline)
    expected_members = {row['path'] for row in original_seal['members']} | {'seal.json'}
    actual_members = set()
    for path in O.rglob('*'):
        if deadline is not None: require(time.monotonic() < deadline, 'original membership deadline')
        relative = path.relative_to(O)
        if relative.parts[0] == 'build' and transient_build_allowed:
            continue
        require(not path.is_symlink(), 'original packet symlink')
        if path.is_file(): actual_members.add(str(relative))
    require(actual_members == expected_members, 'original frozen membership changed outside released transient build destination')
    if not transient_build_allowed: require(not (O/'build').exists(), 'original transient build destination must be absent')
    pinned(plan['prior_v2_packet']['seal'], R, deadline)
    prior_seal = loads((V / 'seal.json').read_text())
    require(len(prior_seal['members']) == 16, 'prior v2 sealed membership changed')
    require(sha(canonical(prior_seal['members'])) == prior_seal['tree_sha256'], 'prior v2 seal tree')
    for item in prior_seal['members']: pinned(item, V, deadline)
    prior_actual = set()
    for path in V.rglob('*'):
        if deadline is not None: require(time.monotonic() < deadline, 'prior v2 inventory deadline')
        require(not path.is_symlink(), 'prior v2 symlink')
        if path.is_file(): prior_actual.add(str(path.relative_to(V)))
    require(prior_actual == {row['path'] for row in prior_seal['members']} | {'seal.json'}, 'prior v2 frozen membership changed')
    for item in plan['preaccess_frozen_seals']:
        seal_path = pinned(item, R, deadline)
        external_seal = loads(seal_path.read_text())
        require(sha(canonical(external_seal['members'])) == external_seal['tree_sha256'], 'preaccess seal tree')
        for member in external_seal['members']: pinned(member, seal_path.parent, deadline)
    require(plan['execution'] == {'compiler_started': False, 'runtime_started': False, 'version_commands_started': 0}, 'preparation invents execution')
    for item in plan['scripts']: pinned(item, D, deadline)
    for item in plan['inputs']: pinned(item, R, deadline)
    for key in ['toolchain_manifest', 'sdk_path_settings', 'delta']: pinned(plan[key], O, deadline)
    toolmanifest = loads((O / 'toolchain-manifest.json').read_text())
    require(sha(canonical(toolmanifest['members'])) == toolmanifest['tree_sha256'], 'toolchain manifest tree')
    for item in toolmanifest['members']: pinned(item, Path(toolmanifest['root']), deadline)
    pinned(plan['compiler'], R, deadline)
    pinned(plan['python']['tool'], R, deadline)
    require(sys.version == plan['python']['version'], 'Python version drift')
    sdk = loads((O / 'sdk-path-settings.json').read_text())
    require(str(Path(sdk['requested']).resolve()) == sdk['resolved'], 'SDK resolution changed')
    for item in sdk['settings']: pinned(item, R, deadline)
    original = plan['original_source']
    pinned(original['manifest'], O, deadline)
    require(sha(canonical(original['members'])) == original['tree_sha256'] == '91bab68a8aef4a7cbe300af0fca8145462e08dcaaef2631f42a0d2d55748bd8f', 'original tree')
    tree(Path(original['directory']), original['members'], deadline)
    diagnostic = plan['diagnostic_source']
    require(sha(canonical(diagnostic['members'])) == diagnostic['tree_sha256'], 'diagnostic tree')
    require(Path(plan['diagnostic_source_directory']) == O/'source/vm', 'diagnostic source directory differs')
    tree(O / 'source/vm', diagnostic['members'], deadline)
    require(loads((O / 'diagnostic-source-manifest.json').read_text()) == diagnostic, 'diagnostic manifest mismatch')
    old = {row['path']: row for row in original['members']}; new = {row['path']: row for row in diagnostic['members']}
    names = sorted(name for name in old if old[name] != new[name])
    require(names == ['src/experimental_swift_reactor/cache/initial_profile_v1.rs', 'src/experimental_swift_reactor/retained_profile_loader_v1.rs'], 'unexpected changed source file')
    loader, cache = names[1], names[0]
    before = {name: (Path(original['directory']) / name).read_bytes() for name in names}
    after = dict(before)
    for name, fragment, marker in [(loader, 'proposed-owner-layout-queries.inc.rs', b'    // OWNER_PROBE_INSERTION'),
                                    (cache, 'proposed-cache-layout-queries.inc.rs', b'    // Private outer caller candidate; all prior bodies remain exact.')]:
        require(after[name].count(marker) == 1, 'insertion anchor not unique')
        after[name] = after[name].replace(marker, (O / fragment).read_bytes() + b'\n' + marker)
    needle = b'        Ok(reservation.dispatch_v1(|| run_prepaid_admitted_fixture_v1(fixture, attempt, expected)))'
    require(after[cache].count(needle) == 1, 'closure replacement anchor not unique')
    after[cache] = after[cache].replace(needle, (O / 'proposed-actual-closure-layout-fragment.rs').read_bytes().rstrip(b'\n'))
    require(all(after[name] == (O / 'source/vm' / name).read_bytes() for name in names), 'not exact three-edit replay')
    proposal = loads((R / 'verification/swift-root-bound-work-storage-delta/layout-probe-proposal.json').read_text())
    require(plan['argv'] == proposal['argv'] and plan['cwd'] == proposal['cwd'] and plan['environment'] == proposal['environment'], 'argv/environment differs from accepted proposal')
    original_plan = loads((O/'plan.json').read_text())
    for field in ['argv','cwd','environment','original_source','diagnostic_source','diagnostics','bounds','compiler','python']:
        require(plan[field] == original_plan[field], 'v3 changed frozen source/query/tool/command/bounds field: ' + field)
    prior_plan = loads((V/'plan.json').read_text())
    for field in ['argv','cwd','environment','original_source','diagnostic_source','diagnostics','bounds','compiler','python','root_release_required']:
        require(plan[field] == prior_plan[field], 'v3 changed v2 source/query/tool/command/bounds field: ' + field)
    require(plan['execution_build_directory'] == str(O/'build'), 'v3 changed execution-owned exact build destination')
    require(len(plan['diagnostics']['named_queries']) == 28 and plan['diagnostics']['expected_primary_errors'] == {'E0308': 56, 'E0512': 2}, 'query cardinality')
    require(not plan['all_price_layout_backing_peak_funding_ownership_GA_authority'], 'invented authority')
    return plan


if __name__ == '__main__':
    started = time.monotonic(); plan = check(deadline=started + 20)
    print(json.dumps({'status': 'frozen-preparation-custody-passed', 'plan_sha256': sha((D / 'plan.json').read_bytes()),
                      'source146_original_and_diagnostic_verified': True, 'exact_edits': 3,
                      'compiler_runtime_children_started': 0, 'elapsed_seconds': time.monotonic()-started}))
