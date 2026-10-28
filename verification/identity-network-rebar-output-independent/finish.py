#!/usr/bin/env python3
"""Read existing public evidence and seal this owned independent review."""
from pathlib import Path
import ast, datetime, hashlib, json, sys
BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
PACKET = ROOT / 'verification/identity-network-rebar-output-correction'
def row(data): return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
def canon(value): return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
def save(name, value): (BASE / name).write_text(json.dumps(value, sort_keys=True, indent=2) + '\n')

proof = PACKET / 'proof/runtime-review/selected/artifact'
prepared = json.loads((proof / 'prepared-manifest.json').read_bytes())
markers = [line[len(b'IDENTITY_JSON='):] for line in (proof / 'logs/0089.stdout').read_bytes().splitlines() if line.startswith(b'IDENTITY_JSON=')]
assert len(markers) == 1
compiled = json.loads(markers[0])
diff = []
assert set(prepared) == set(compiled) == {'source', 'deps', 'tools', 'helpers'}
for section in sorted(prepared):
    for path in sorted(prepared[section].keys() | compiled[section].keys()):
        old, new = prepared[section].get(path), compiled[section].get(path)
        if old != new: diff.append({'section': section, 'path': path, 'before': old, 'after': new})
expected = [{'after': {'bytes': 895, 'sha256': '71360df95b056715d6215b91ba581e4dd91d850f4894c13720f142075a53d685'}, 'before': None, 'path': 'hosted/deps/telemetry/_build/prod/lib/.rebar3/rebar_compiler_erl/source.dag', 'section': 'deps'}]
assert diff == expected == json.loads((PACKET / 'proof/runtime-review/manifest-diff.json').read_bytes())
command = json.loads((proof / 'logs/0089.json').read_bytes())
assert command['exit_code'] == 0 and command['stdout_complete'] is True and command['stderr_complete'] is True
assert command['stdout_bytes'] == (proof / 'logs/0089.stdout').stat().st_size and command['stderr_bytes'] == 0
save('prior-causal-diff.json', {'command': 89, 'actual_run_id': 40753111388, 'complete_command': True, 'recomputed_difference': diff, 'raw_DAG_or_file_metadata_available': False})

bindings = json.loads((PACKET / 'source-bindings.json').read_bytes())
for path, expected_row in bindings.items(): assert row((ROOT / path).read_bytes()) == expected_row
assert canon(bindings) == '163073180bacc272e3d19209508cf9e625950f1afb8bc7a5b6b1b1c27ae9bf91'
assert row((PACKET / 'packet-manifest.json').read_bytes())['sha256'] == 'd56a5dde00bc61888d5cdf690cf0e44bf11430ac3bb82a819d3206de390349ac'
for path, expected_hash in {'.github/workflows/hosted.yml': 'fafd2560cc385a4113ea140bf2d4445d456e1f7f396539dfe2c3e7d6302e8b57', 'hosted/lib/mixer_hosted/browser_auth/store.ex': '8c314b1d3ce288a6dc617251233796bd0a9d8894247ccb15b101e1292e513299'}.items(): assert row((ROOT / path).read_bytes())['sha256'] == expected_hash

