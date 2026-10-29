#!/usr/bin/env python3
"""File-only controls. No local compiler, subprocess, shell or network access."""
from pathlib import Path
import sys
HERE = Path(__file__).resolve().parent
V3 = HERE.parent / 'cache-fixture-compiler-admission-v3'
sys.path.insert(0, str(V3))
import offline_guard
sys.path.pop(0)
offline_guard.install(HERE)

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import io
import json
import shutil
import tempfile
import unittest
import workflow_context as workflow
import verify_candidate as verifier

WORKFLOW_SHA256 = '4d00c7a64b32ff4d20725189906fcdf24817525fde8b8285ad3440eb1eda926d'


class WorkflowContextControls(unittest.TestCase):
    def setUp(self):
        self.source = (HERE / 'workflow/cache-fixture-workflow-context-v4.yml').read_text()
        self.old_source = (V3 / 'workflow/cache-fixture-compiler-admission-v3.yml').read_text()
        self.document = workflow.parse(self.source)
        self.original = workflow.parse(self.old_source)
        self.job = self.document['jobs']['complete-fixture-on-declared-compiler']

    def test_original_rejection_reproduced_at_job_env(self):
        with self.assertRaisesRegex(ValueError, 'Context runner unavailable at jobs.*env.RUSTUP_HOME'):
            workflow.validate(self.original)

    def test_candidate_all_context_references_allowed(self):
        result = workflow.validate(self.document)
        runner = [r for r in result['expression_references'] if r['expression'] == 'runner.temp']
        self.assertEqual([r['location'] for r in runner], [
            'jobs.complete-fixture-on-declared-compiler.steps.3.env.RUSTUP_HOME',
            'jobs.complete-fixture-on-declared-compiler.steps.4.env.RUSTUP_HOME'])
        self.assertFalse(result['official_validator'])

    def test_schema_and_documented_context_difference(self):
        rules = json.loads((HERE / 'context-rules.json').read_text())
        self.assertNotIn('runner', rules['contexts']['job-env'])
        self.assertIn('runner', rules['contexts']['step-env'])
        self.assertEqual(rules['schema_version'], 'workflow-v1.0')

    def test_exact_authorized_transform_and_bytes(self):
        self.assertEqual(hashlib.sha256(self.source.encode()).hexdigest(), WORKFLOW_SHA256)
        workflow.validate_contract(self.document, self.original)

    def test_install_and_fixture_scripts_identical_to_v3(self):
        previous = self.original['jobs']['complete-fixture-on-declared-compiler']['steps']
        for index in [3, 4]:
            self.assertEqual(self.job['steps'][index]['run'], previous[index]['run'])
            self.assertEqual(self.job['steps'][index]['timeout-minutes'], previous[index]['timeout-minutes'])

    def test_step_homes_identical_and_job_home_absent(self):
        self.assertNotIn('RUSTUP_HOME', self.job['env'])
        self.assertEqual(self.job['steps'][3]['env'], self.job['steps'][4]['env'])
        self.assertEqual(self.job['steps'][3]['env']['RUSTUP_HOME'],
                         self.original['jobs']['complete-fixture-on-declared-compiler']['env']['RUSTUP_HOME'])

    def test_job_scope_regression_rejected(self):
        self.job['env'].update(self.job['steps'][3].pop('env'))
        with self.assertRaisesRegex(ValueError, 'Context runner unavailable'):
            workflow.validate(self.document)

    def test_workflow_scope_regression_rejected(self):
        self.document['env'] = self.job['steps'][3]['env']
        with self.assertRaisesRegex(ValueError, 'Context runner unavailable at env'):
            workflow.validate(self.document)

    def test_missing_fixture_home_rejected(self):
        self.job['steps'][4].pop('env')
        with self.assertRaisesRegex(ValueError, 'authorized'):
            workflow.validate_contract(self.document, self.original)

    def test_changed_home_or_pin_or_install_authority_rejected(self):
        mutations = [
            lambda j: j['steps'][4]['env'].update(RUSTUP_HOME='different'),
            lambda j: j['env'].update(RUSTUP_TOOLCHAIN='1.99.0-aarch64-apple-darwin'),
            lambda j: j['env'].update(RUSTUP_AUTO_INSTALL='1'),
            lambda j: j['steps'][3].update(**{'timeout-minutes': 3}),
            lambda j: j['steps'].insert(5, deepcopy(j['steps'][4])),
            lambda j: j['steps'][4].update(**{'continue-on-error': True})]
        for mutation in mutations:
            changed = deepcopy(self.document)
            mutation(changed['jobs']['complete-fixture-on-declared-compiler'])
            with self.subTest(mutation=mutation), self.assertRaisesRegex(ValueError, 'authorized'):
                workflow.validate_contract(changed, self.original)

    def test_duplicate_keys_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Duplicate mapping key'):
            workflow.parse(self.source.replace('    runs-on: macos-15',
                                               '    runs-on: macos-15\n    runs-on: macos-15'))

    def test_unsupported_yaml_fails_closed(self):
        for source in ['a: &alias value\n', 'a: *alias\n', 'a: >\n  text\n',
                       'a: [one, two]\n', 'a: !tag value\n', '---\na: one\n', 'a:\n\tb: one\n']:
            with self.subTest(source=source), self.assertRaises(ValueError):
                workflow.parse(source)

    def test_unsupported_expression_fails_closed(self):
        for expression in ["${{ runner['temp'] }}", '${{ unknown.temp }}', '${{ runner.temp',
                           "${{ format('{0}', runner.temp) }}"]:
            with self.subTest(expression=expression), self.assertRaises(ValueError):
                workflow.expressions(expression, ['runner'], 'synthetic')

    def test_manual_trigger_and_failure_path_preserved(self):
        self.assertEqual(self.document['on'], {'workflow_dispatch': None})
        self.assertEqual([i for i, step in enumerate(self.job['steps']) if 'if' in step], [5, 6])
        for index in [5, 6]:
            self.assertEqual(self.job['steps'][index]['if'], 'always()')

    def test_frozen_source_closure(self):
        result = verifier.verify()
        self.assertEqual(result['frozen_v3_seal_sha256'], verifier.V3_SEAL)
        self.assertFalse(result['installed_v2_v4_bound_and_invalid_v3_absent'])

    def test_installed_mode_requires_exact_v2_v4_and_retired_v3(self):
        scratch = HERE / 'control-scratch'
        scratch.mkdir(exist_ok=True)
        temporary = Path(tempfile.mkdtemp(dir=scratch))
        old_root = verifier.ROOT
        try:
            directory = temporary / '.github/workflows'
            directory.mkdir(parents=True)
            current = directory / Path(verifier.WORKFLOW).name
            previous = directory / Path(verifier.REJECTED).name
            v2_name = 'cache-fixture-shared-input-controls-v2.yml'
            current.write_text(self.source)
            (directory / v2_name).write_bytes((HERE.parent / 'cache-fixture-shared-input-candidate-v2'
                                               / 'workflow' / v2_name).read_bytes())
            verifier.ROOT = temporary
            self.assertTrue(verifier.verify(True)['installed_v2_v4_bound_and_invalid_v3_absent'])
            previous.write_text(self.old_source)
            with self.assertRaisesRegex(RuntimeError, 'must be retired'):
                verifier.verify(True)
            previous.unlink()
            current.write_text(self.source + '\n')
            with self.assertRaisesRegex(RuntimeError, 'Installed v4 workflow differs'):
                verifier.verify(True)
            current.write_text(self.source)
            (directory / v2_name).write_text('altered\n')
            with self.assertRaisesRegex(RuntimeError, 'Installed v2 workflow differs'):
                verifier.verify(True)
        finally:
            verifier.ROOT = old_root
            shutil.rmtree(temporary)
            if not any(scratch.iterdir()):
                scratch.rmdir()


