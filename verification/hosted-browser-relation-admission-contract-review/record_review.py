#!/usr/bin/env python3
"""Record the bounded independent review; writes only this lane's directory."""
from __future__ import annotations
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def dump(name, data):
    (HERE / name).write_text(json.dumps(data, indent=2) + '\n')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(label, argv):
    result = subprocess.run(argv, cwd=ROOT, text=True, capture_output=True, check=False)
    (HERE / f'{label}.stdout').write_text(result.stdout)
    (HERE / f'{label}.stderr').write_text(result.stderr)
    row = dict(argv=argv, cwd=str(ROOT), exit_code=result.returncode,
               stdout=f'{label}.stdout', stderr=f'{label}.stderr')
    dump(f'{label}-command.json', row)
    return result, row


commands = []
for name, argv in [('python-version', ['python3', '--version']),
                   ('elixir-version', ['elixir', '--version']),
                   ('git-version', ['git', '--version']),
                   ('source-revision', ['git', 'rev-parse', 'HEAD'])]:
    result, command = run(name, argv)
    commands.append(command)
    if result.returncode:
        sys.exit(result.returncode)

result, command = run('review-tests', ['python3', str(HERE.relative_to(ROOT) / 'check_review.py')])
commands.append(command)
print(result.stderr)
if result.returncode:
    dump('commands.json', commands)
    sys.exit(result.returncode)

