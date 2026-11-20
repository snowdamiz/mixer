"""Replay hosted v68 source admission and restoration from a local candidate commit."""

import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import stat
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

PUBLIC_V67 = '1bf567bd70b34237d1bf98b6e0a6e5b6c06df23d'
PUBLIC_V66 = 'b963585ef2f5089dae67b3bcd30a3cdec3f358b5'
ANCHOR = '29aeb8069f1b7e85cb221bbc6e2713354cc32f9e'
ARCHIVE = 'verification/native-report-source141-archive-v1'
VERIFY = '.github/workflows/verify.yml'
WORKFLOW_PREIMAGE = f'{ARCHIVE}/hosted-v68-predecessor-bytes/{VERIFY}'
RUNNER = 'hosted/scripts/test-identity-network.py'
COLLECTOR_TEST = 'hosted/scripts/test_identity_network_collector.py'
MANIFEST = 'selected-source-manifest.json'
CONTROL_INPUTS = {
    'hosted/scripts/check-configured-startup.exs',
    'hosted/scripts/check-provider-trust-config.exs',
    'hosted/scripts/check-startup-secrets.exs',
}
PROJECTS = {
    'phoenix': 'hosted',
    'identity-network': 'identity-network',
    'services': 'verify',
    'swift-host': 'verify',
    'android-generated-java': 'verify',
}
ENV = dict(os.environ, GIT_NO_LAZY_FETCH='1', GIT_CONFIG_NOSYSTEM='1',
           GIT_CONFIG_GLOBAL=os.devnull, GIT_ATTR_NOSYSTEM='1')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def run(cwd, command, *, data=None, expected_error=None, tmp=None):
    env = ENV if tmp is None else dict(ENV, TMPDIR=str(tmp))
    result = subprocess.run(command, cwd=cwd, input=data, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, env=env, timeout=60, check=False)
    if expected_error is None:
        require(result.returncode == 0, f'{command}: {result.returncode}\n{result.stderr.decode()}')
    else:
        require(result.returncode != 0 and expected_error.encode() in result.stderr,
                f'{command} did not refuse {expected_error}: {result.stderr.decode()}')
    return result.stdout


def git(cwd, *args, data=None):
    return run(cwd, ['git', '--no-replace-objects', *args], data=data)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def blob(root, ref, name):
    return git(root, 'show', f'{ref}:{name}')


def version_path(version):
    return f'verification/identity-network-current-source-v{version}'


def manifest(root, ref, version):
    return json.loads(blob(root, ref, f'{version_path(version)}/{MANIFEST}'))


def tree(root, ref):
    entries = {}
    for item in git(root, 'ls-tree', '-rz', ref).split(b'\0')[:-1]:
        header, path = item.decode().split('\t', 1)
        mode, kind, oid = header.split()
        entries[path] = mode, kind, oid
    return entries


def disk_entry(path):
    mode = path.lstat().st_mode
    require(stat.S_ISREG(mode) and stat.S_IMODE(mode) in (0o644, 0o755),
            f'Unexpected mode for {path}')
    body = path.read_bytes()
    oid = hashlib.sha1(f'blob {len(body)}\0'.encode() + body).hexdigest()
    return f'{mode:o}', 'blob', oid


def inventory(rows):
    return sha(''.join(f'{path}\0{mode}\0{oid}\n'
                       for path, (mode, _, oid) in sorted(rows.items())).encode())


def sparse_rules(raw, job):
    lines = raw.decode().split(f'\n  {job}:\n', 1)[1].splitlines()
    end = next((i for i, line in enumerate(lines) if line.startswith('  ') and line[2:].strip()
                and not line.startswith('   ')), len(lines))
    job_lines = lines[:end]
    start = job_lines.index('          sparse-checkout: |')
    require(job_lines.count('          sparse-checkout: |') == 1 and
            '          sparse-checkout-cone-mode: false' in job_lines[:start],
            f'{job}: expected one non-cone checkout')
    patterns = []
    for line in job_lines[start + 1:]:
        if not line.startswith('            '):
            break
        patterns.append(line.strip())
    require(patterns and all(pattern.startswith(('/', '!/')) for pattern in patterns), f'{job}: sparse rules differ')
    return ('\n'.join(patterns) + '\n').encode()


def compare_disk(root, expected):
    observed = {path.relative_to(root).as_posix(): disk_entry(path)
                for path in root.rglob('*') if path.is_symlink() or path.is_file()}
    require(observed == expected, f'{root.name}: disk inventory, bytes or modes differ')
    return inventory(observed)