if __name__ == '__main__':
    output = io.StringIO()
    result = unittest.TextTestRunner(stream=output, verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(WorkflowContextControls))
    text = output.getvalue()
    print(text, end='')
    logs = HERE / 'logs'
    logs.mkdir(exist_ok=True)
    (logs / 'pure-controls.stdout').write_text(text)
    receipt = {
        'schema': 1, 'at': datetime.now(timezone.utc).isoformat(), 'python': sys.version,
        'command': 'python3 -B verification/cache-fixture-workflow-context-v4/test_context.py',
        'source_revision': 'c62f80e386016ead55d11786a8c0fc6c1f3d4eff',
        'source_tree': '16ea61785086424f3eae070e48d9154fe0cacbe9',
        'source_identity_provenance': 'parent-supplied canonical base; no local Git command',
        'tests_run': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
        'forbidden_operations_attempted': offline_guard.DENIED,
        'control_scratch_absent': not (HERE / 'control-scratch').exists(),
        'workflow_sha256': WORKFLOW_SHA256,
        'candidate_tree_sha256': json.loads((HERE / 'seal.json').read_text())['tree_sha256'],
        'scope': 'restricted data parser, official context allowlists, exact transformation and frozen bindings',
        'official_validator_executed': False,
        'GitHub_workflow_parse_and_Bash_execution': 'pending remote',
        'rustup_installation_and_complete_fixture': 'pending remote'}
    (logs / 'pure-controls.json').write_text(json.dumps(receipt, sort_keys=True, indent=2) + '\n')
    sys.exit(0 if result.wasSuccessful() and not offline_guard.DENIED else 1)
