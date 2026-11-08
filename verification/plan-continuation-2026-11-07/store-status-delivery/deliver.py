"""Deliver the accepted store-status slice with compact evidence; preserve active lanes."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
ROOT = BASE.parent.parent
EXPECTED_HEAD = '62ce9b76840b2fa56306736fc4c4fe2962780adf'
DIGEST = 'eda43c6bb96bfeb15ab31731858c7388a7ba52329c8ba8e48ed52505bfe86158'
TRACKED = {'STATUS.md', 'README.md', 'AGENTS.md', 'verification/plan-continuation-2026-11-07/generated-java-ci-integration/test_sparse_checkout.py', 'cli/Sources/MixerCLI/main.swift', 'PLAN.md', 'work-graph.json', 'gates/ga.json', 'verification/plan-continuation-2026-11-07/native-resumption.json', 'verification/plan-continuation-2026-11-07/generated-java-ci-integration/bootstrap.py'}
EXTRA = ['cli/Sources/MixerBuild/AppStoreConnectBuildStatus.swift', 'cli/Sources/MixerBuild/StoreReconciliation.swift', 'cli/Tests/MixerBuildTests/StoreReconciliationTests.swift', 'docs/store-reviewer-information-template.md']
FINISHED = ['store-journal-integrity-fix', 'store-journal-integrity-review', 'store-journal-delivery', 'store-journal-root-integration', 'store-journal-six-consumers-review', 'store-reviewer-template', 'api28-root-observation', 'apple-adoption-recovery', 'root-continuation-0237', 'android-api32-33-image-install', 'api32-33-motion-package-review', 'pair9-api28-controller-fix-r3', 'pair9-api28-controller-review-r3', 'apple-window-identity-campaign/adoption-attempt-1']
TOP_ONLY = ['apple-safe-keyboard-root-runtime', 'apple-window-identity-review', 'apple-window-identity-campaign', 'apple-keyboard-readiness-campaign']
TOP_SELECTION = {'apple-window-recovery': ['inspect_once.py', 'inspect_ax.py', 'inspection-1/result.json'], 'api32-33-motion-package': ['REPORT.md', 'result.json', 'runtime-packet.json', 'frozen-ready-input-manifest.json', 'delivery-seal.json'], 'store-journal-six-consumers': ['receipt.json', 'commands/commands.json']}
ACCEPTANCES = ['store-journal-source-acceptance.json', 'store-journal-integrated-acceptance.json', 'api32-33-package-acceptance.json']
sys.path.insert(0, str(BASE / 'native-custody-premise'))
from cleanup_control import Commands


def require(value, message):
    if not value:
        raise ValueError(message)


def identity(path):
    require(path.is_file() and not path.is_symlink(), 'regular file required: ' + str(path))
    data = path.read_bytes()
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def evidence_files(directory):
    for base, dirs, files in os.walk(directory, followlinks=False):
        dirs[:] = [d for d in dirs if d not in {'scratch', 'temporary', 'input', '__pycache__'}]
        for name in files:
            path = Path(base) / name
            require(not path.is_symlink(), 'symlink evidence')
            yield path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    phase = 'delivery' if args.execute else 'selection'
    out = HERE / (phase + '-commands')
    out.mkdir(exist_ok=False)
    scratch = HERE / (phase + '-scratch')
    scratch.mkdir(exist_ok=False)
    commands = Commands(out, dict(os.environ, GIT_TERMINAL_PROMPT='0', PYTHONDONTWRITEBYTECODE='1'),
                        deadline=time.monotonic()+600)
    result = {'schema': 1, 'recordedAt': datetime.now(timezone.utc).isoformat(),
              'scope': 'Accepted store-status four-path integration, source103 bootstrap, documentation and compact evidence; active native implementations excluded',
              'expectedParent': EXPECTED_HEAD, 'gaPromoted': False, 'freshCIPending': True}

    def run(label, argv):
        return commands.run(label, argv, ROOT, 120)

    selection_path = HERE / 'selection.json'
    try:
        require(run('head', ['git', 'rev-parse', 'HEAD']) == EXPECTED_HEAD, 'parent changed')
        require(not run('index-before', ['git', 'diff', '--cached', '--name-only']), 'preselected index')
        dirty = set(run('tracked-before', ['git', 'diff', '--name-only']).splitlines())
        require(dirty == TRACKED, 'unexpected tracked edits')
        run('whitespace', ['git', 'diff', '--check'])
        spec = importlib.util.spec_from_file_location('inventory', ROOT / 'scripts/ci/check-android-generated-java.py')
        inventory = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(inventory)
        inputs = inventory.source_inputs(inventory.load_profile())
        require(len(inputs) == 103 and inventory.source_digest(inputs) == DIGEST, 'owning product drift')
        require(json.loads((BASE / 'store-journal-integrated-acceptance.json').read_text())['decision'] ==
                'ACCEPT_EXACT_STORE_STATUS_SOURCE103_JAVA_D8_INTEGRATION', 'store source/artifact acceptance')
        if not args.execute:
            paths = {ROOT / name for name in [*TRACKED, *EXTRA]}
            for directory in FINISHED:
                paths.update(evidence_files(BASE / directory))
            for directory in TOP_ONLY:
                paths.update(p for p in (BASE / directory).iterdir() if p.is_file() and not p.is_symlink())
            for directory, names in TOP_SELECTION.items():
                paths.update(BASE / directory / name for name in names)
            paths.update(BASE / name for name in ACCEPTANCES)
            paths.add(Path(__file__).resolve())
            candidates = sorted(str(p.relative_to(ROOT)) for p in paths)
            untracked = set(run('untracked-selection', ['git', 'ls-files', '--others', '--exclude-standard', '--', *candidates]).splitlines())
            selected = sorted(set(candidates) & (dirty | untracked))
            members = {name: identity(ROOT / name) for name in selected}
            require(all(x['bytes'] <= 10_000_000 for x in members.values()), 'large evidence member')
            total = sum(x['bytes'] for x in members.values())
            require(total <= 40_000_000, 'delivery size limit')
            data = dict(result, members=members, paths=len(members), bytes=total,
                        source103=DIGEST,
                        excluded=['active API28 identity correction/review', 'active API32/33 controller/review', 'active iOS isolation research',
                                  'native APKs/classfiles/libraries/system images', 'held scratch',
                                  'raw six-consumer classes/DEX/logs retained locally and hash-bound by review'])
            selection_path.write_text(json.dumps(data, indent=2)+'\n')
            result.update(status='PREPARED', paths=len(members), bytes=total)
            return
        data = json.loads(selection_path.read_text())
        members = data['members']
        for path, expected in members.items():
            require(identity(ROOT / path) == expected, 'selected drift: ' + path)
        require(run('remote-before', ['git', 'ls-remote', '--exit-code', 'origin', 'refs/heads/main']).split() ==
                [EXPECTED_HEAD, 'refs/heads/main'], 'remote changed')
        selected = sorted([*members, str(selection_path.relative_to(ROOT))])
        paths_file = scratch / 'paths.nul'
        paths_file.write_bytes(b'\0'.join(p.encode() for p in selected)+b'\0')
        run('stage', ['git', 'add', '--pathspec-from-file='+str(paths_file), '--pathspec-file-nul'])
        require(set(run('staged-paths', ['git', 'diff', '--cached', '--name-only']).splitlines()) == set(selected), 'staged paths')
        objects = run('staged-objects', ['git', 'ls-files', '--stage', '-z', '--', *selected])
        for row in objects.split('\0'):
            if not row:
                continue
            meta, name = row.split('\t', 1)
            mode, oid, stage = meta.split()
            body = (ROOT / name).read_bytes()
            expected = hashlib.sha1(b'blob '+str(len(body)).encode()+b'\0'+body).hexdigest()
            require(oid == expected and stage == '0' and mode in {'100644', '100755'}, 'staged identity')
        run('commit', ['git', 'commit', '-m', 'Add existing App Store build status reconciliation'])
        revision = run('committed-head', ['git', 'rev-parse', 'HEAD'])
        require(run('committed-parent', ['git', 'rev-parse', 'HEAD^']) == EXPECTED_HEAD, 'commit parent')
        require(set(run('committed-paths', ['git', 'diff-tree', '--no-commit-id', '--name-only', '-r', 'HEAD']).splitlines()) == set(selected), 'commit paths')
        require(not run('index-after', ['git', 'diff', '--cached', '--name-only']), 'index not empty')
        for path, expected in members.items():
            require(identity(ROOT / path) == expected, 'postcommit source drift')
        run('push', ['git', 'push', 'origin', 'HEAD:refs/heads/main'])
        require(run('remote-after', ['git', 'ls-remote', '--exit-code', 'origin', 'refs/heads/main']).split() ==
                [revision, 'refs/heads/main'], 'remote confirmation failed; inspect without retry')
        result.update(status='DELIVERED', revision=revision, paths=len(selected), forcePush=False)
    except BaseException as error:
        result.update(status='FAILED', error=repr(error))
        raise
    finally:
        result['cleanup'] = commands.cleanup(scratch)
        result['commands'] = str((out / 'commands.json').relative_to(ROOT))
        (HERE / (phase+'-result.json')).write_text(json.dumps(result, indent=2)+'\n')
        print(json.dumps(result))


if __name__ == '__main__':
    main()