def check_projection(root, scratch, binding, entries, objects, job, workflow, versions):
    work = scratch / job
    git(scratch, 'init', '-q', str(work))
    (work / '.git/objects/info/alternates').write_text(str(objects) + '\n')
    for key, value in {'core.hooksPath': os.devnull, 'core.autocrlf': 'false', 'core.filemode': 'true'}.items():
        git(work, 'config', key, value)
    rules = sparse_rules(blob(root, binding, f'.github/workflows/{workflow}.yml'), job)
    git(work, 'sparse-checkout', 'set', '--no-cone', '--stdin', data=rules)
    git(work, 'checkout', '-q', '--detach', binding)
    selection = git(work, 'sparse-checkout', 'check-rules', '-z',
                    data=b''.join(path.encode() + b'\0' for path in entries))
    expected = {path.decode(): entries[path.decode()] for path in selection.split(b'\0')[:-1]}
    active_index = {row[2:].decode() for row in git(work, 'ls-files', '-tz').split(b'\0') if row.startswith(b'H ')}
    require(active_index == expected.keys(), f'{job}: sparse index differs from workflow selection')
    disk = {path: disk_entry(work / path) for path in active_index}
    require(disk == expected, f'{job}: checkout bytes or file modes differ')
    output = {'rules': len(rules.splitlines()), 'rules_sha256': sha(rules), 'files': len(disk),
              'path_mode_blob_sha256': inventory(disk), 'runs': {}}
    tmp = scratch / (job + '-tmp')
    tmp.mkdir()
    for mode, flags in (('normal', []), ('optimized', ['-O'])):
        if job in ('swift-host', 'android-generated-java'):
            result = check_archive(work, tmp, flags)
        else:
            command = ['python3', '-B', *flags, RUNNER, '--check-source']
            raw = run(work, command, tmp=tmp)
            result = {'command': command, 'exit': 0, 'stdout_sha256': sha(raw)}
            value = json.loads(raw)
            current_selection = (work / version_path(68) / 'selection.json').read_bytes()
            selected = json.loads(current_selection)
            require(value == {'identity': selected['identity'], 'source_count': 483,
                              'source_digest_sha256': selected['selected']['source_digest_sha256'],
                              'selection_sha256': sha(current_selection), 'runtime_or_GA_accepted': False},
                    'Selected source admission output differs')
            if job == 'phoenix':
                result['round_trip'] = check_round_trip(work, tmp, versions)
                result['refusal_controls'] = check_source_refusals(work, tmp, command)
        require(not any(tmp.iterdir()), f'{job}: temporary files remain after {mode}')
        output['runs'][mode] = result
    require(not git(work, 'status', '--porcelain=v1', '--untracked-files=all'), f'{job}: checkout mutated')
    return output


def check_round_trip(work, tmp, versions):
    restore = tmp / 'hosted-restore'
    for name in versions[68]:
        target = restore / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(work / name, target)
    round_trip = {'68': compare_disk(restore, versions[68])}
    for version in (68, 67):
        folder = work / version_path(version)
        changes = json.loads((folder / 'selection.json').read_bytes())['exact_delta']
        for name, change in changes.items():
            target = restore / name
            if change['before'] is None:
                target.unlink()
            else:
                shutil.copy2(folder / 'preimages' / name, target)
        round_trip[f'{version}->{version - 1}'] = compare_disk(restore, versions[version - 1])
    for version in (67, 68):
        for name in versions[version].keys() - versions[version - 1].keys():
            target = restore / name
            target.parent.mkdir(parents=True, exist_ok=True)
        for name in json.loads((work / version_path(version) / 'selection.json').read_bytes())['exact_delta']:
            shutil.copy2(work / name, restore / name)
        round_trip[f'{version - 1}->{version}'] = compare_disk(restore, versions[version])
    shutil.rmtree(restore)
    return round_trip


def check_source_refusals(work, tmp, command):
    script = sorted(CONTROL_INPUTS)[0]
    path = work / script
    original = path.read_bytes()
    preimage = work / version_path(68) / 'preimages' / script
    cases = [
        (path, preimage.read_bytes(), None, 'workspace source digest'),
        (preimage, original, None, 'workspace source preimages differ'),
        (preimage, None, 0o755, 'workspace source file mode differs'),
    ]
    for target, replacement, mode, message in cases:
        raw = target.read_bytes()
        try:
            if mode is None:
                target.write_bytes(replacement)
            else:
                target.chmod(mode)
            run(work, command, expected_error=message, tmp=tmp)
        finally:
            target.write_bytes(raw)
            target.chmod(0o644)
    return [message for _, _, _, message in cases]


def check_archive(work, tmp, flags):
    python = ['python3', '-I', '-B', '-S', *flags]
    adopt = [*python, f'{ARCHIVE}/adopt_archive.py']
    verify = [*adopt, 'verify', '--workflow-installed']
    result = {'command': verify, 'exit': 0, 'stdout_sha256': sha(run(work, verify, tmp=tmp)), 'restored': {}}
    for label, prepare, authority in (
        ('141', 'prepare-source141', 'sdk-feature-ui-source141-v1/adopt_sdk.py'),
        ('127', 'prepare-predecessor', 'native-report-source127-v1/adopt_envelope.py'),
    ):
        destination = tmp / ('source' + label)
        run(work, [*adopt, prepare, '--out', str(destination)], tmp=tmp)
        admitted = run(destination, [*python, f'verification/{authority}', 'verify', '--workflow-installed'], tmp=tmp)
        disk = {path.relative_to(destination).as_posix(): disk_entry(path)
                for path in destination.rglob('*') if path.is_symlink() or path.is_file()}
        result['restored'][label] = {'files': len(disk), 'path_mode_blob_sha256': inventory(disk),
                                     'admission_sha256': sha(admitted), 'verify_workflow': disk[VERIFY][2]}
        shutil.rmtree(destination)
    return result


