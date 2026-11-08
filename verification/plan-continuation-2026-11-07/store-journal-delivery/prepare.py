#!/usr/bin/env python3
"""Recompute delivery from file bytes only; writes only beside this file."""
import difflib
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import re
import shlex
import sys
from datetime import datetime, timezone

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE = HERE.parent
FIX = BASE / 'store-journal-integrity-fix'
REVIEW = BASE / 'store-journal-integrity-review'
BASE_DIGEST = 'a10a62cc79145bc80bfd780257589f437cc82e2f1ebaad6ccde39c134d56e0ca'
PATCH_DIGEST = 'a66174135b4756a46426c36e5f38029898774768f8be0bc4049894413f235446'

def require(value, message):
    if not value:
        raise RuntimeError(message)

def identity(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

def file_identity(path):
    return identity(path.read_bytes())

def save(name, data):
    (HERE / name).write_text(json.dumps(data, indent=2, sort_keys=True) + '\n')

def digest(files):
    return hashlib.sha256(''.join(p + '\0' + v['sha256'] + '\n'
        for p, v in sorted(files.items())).encode()).hexdigest()

def apply_in_memory(patch, expected):
    """Exact unified hunks; no fuzz, offset, subprocess, or filesystem mutation."""
    results, checks = {}, {}
    blocks = patch.split(b'diff --git ')[1:]
    require(len(blocks) == 4, 'Patch must have four file sections')
    for block in blocks:
        lines = block.splitlines(keepends=True)
        header = lines[0].decode().rstrip('\n').split(' ')
        require(len(header) == 2 and header[0].startswith('a/') and header[1].startswith('b/'), 'Bad diff header')
        path = header[1][2:]
        require(path == header[0][2:] and path in expected and path not in results, 'Unexpected or repeated path')
        target = ROOT / path
        require(not target.is_symlink(), 'Canonical target is a symlink')
        old_header = next(x for x in lines if x.startswith(b'--- ')).rstrip(b'\n')[4:]
        new_file = old_header == b'/dev/null'
        require(new_file == (not target.exists()), 'Creation/existing-file precondition differs: ' + path)
        require(new_file or old_header == ('a/' + path).encode(), 'Old path differs')
        require(b'+++ b/' + path.encode() + b'\n' in lines, 'New path differs')
        original = b'' if new_file else target.read_bytes()
        source, output, cursor, i, hunks = original.splitlines(keepends=True), [], 0, 0, 0
        while i < len(lines):
            if not lines[i].startswith(b'@@ '):
                i += 1
                continue
            match = re.fullmatch(rb'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@[^\n]*\n', lines[i])
            require(match is not None, 'Unsupported hunk header')
            old_start, old_count, new_start, new_count = (int(match[1]), int(match[2] or 1), int(match[3]), int(match[4] or 1))
            position = old_start - 1 if old_count else old_start
            require(cursor <= position <= len(source), 'Overlapping or out-of-range hunk')
            output.extend(source[cursor:position]); cursor = position
            require(len(output) == (new_start - 1 if new_count else new_start), 'New hunk offset differs')
            removed = added = 0
            i += 1
            while i < len(lines) and not lines[i].startswith(b'@@ '):
                line = lines[i]
                require(line[:1] in (b' ', b'+', b'-'), 'Unsupported patch body or no-newline marker')
                if line[:1] in (b' ', b'-'):
                    require(cursor < len(source) and source[cursor] == line[1:], 'Exact base/context mismatch: ' + path)
                    cursor += 1; removed += 1
                if line[:1] in (b' ', b'+'):
                    output.append(line[1:]); added += 1
                i += 1
            require((removed, added) == (old_count, new_count), 'Hunk line counts differ')
            hunks += 1
        output.extend(source[cursor:])
        value = b''.join(output)
        require(hunks > 0 and identity(value) == expected[path], 'Candidate hash mismatch: ' + path)
        require(value == (FIX / 'candidate' / path).read_bytes(), 'Frozen candidate bytes differ')
        results[path] = value
        checks[path] = {'operation': 'create' if new_file else 'modify', 'before': None if new_file else identity(original),
            'after': identity(value), 'hunks': hunks, 'exactHunksMatch': True, 'frozenCandidateMatches': True}
    require(set(results) == set(expected), 'Four-path set differs')
    return results, checks

def main():
    manifest_path = FIX / 'patch-manifest.json'
    manifest = json.loads(manifest_path.read_text())
    patch = (FIX / 'implementation.patch').read_bytes()
    require(identity(patch)['sha256'] == PATCH_DIGEST, 'Accepted patch hash differs')
    report = (REVIEW / 'REPORT.md').read_text()
    require(report.startswith('**ACCEPT') and PATCH_DIGEST in report and '462' in report and '33/33' in report, 'Independent review binding differs')
    expected = manifest['files']
    candidate, checks = apply_in_memory(patch, expected)
    runner_path = ROOT / 'scripts/ci/check-android-generated-java.py'
    spec = importlib.util.spec_from_file_location('delivery_readonly_authority', runner_path)
    authority = importlib.util.module_from_spec(spec); spec.loader.exec_module(authority)
    profile = authority.load_profile()
    current = authority.source_inputs(profile)
    require(len(current) == 101 and digest(current) == BASE_DIGEST, 'Current canonical101 has drifted')
    prospective = dict(current)
    for path, data in candidate.items():
        if path.startswith('cli/Sources/'):
            prospective[path] = identity(data)
    require(len(prospective) == 103, 'Expected source103')
    proposed_digest = digest(prospective)
    require(proposed_digest != 'f64cc694b942799d9c4f6755028ce5c7988ddc2f3d0e027603e340e47692d72f', 'Rejected digest reused')
    metadata = {
      'verification/plan-continuation-2026-11-07/generated-java-ci-integration/bootstrap.py': [
        ('SOURCE_INPUT_COUNT = 101', 'SOURCE_INPUT_COUNT = 103'),
        ("SOURCE_INPUT_SHA256 = '" + BASE_DIGEST + "'", "SOURCE_INPUT_SHA256 = '" + proposed_digest + "'")],
      'verification/plan-continuation-2026-11-07/generated-java-ci-integration/test_sparse_checkout.py': [
        ('self.assertEqual(len(inputs), 101)', 'self.assertEqual(len(inputs), 103)')]}
    metadata_checks, metadata_diff = {}, ''
    for path, replacements in metadata.items():
        before = (ROOT / path).read_text(); after = before
        for old, new in replacements:
            require(after.count(old) == 1, 'Metadata baseline differs: ' + path)
            after = after.replace(old, new)
        metadata_diff += ''.join(difflib.unified_diff(before.splitlines(keepends=True), after.splitlines(keepends=True),
            fromfile='a/' + path, tofile='b/' + path))
        metadata_checks[path] = {'before': identity(before.encode()), 'after': identity(after.encode()),
            'replacements': [{'old': x, 'new': y} for x, y in replacements]}
    (HERE / 'proposed-metadata.patch').write_text(metadata_diff)
    prior_path = BASE / 'generated-java-pair9-r2-actual/primary/receipt.json'
    prior = json.loads(prior_path.read_text())
    prior_review = json.loads((BASE / 'generated-java-pair9-r2-actual-review/result.json').read_text())
    require(prior_review['verdict'] == 'ACCEPT' and prior_review['evidence']['rawReceipt'] == file_identity(prior_path), 'Accepted pair9 receipt binding differs')
    require(prior['source_inputs'] == current and prior['status'] == 'passed-java-crosscompile-only', 'Pair9 source101 differs')
    require(file_identity(runner_path) == prior_review['candidate']['runner'], 'Accepted runner differs')
    python = next(c['argv'][0] for c in prior['command_records'] if c['label'] == 'official-inspect')
    output = BASE / 'store-journal-six-consumers'
    require(not output.exists(), 'New consumer namespace already exists; root must reconcile rather than overwrite')
    argv = [python, '-B', str(runner_path)]
    for flag, key in [('swift','swift'),('swift-sdks','swift_sdks'),('android-artifact','android_artifact'),('jdk','jdk'),('android-sdk','android_sdk')]:
        argv += ['--' + flag, prior['selected_paths'][key]]
    argv += ['--output', str(output), '--execute-toolchains']
    environment = prior['apple_producer']['selection']
    command = shlex.join(['/usr/bin/env', '-u', 'TOOLCHAINS', 'PYTHONDONTWRITEBYTECODE=1',
        *[k + '=' + v for k, v in environment.items()], *argv])
    (HERE / 'six-consumers.command.txt').write_text('cd ' + shlex.quote(str(ROOT)) + '\n' + command + '\n')
    control_paths = ['scripts/ci/tests/test_android_generated_java_runner.py',
        'verification/plan-continuation-2026-11-07/generated-java-ci-integration/test_bootstrap.py',
        'verification/plan-continuation-2026-11-07/generated-java-ci-integration/test_sparse_checkout.py']
    control_commands = [shlex.join([python, '-I', '-B', '-S', *(['-O'] if optimized else []), str(ROOT / path), '-v'])
        for path in control_paths for optimized in (False, True)]
    (HERE / 'controls.command.txt').write_text('cd ' + shlex.quote(str(ROOT)) + '\n' + '\n'.join(control_commands) + '\n')
    bindings = {str(p.relative_to(ROOT)): file_identity(p) for p in [manifest_path, FIX/'implementation.patch', REVIEW/'REPORT.md', prior_path,
        BASE/'generated-java-pair9-r2-actual-review/result.json', BASE/'pair9-generated-hosted-acceptance.json', runner_path,
        ROOT/'cli/Sources/MixerBuild/AndroidSDKCompatibility.swift', ROOT/'cli/Sources/MixerBuild/Resources/android-build.py',
        ROOT/'.github/workflows/verify.yml', BASE/'generated-java-ci-integration/workflow-proposal.yml', FIX/'cleanup_control.py',
        BASE/'store-status-root-integration/prospective-source103.json', *[ROOT/p for p in metadata]]}
    save('current-source101.json', current)
    save('prospective-source103.json', prospective)
    save('manifest.json', {'schema':1, 'preparedAt':datetime.now(timezone.utc).isoformat(),
      'status':'PREPARED_FOR_ALREADY_AUTHORIZED_ROOT_INTEGRATION_AFTER_API28_ATTEMPT',
      'writesOnly':str(HERE), 'preparationPython':sys.version, 'preparationExecutable':sys.executable, 'host':platform.system(),
      'candidatePatchSHA256':PATCH_DIGEST, 'applicationChecks':checks,
      'review':{'decision':'ACCEPT','path':str(REVIEW/'REPORT.md'),'groups':33,'mutatedOperations':462,'preProviderRefusals':20,
        'manifestReviewFlagsPredateIndependentAcceptance':True,'suppliedTests':31,'reviewTests':33,
        'reviewAppendedGroupsAreEvidenceNotPartOfFourPathPatch':True},
      'currentSourceCount':101,'currentSourceSHA256':BASE_DIGEST,'proposedSourceCount':103,'proposedSourceSHA256':proposed_digest,
      'sourceDigestEncoding':'SHA256 of sorted path + NUL + lowercase file SHA256 + newline, UTF-8',
      'sourceAdded':sorted(set(prospective)-set(current)),
      'sourceChanged':sorted(p for p in current if current[p] != prospective[p]),
      'testPathOutsideOwningSourceClosure':'cli/Tests/MixerBuildTests/StoreReconciliationTests.swift',
      'metadataEdits':metadata_checks,'protectedBindings':bindings,
      'sixConsumers':{'executed':False,'namespace':str(output),'argv':argv,'environment':environment,'unsetEnvironment':['TOOLCHAINS'],
        'command':command,'acceptedPathSource':str(prior_path),'pathProvenanceIsHistorical':True},
      'controls':{'executed':False,'commands':control_commands},
      'bounds':{'runnerSeconds':2400,'commandSeconds':600,'commandCountMaximum':160,'producerJobs':2,
        'perStreamBytes':4194304,'explicitJavapStdoutMaximum':8388608,'aggregateOutputBytes':67108864,'cleanupSeconds':5},
      'canonicalWrites':False,'compilerRuns':0,'JVMRuns':0,'networkCalls':0,'processQueries':0,'otherAgents':0,'commits':0,'pushes':0,
      'limits':['API28 source101 remains pinned until root records its attempt finished.',
        'Only exact candidate delivery and prospective metadata are checked here; canonical application and six actual consumers remain unperformed.',
        'No redundant 33-group Swift run is required before actual consumers: accepted review already binds these exact product bytes and supplied31-test prefix.',
        'No live ASC, native runtime, API28 floor, D6, immutable package, FieldLog, signing, store, or GA acceptance.',
        'All historical process/custody, reserved simulator, v5, frozen hosted and physical-phone holds remain.']})
    require(authority.source_inputs(profile) == current, 'Canonical closure changed during preparation')
    require(all(file_identity(ROOT/p) == v for p,v in bindings.items()), 'Protected input changed during preparation')
    save('postflight.json', {'allProtectedBindingsUnchanged':True,'canonicalSource101Unchanged':True,
        'fileChecksPassed':True,'strictPatchApplication':'in memory only','metadataApplied':False,
        'preparationSource':file_identity(Path(__file__)),'command':[sys.executable,'-I','-B','-S',str(Path(__file__))]})
    print(json.dumps({'fileChecks':'passed','current101':BASE_DIGEST,'proposed103':proposed_digest,'canonicalWrites':False}))

if __name__ == '__main__':
    main()