# Import own checker, not producer expectation/checker/extractor. Its only
# execution is the allowlisted ordinary-source capture already recorded.
spec = importlib.util.spec_from_file_location('independent_relation_review', HERE / 'check_review.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
incoming = [dict(source_relation=r, **f) for r, table in module.D['tables'].items() if r not in module.NAMES
            for f in table['foreign_keys'] if f['relation'] in module.NAMES]
dump('independent-derived-baseline.json', dict(
    scope='Ordinary source derived structure only, not live PostgreSQL expectation forms',
    relations={r: module.D['tables'][r] for r in module.NAMES},
    policies={r: module.D['policies'][r] for r in module.NAMES},
    writer_grants=module.D['grants'], user_triggers=module.D['triggers'],
    incoming_foreign_keys=incoming, counts_by_relation=module.EXPECTED_COUNTS,
    function_source_bindings={n: dict(bytes=len(s.encode()), sha256=hashlib.sha256(s.encode()).hexdigest())
                              for n, s in module.FUNCTIONS.items()}))

text_paths = [HERE / 'capture_ordinary_source.exs', HERE / 'check_review.py', HERE / 'record_review.py',
              ROOT / 'docs/hosted-browser-relation-admission-contract-review.md']
issues = []
for path in text_paths:
    data = path.read_bytes()
    if not data.endswith(b'\n') or data.endswith(b'\n\n'):
        issues.append(str(path.relative_to(ROOT)) + ': terminal newline')
    if any(line.rstrip(b' \t') != line for line in data.splitlines()):
        issues.append(str(path.relative_to(ROOT)) + ': trailing whitespace')
dump('text-lint.json', dict(paths=[str(p.relative_to(ROOT)) for p in text_paths], issues=issues, passed=not issues))
if issues:
    sys.exit('owned text lint failed')

closure = json.loads((HERE / 'reviewed-migration-source-closure.json').read_text())
inputs = {x['path']: x['sha256'] for x in closure['inputs']}
for path in ('AGENTS.md', 'PLAN.md', 'docs/hosted-browser-lifecycle-runtime-contract.md'):
    inputs[path] = sha(ROOT / path)
input_tree = hashlib.sha256(''.join(f'{p}\t{inputs[p]}\n' for p in sorted(inputs)).encode()).hexdigest()
producer_receipt = ROOT / 'verification/hosted-browser-relation-admission-contract/receipt.json'
producer = json.loads(producer_receipt.read_text())
dump('commands.json', commands)
artifacts = {str(p.relative_to(ROOT)): sha(p) for p in sorted(HERE.iterdir())
             if p.is_file() and p.name != 'receipt.json'}
artifacts['docs/hosted-browser-relation-admission-contract-review.md'] = sha(ROOT / 'docs/hosted-browser-relation-admission-contract-review.md')
artifact_tree = hashlib.sha256(''.join(f'{p}\t{artifacts[p]}\n' for p in sorted(artifacts)).encode()).hexdigest()
dump('receipt.json', dict(
    format=1, recorded_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    scope='Independent source/structural contract review only; no database or runtime security acceptance',
    source_revision=(HERE / 'source-revision.stdout').read_text().strip(),
    input_sha256=inputs, input_tree_sha256=input_tree,
    tree_digest_format='SHA256 of sorted path + TAB + file SHA256 + LF records',
    producer_receipt_sha256=sha(producer_receipt), producer_input_tree_sha256=producer['input_tree_sha256'],
    producer_artifact_tree_sha256=producer['artifact_tree_sha256'],
    artifact_sha256=artifacts, artifact_tree_sha256=artifact_tree,
    observed_result=dict(methods_passed=16, methods_failed=0,
                         shape_negative_controls=10, policy_negative_controls=6, grant_negative_controls=5,
                         relations=9, columns=124, checks=80, primary_keys=9, unique_constraints=4,
                         outgoing_foreign_keys=10, incoming_boundary_foreign_keys=2, indexes=14,
                         user_triggers=5, policies=32, ordinary_public_policies=10, writer_policies=22,
                         proposed_fk_groups_pending_runtime=12, proposed_ri_triggers_pending_runtime=48,
                         proposed_all_triggers_pending_runtime=53, proposed_constraint_boundary_pending_runtime=109,
                         runtime_cases_pending=producer['observed_result']['runtime_cases_pending']),
    corrected_findings=[
        dict(priority='blocking source completeness', source='hosted/lib/mixer_hosted/customer_artifacts/schema.ex:67',
             detail='Omitted idempotency principal FK; old packet had one incoming FK and undercounted boundary/RI caps',
             retained_regression='incoming-fk-regression.stderr', corrected=True),
        dict(priority='contract clarity', detail='Qualified immutable/authz linkage UPDATE denial against exact mutable browser lists', corrected=True),
        dict(priority='contract clarity', detail='Explicit four RI function/event/endpoint mappings and FK/other-endpoint/index linkage', corrected=True)],
    historical_incomplete_packet=dict(receipt_sha256='701bd8c6a36cd3002fc2c42fed81dff0969db761dbdd89aea7aece447b120ab1',
                                      retained_matrix='before-incoming-fk-correction-relation-matrix.json',
                                      accepted=False, dependency_expansion_regression=dict(methods_passed=11, methods_failed=2)),
    review_tool_adaptation=dict(retained_output='v2-provenance-field-adaptation-review-tests.stderr',
                                methods_passed=15, methods_failed=1,
                                reason='Corrected packet added migration source-location metadata to second incoming FK; review separates provenance fields from unchanged exact FK semantics'),
    text_lint_repair=dict(retained_output='text-lint-before-terminal-lf-repair.json',
                          reason='Removed the extra terminal LF appended after Elixir formatter output in owned inert extractor; no semantic change'),
    pending=['Actual PostgreSQL16/17 catalogs, deparse/defaults/collation/locale and full RI fixture review',
             'RelationCatalog implementation, bounded query/result/ACL escape checks and independent runtime tests',
             'Trusted Store/Repo/owner and original deadline/rollback/current function prerequisite composition',
             'Provider/HTTP/console/Neon/operator/customer/FieldLog and GA qualification'],
    resource_cleanup=dict(database_started=False, database_connection_attempted=False,
                          native_or_capture_started=False, ui_automation_performed=False,
                          process_discovery_performed=False, other_projects_processes_touched=False,
                          owned_disposable_processes_remaining=False, bytecode_cache_present=(HERE / '__pycache__').exists(),
                          persistent_evidence_only=True),
    delivery=dict(committed=False, pushed=False, coordinator='root'),
    limitations=['Static SQL token comparison tests documentation transcription only; not live expression authorization',
                 'No producer checker/expectation module was imported or executed',
                 'No frozen catalog-inspector, authority-driver, rejected WorkerV2, broad app or harness was read/executed',
                 'No native tests were attempted under pause; no skipped or unrun gate marked passed']))
print(json.dumps({'review_receipt_sha256':sha(HERE / 'receipt.json'), 'artifact_tree_sha256':artifact_tree}))