def main():
    os.umask(0o022)
    root = Path(git(Path.cwd(), 'rev-parse', '--show-toplevel').decode().strip()).resolve()
    candidate = git(root, 'rev-parse', '--verify', sys.argv[1] + '^{commit}').decode().strip()
    require(git(root, 'rev-parse', ANCHOR + '^').decode().strip() == PUBLIC_V67, 'Anchor parent differs')
    entries = tree(root, candidate)
    anchor = tree(root, ANCHOR)
    old = tree(root, PUBLIC_V67)
    restore_66 = tree(root, PUBLIC_V66)
    require({path for path in set(old) | set(anchor) if old.get(path) != anchor.get(path)} == CONTROL_INPUTS,
            'Product commit changes more than the standalone startup inputs')
    for path in CONTROL_INPUTS:
        require(anchor[path][0] == old[path][0] == '100644' and
                entries[f'{version_path(68)}/preimages/{path}'] == old[path], f'Preimage differs: {path}')
    require(entries[WORKFLOW_PREIMAGE] == old[VERIFY], 'Verify workflow preimage differs')
    for path in old:
        is_history = path.startswith((version_path(66) + '/', version_path(67) + '/'))
        is_archive_preimage = path.startswith(ARCHIVE + '/') and '-predecessor-bytes/' in path
        if is_history or is_archive_preimage or path == COLLECTOR_TEST:
            require(entries[path] == old[path], f'Predecessor authority or separately owned collector changed: {path}')
    versions = {version: {path: rows[path] for path in manifest(root, ref, version)}
                for version, rows, ref in ((68, entries, candidate), (67, old, PUBLIC_V67),
                                           (66, restore_66, PUBLIC_V66))}
    require(versions[68].keys() == versions[67].keys() and
            {path for path in versions[68] if versions[68][path] != versions[67][path]} == CONTROL_INPUTS and
            all(anchor[path] == entry for path, entry in versions[68].items()), 'Selected source differs from anchor')
    objects = (root / git(root, 'rev-parse', '--git-path', 'objects').decode().strip()).resolve()
    parent = root / 'verification/local'
    parent.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='hosted-v68-replay-', dir=parent) as name:
        scratch = Path(name)
        with ThreadPoolExecutor(max_workers=len(PROJECTS)) as executor:
            jobs = {job: executor.submit(check_projection, root, scratch, candidate, entries, objects,
                                        job, workflow, versions) for job, workflow in PROJECTS.items()}
            projections = {job: result.result() for job, result in jobs.items()}
    require(not scratch.exists(), 'Owned projections remain')
    for job, projection in projections.items():
        normal, optimized = (projection['runs'][mode] for mode in ('normal', 'optimized'))
        require({key: value for key, value in normal.items() if key != 'command'} ==
                {key: value for key, value in optimized.items() if key != 'command'}, f'{job}: Python modes differ')
    prior_archive = json.loads(blob(root, PUBLIC_V67,
        'verification/receipts/hosted-source-binding-v67-0f191753.json'))['projections']
    for job in ('swift-host', 'android-generated-java'):
        verified = projections[job]['runs']['normal']
        prior = prior_archive[job]['python']['normal']
        require(verified['stdout_sha256'] == prior['stdout_sha256'] and
                all(verified['restored'][label]['admission_sha256'] == prior['restoration'][label]['admission_sha256']
                    for label in ('141', '127')), f'{job}: historical archive admission differs from v67 evidence')
    print(json.dumps({
        'binding_commit': candidate, 'binding_tree': git(root, 'rev-parse', candidate + '^{tree}').decode().strip(),
        'public_v67': PUBLIC_V67, 'public_v66': PUBLIC_V66, 'product_anchor': ANCHOR,
        'changed_controls': sorted(CONTROL_INPUTS), 'verify_workflow_preimage': entries[WORKFLOW_PREIMAGE][2],
        'selection_sha256': sha(blob(root, candidate, f'{version_path(68)}/selection.json')),
        'manifest_sha256': sha(blob(root, candidate, f'{version_path(68)}/{MANIFEST}')),
        'git': git(root, '--version').decode().strip(), 'python': platform.python_version(),
        'platform': platform.platform(), 'projections': projections,
        'cleanup': 'owned sparse projections and restoration scratch removed',
    }, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