execution = json.loads((BASE / 'execution.json').read_bytes())
decision = {
    'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'reviewer': {'task': '/root/astra_rebar_output_independent', 'delegated_model': 'gpt-6-astra', 'delegated_reasoning_effort': 'xhigh', 'fresh_context': True},
    'decision': 'accept-source-correction-for-fresh-isolated-CI-only', 'blocking_findings': [],
    'source_revision_observed_by_readonly_git': '56ff14c925168284761c5aca4f0bd4129cf3c995',
    'git_tree_observed': '75989099938ed5256c4144cbc9e62979ee323183', 'git_version_observed': 'git version 2.56.0',
    'canonical_three_file_tree_digest_sha256': canon(bindings),
    'correction_packet_manifest_sha256': 'd56a5dde00bc61888d5cdf690cf0e44bf11430ac3bb82a819d3206de390349ac',
    'correction_packet_tree_digest_sha256': '471e4b7f76ded7273fb53760a421cad60d48d4b7419746ca9360b5f3263b4093',
    'prior_runtime_review_packet_manifest_sha256': '148912f1c031a1bdd757376436cd4959235b170f7dd2ae60e6c38df2d6a96d8c',
    'verified': [
        '48 correction files and 483 prior review files rehashed; exact inventories and seals match',
        'canonical files exactly equal sealed after snapshots; protected hosted workflow and store hashes unchanged',
        'all prior Python function bodies except Collector.collect exact; all prior assignment ASTs except MANIFEST_EXS exact; all 111 prior test methods exact',
        '126 producer pure controls and six independent probe methods passed under 50-second audit bound',
        'prior command 89 completed; independently recomputed full manifest difference is exactly the single fresh 895-byte telemetry DAG',
        'prepared archive build ban and restored manifest equality remain exact',
        'postcompile admission requires frozen source/lock and pinned telemetry anchors; removes only exact fresh DAG row before full comparison',
        'new helper checks exact file/ancestor type, owner, mode and bounds; fixed export performs no ETF interpretation',
        'capture requires owned test role, finite timeout at most 15 seconds, complete command and exact byte/hash join before input validation and test flag',
        'known raw capture survives byte/hash and later immutable-input rejection; exact maximum, zero, neighboring aliases and malformed metadata exercised',
        'final unchanged-source comparison includes generated row contents and observed metadata',
        'generic export paths, execution/create/cleanup/seal functions, resources, mounts, images and other helper bindings unchanged'
    ],
    'boundary_limitations': [
        'Generated lstat checks followed by File.read! are point-in-time checks, not descriptor-bound atomic identity against a concurrent same-root writer.',
        'Host capture exists() plus write_bytes is not an atomic no-follow exclusive-create guarantee against concurrent same-UID mutation of the fresh owned output directory.',
        'These limitations do not block the existing serial ordinary fixture scope: output is exclusively created, runtime containers have no host source/socket mounts, and the reviewed tool/source inputs remain fixed. This is not acceptance of an adversarial compiler or hostile concurrent writer threat model.',
        'A command exception before command() persists its stdout can leave missing partial bytes; missing or incomplete command evidence remains unqualified. Existing command implementation is unchanged.',
        'Actual helper Elixir syntax, Linux uid/gid/modes, raw DAG semantics and the two product methods were not executed by this source review.'
    ],
    'named_unlock': 'fresh isolated identity-production-network CI attempt that reaches both unchanged production-network methods after actual helper/raw-DAG/input-equality checks',
    'required_next_evidence': [
        'fresh actual Elixir helper execution, complete raw DAG export <=64KiB and exact compiled-manifest byte/hash join',
        'actual root uid/gid and 0644/0755 metadata hypotheses validated or a separately reviewed evidence-based correction',
        'fresh prerequisite/image/mount/environment/namespace/resource checks, loaded-module identities, both product methods and semantic receipts',
        'current ten migrations, exact post-test manifest including DAG, synthetic key-directory cleanup and all owned CID cleanup',
        'independent acceptance of complete fresh run artifacts'
    ],
    'runtime_qualification': False, 'product_method_pass': False, 'GA_accepted': False,
    'commands': [
        {'argv': ['python3', '-B', 'verification/identity-network-rebar-output-independent/review.py'], 'exit_code': 0, 'alarm_seconds': 50, 'seconds': execution['seconds']},
        {'argv': ['git', '--no-replace-objects', 'rev-parse', 'HEAD', 'HEAD^{tree}'], 'exit_code': 0, 'scope': 'readonly source identity'},
        {'argv': ['git', '--version'], 'exit_code': 0},
        {'argv': ['python3', '-B', 'verification/identity-network-rebar-output-independent/finish.py'], 'scope': 'offline prior-diff recomputation, current-source recheck and owned review seal'}
    ],
    'scope_holds': ['UnitA', 'broad local hosted and PostgreSQL', 'held processes and custody including 20745,20770,20780,20817,20842,20851,20866', 'native simulator/emulator and phones', 'UI and screen capture', 'private FieldLog source', 'provider/customer/release/GA'],
    'canonical_edits_commit_push_dispatch_or_new_runtime': False,
    'cleanup': execution['cleanup'], 'unexpected_audit_denials': execution['unexpected_denials']
}
save('decision.json', decision)
paths = sorted(p for p in BASE.rglob('*') if p.is_file() and p.name != 'packet-manifest.json')
assert not any(p.is_symlink() for p in BASE.rglob('*'))
files = {str(p.relative_to(BASE)): row(p.read_bytes()) for p in paths}
assert not (BASE / 'packet-manifest.json').exists()
manifest = {'schema': 1, 'files': files, 'tree_digest_sha256': canon(files), 'scope': decision['decision']}
save('packet-manifest.json', manifest)
print(json.dumps({'decision': decision['decision'], 'files': len(files), 'tree_digest_sha256': canon(files), 'packet_manifest': row((BASE / 'packet-manifest.json').read_bytes()), 'runtime_qualification': False}, sort_keys=True))
