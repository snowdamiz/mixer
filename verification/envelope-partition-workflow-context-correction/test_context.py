#!/usr/bin/env python3
"""Guarded narrow context-placement regression controls; no runtime qualification."""
from pathlib import Path
import sys
HERE = Path(__file__).resolve().parent
import offline_guard
offline_guard.install(HERE)
from copy import deepcopy
import io
import json
import tempfile
import unittest
import admission
import context_placement as context
import verify_candidate as verifier


class ContextControls(unittest.TestCase):
    def setUp(self):
        self.source = (HERE / 'workflow-proposal.yml').read_text()
        self.original = context.parse((HERE / 'frozen-parent-workflow.yml').read_text())
        self.document = context.parse(self.source)
        self.job = self.document['jobs']['one-complete-host-fixture']

    def test_original_job_runner_environment_failure_is_reproduced(self):
        with self.assertRaisesRegex(ValueError, 'Context runner unavailable at jobs.*env.MIXER_RUNNER_ENVIRONMENT'):
            context.validate(self.original)

    def test_arbitrary_runner_properties_are_rejected_at_job_env(self):
        for prop in ('environment', 'temp', 'os', 'arch', 'name', 'anything_else'):
            changed = deepcopy(self.document)
            changed['jobs']['one-complete-host-fixture']['env']['ARBITRARY_KEY'] = '${{ runner.' + prop + ' }}'
            with self.subTest(property=prop), self.assertRaisesRegex(ValueError, 'Context runner unavailable'):
                context.validate(changed)

    def test_runner_is_allowed_only_on_both_context_consuming_steps(self):
        result = context.validate_contract(self.document, self.original)
        locations = [row['location'] for row in result['expression_references']
                     if row['expression'] == 'runner.environment']
        self.assertEqual(locations, [
            'jobs.one-complete-host-fixture.steps.2.env.MIXER_RUNNER_ENVIRONMENT',
            'jobs.one-complete-host-fixture.steps.3.env.MIXER_RUNNER_ENVIRONMENT'])
        self.assertNotIn('MIXER_RUNNER_ENVIRONMENT', self.job['env'])
        self.assertFalse(result['official_validator_executed'])

    def test_either_missing_or_changed_step_environment_is_rejected(self):
        for index in (2, 3):
            for mutate in (lambda step: step.pop('env'),
                           lambda step: step['env'].update(MIXER_RUNNER_ENVIRONMENT='github-hosted'),
                           lambda step: step['env'].update(MIXER_RUNNER_ENVIRONMENT='${{ runner.temp }}')):
                changed = deepcopy(self.document)
                mutate(changed['jobs']['one-complete-host-fixture']['steps'][index])
                with self.subTest(step=index), self.assertRaisesRegex(ValueError, 'authorized context correction'):
                    context.validate_contract(changed, self.original)

    def test_runner_environment_on_wrong_step_is_rejected(self):
        self.job['steps'][1]['env'] = self.job['steps'][2].pop('env')
        with self.assertRaisesRegex(ValueError, 'authorized context correction'):
            context.validate_contract(self.document, self.original)

    def test_workflow_environment_regression_is_rejected(self):
        self.document['env'] = dict(context.RUNNER_ENV)
        with self.assertRaisesRegex(ValueError, 'Context runner unavailable at env'):
            context.validate(self.document)

    def test_job_inputs_and_literal_policies_remain_exact(self):
        self.assertEqual(self.job['env'], {
            'MIXER_REVIEWED_SHA': '${{ inputs.reviewed_sha }}',
            'RUSTUP_AUTO_INSTALL': '0', 'PYTHONDONTWRITEBYTECODE': '1'})
        for key in self.job['env']:
            changed = deepcopy(self.document)
            changed['jobs']['one-complete-host-fixture']['env'][key] = 'changed'
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'authorized context correction'):
                context.validate_contract(changed, self.original)

    def test_routing_and_all_other_workflow_semantics_are_exact(self):
        self.assertNotIn(context.PARENT, self.source)
        context.validate_contract(self.document, self.original)
        mutations = [lambda job: job.update(**{'timeout-minutes': 21}),
                     lambda job: job['steps'].append(deepcopy(job['steps'][2])),
                     lambda job: job['steps'][3].pop('if'),
                     lambda job: job['steps'][2].update(**{'continue-on-error': True}),
                     lambda job: job['steps'][2].update(run=job['steps'][2]['run'].replace('begin', 'verify'))]
        for mutation in mutations:
            changed = deepcopy(self.document)
            mutation(changed['jobs']['one-complete-host-fixture'])
            with self.subTest(mutation=mutation), self.assertRaisesRegex(ValueError, 'authorized context correction'):
                context.validate_contract(changed, self.original)

    def test_duplicate_yaml_and_unsupported_expression_fail_closed(self):
        with self.assertRaisesRegex(ValueError, 'Duplicate mapping key'):
            context.parse(self.source.replace('    runs-on: macos-15',
                                             '    runs-on: macos-15\n    runs-on: macos-15'))
        for expression in ("${{ runner['environment'] }}", '${{ unknown.environment }}',
                           '${{ runner.environment', '${{ runner.environment || true }}'):
            changed = deepcopy(self.document)
            changed['jobs']['one-complete-host-fixture']['env']['KEY'] = expression
            with self.subTest(expression=expression), self.assertRaises(ValueError):
                context.validate(changed)

    def test_frozen_parent_copies_and_corrected_source_closure(self):
        result = verifier.verify()
        self.assertTrue(result['corrected_closure_seal_verified'])
        self.assertFalse(result['installed_workflow_matches'])
        self.assertFalse(result['official_validator_executed'])
        self.assertEqual(result['frozen_parent_seal_sha256'], verifier.PARENT_SEAL)

    def test_here_local_seal_rejects_corrected_member_drift(self):
        with tempfile.TemporaryDirectory(prefix='pure-', dir=HERE) as name:
            copy = Path(name)
            for row in json.loads((HERE / 'seal.json').read_bytes())['members']:
                target = copy / row['path']
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((HERE / row['path']).read_bytes())
            (copy / 'seal.json').write_bytes((HERE / 'seal.json').read_bytes())
            previous = admission.HERE
            try:
                admission.HERE = copy
                admission.verify_sources()
                (copy / 'workflow-proposal.yml').write_text(self.source + '\n')
                with self.assertRaisesRegex(RuntimeError, 'Review source differs: workflow-proposal.yml'):
                    admission.verify_sources()
            finally:
                admission.HERE = previous

    def test_installed_workflow_comparison_uses_corrected_sibling(self):
        real_raw = admission.raw
        installed = admission.ROOT / admission.WORKFLOW
        for data, passed in ((self.source.encode(), True),
                             ((HERE / 'frozen-parent-workflow.yml').read_bytes(), False)):
            def controlled_raw(path):
                return data if path == installed else real_raw(path)
            admission.raw = controlled_raw
            try:
                if passed:
                    admission.verify_sources(installed=True)
                else:
                    with self.assertRaisesRegex(RuntimeError, 'Installed workflow differs'):
                        admission.verify_sources(installed=True)
            finally:
                admission.raw = real_raw

    def test_no_real_nested_runtime_operation_attempted(self):
        self.assertEqual(offline_guard.DENIED, [])


if __name__ == '__main__':
    output = io.StringIO()
    result = unittest.TextTestRunner(stream=output, verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(ContextControls))
    text = output.getvalue()
    print(text, end='')
    logs = HERE / 'logs'
    logs.mkdir(exist_ok=True)
    (logs / 'context-controls.stdout').write_text(text)
    report = {'schema': 1, 'command': 'python3 -B verification/envelope-partition-workflow-context-correction/test_context.py',
              'python': sys.version, 'interpreter': sys.executable, 'tests_run': result.testsRun,
              'failures': len(result.failures), 'errors': len(result.errors), 'skipped': len(result.skipped),
              'success': result.wasSuccessful(), 'denied_runtime_attempts': offline_guard.DENIED,
              'official_validator_executed': False, 'scope': 'restricted data parsing, frozen context allowlists, exact transform and source closure only',
              'owned_scratch_absent': not any(HERE.glob('pure-*'))}
    (logs / 'context-controls.json').write_text(json.dumps(report, sort_keys=True, indent=2) + '\n')
    raise SystemExit(not (result.wasSuccessful() and not offline_guard.DENIED))
