#!/usr/bin/env python3
"""Guarded Release-only admission controls; no live child or native runtime."""
import unittest.mock
import offline
offline.install()
import ast, contextlib, io, json, os, signal, socket, sys, unittest
from pathlib import Path
from unittest import mock
import admit as a
import bounded_commands as b
import host_controls as h
import verify as v

HERE = Path(__file__).resolve().parent
TRACE = 'control_trace close config=Limits { limit: 1 }/ExecutionBudget { limit: 1 }/CacheBudget { limit: 1 }/true/1/1 constructor=Ok allocations=(0, 0, 0)'


class Controls(unittest.TestCase):
    def test_guard_before_subject_imports_and_all_live_effects_denied(self):
        for call in (b.subprocess.Popen,b.subprocess.run,os.waitpid,os.setsid,os.killpg,os.getpgid,signal.setitimer,signal.signal,socket.socket,b.resource.getrusage):
            self.assertIs(call,offline.denied)
        self.assertEqual(offline.ATTEMPTS,[])

    def test_exact_source_parser_ast_workflow_and_hash_bindings(self):
        result=v.check(verify_seal=False)
        self.assertTrue(result['sourceOnly']);self.assertFalse(result['installedWorkflowChecked'])

    def test_manual_first_attempt_and_fixed_profile_fail_closed(self):
        env={'GITHUB_ACTIONS':'true','RUNNER_ENVIRONMENT':'github-hosted','GITHUB_EVENT_NAME':'workflow_dispatch','GITHUB_RUN_ATTEMPT':'1','GITHUB_REPOSITORY':'snowdamiz/mixer','GITHUB_SHA':'a'*40,'MIXER_PIN_BITMAP_RELEASE_SELECTION':a.PROFILE}
        for key,value,error in [('GITHUB_RUN_ATTEMPT','2','first attempt'),('GITHUB_EVENT_NAME','push','first attempt'),('MIXER_PIN_BITMAP_RELEASE_SELECTION','pin-bitmap-lint-regression-v1','profile selection'),('GITHUB_REPOSITORY','other/project','source revision')]:
            with self.subTest(key=key),mock.patch.dict(os.environ,{**env,key:value},clear=True):
                with self.assertRaisesRegex(RuntimeError,error):a.hosted()

    def test_prior_packet_seal_refuses_before_attribution_or_any_child(self):
        with mock.patch.object(a,'sha',return_value='changed'):
            with self.assertRaisesRegex(RuntimeError,'Prior actual review seal changed'):a.prior_evidence()

    def test_historical_results_cannot_be_relabelled_as_new_runs(self):
        prior=a.prior_evidence()
        self.assertEqual(prior['runID'],40824584975)
        self.assertTrue(prior['oldAllowanceConsumed']);self.assertFalse(prior['historicalResultsAreNewRuns'])
        self.assertEqual(prior['Debug']['passed'],699);self.assertFalse(prior['Debug']['hostParserAdmitted'])
        self.assertEqual(prior['Release'],{'status':'previously-unrun','observedPasses':None})
        self.assertFalse(prior['canonicalPromotionSelected']);self.assertFalse(prior['GAQualified'])

    def with_host_fixture(self, callback):
        case=h.Controls('test_mock_complete_sequence_retains_outputs_and_cleans_scratch')
        case.setUp()
        try:return callback(case)
        finally:case.tearDown()

    def test_terminal_parser_refusal_keeps_postflights_and_owned_cleanup(self):
        text=h.passed_text().replace('699 passed','698 passed')
        def run(case):
            with mock.patch.object(h,'passed_text',return_value=text):result,error,record,out,calls=case.execute_mock()
            self.assertIsNotNone(error);self.assertEqual(calls,['compiler-identity','node-identity','release-regression'])
            self.assertEqual(record['status'],'failed');self.assertNotIn('ReleasePassed',record)
            self.assertTrue(record['commands'][-1]['sourcePostflight']['verified']);self.assertTrue(record['commands'][-1]['binaryPostflight']['verified'])
            self.assertTrue(record['cleanup']['ownedScratchRemoved']);self.assertFalse((out/'scratch').exists())
            self.assertFalse((out/'release-regression.json').exists())
        self.with_host_fixture(run)

    def test_release_sequence_executes_no_Debug_formatter_or_Clippy(self):
        def run(case):
            result,error,record,out,calls=case.execute_mock()
            self.assertIsNone(error);self.assertEqual(calls,['compiler-identity','node-identity','release-regression'])
            self.assertEqual(record['maxChildren'],3);self.assertEqual(record['activeSeconds'],660);self.assertEqual(record['cleanupSeconds'],60)
            self.assertEqual(record['unchangedSourceClosure'],a.closure(json.loads((out/'source-manifest.json').read_text())['candidateFiles']))
            self.assertEqual(record['ReleasePassed'],699);self.assertNotIn('DebugPassed',record)
            self.assertFalse((out/'format').exists());self.assertFalse((out/'clippy-candidate.json').exists())
        self.with_host_fixture(run)

    def test_whitespace_doctest_name_and_serialized_split_terminal(self):
        text=h.passed_text().replace('test fixture_0 ... ok','test src/mod.rs - crate::Type (line 12) - compile fail ... ok')
        text=text.replace('test fixture_1 ... ok','test shared_control_close_partial_effects ... control_observer serialized lane\n'+TRACE+'\nok')
        result=a.test_evidence(text)
        self.assertEqual(result['passed'],699);self.assertEqual(len(result['terminals']),699)

    def test_split_terminal_malformed_orphan_missing_duplicate_or_non_ok_refuses(self):
        base=h.passed_text()
        split='test shared_control_close_partial_effects ... control_observer serialized lane\n'+TRACE+'\nok'
        for text in (base.replace('test fixture_0 ... ok',split.replace('\nok','\nFAILED')),base.replace('test fixture_0 ... ok',split.replace('\nok','')),base.replace('test fixture_0 ... ok',split.replace(TRACE,'unexpected')),base+'ok\n',base.replace('test fixture_0 ... ok','test '+a.ORACLES[0]+' ... ok')):
            with self.subTest(suffix=text[-90:]),self.assertRaises(RuntimeError):a.test_evidence(text)

    def test_group_running_summary_and_terminal_count_must_all_agree(self):
        for text in (h.passed_text().replace('running 699 tests','running 698 tests'),h.passed_text().replace('running 699 tests','running 699 test'),h.passed_text().replace('running 699 tests\n',''),h.passed_text()+'test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0s\n'):
            with self.assertRaises(RuntimeError):a.test_evidence(text)

    def test_original_source_node_custody_functions_are_byte_identical(self):
        before=v.functions((v.BASE/'admit.py').read_text());after=v.functions((HERE/'admit.py').read_text())
        names=('inputs','bound','binary_row','choose_node','check_binaries','arm_environment','inventory','exact_source','cargo_configs_absent','component_evidence')
        for name in names:self.assertEqual(before[name],after[name])
        self.assertEqual((HERE/'bounded_commands.py').read_bytes(),(v.BASE/'bounded_commands.py').read_bytes())

    def test_all_six_binary_identities_remain_observed_before_and_after(self):
        self.assertEqual(a.TOOLS,('rustc','rustfmt','cargo','cargo-clippy','clippy-driver'))
        source=v.functions((HERE/'admit.py').read_text())
        self.assertIn("'count': 6",source['check_binaries'])
        self.assertEqual(source['checked_command'].count('check_binaries(tools, node, paths)'),2)

    def test_finite_active_cleanup_and_no_retry_paths(self):
        source=v.functions((HERE/'admit.py').read_text())
        self.assertIn('signal.setitimer(signal.ITIMER_REAL, ACTIVE_SECONDS)',source['execute'])
        self.assertIn('signal.setitimer(signal.ITIMER_REAL, CLEANUP_SECONDS)',source['execute'])
        self.assertIn('signal.setitimer(signal.ITIMER_REAL, 0)',source['execute'])
        self.assertIn("'automaticRetry': False",source['execute'])
        self.assertEqual(source['execute'].count('for spec in plan:'),1)


if __name__ == '__main__':
    stream=io.StringIO();result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Controls))
    sys.stderr.write(stream.getvalue())
    record={'schema':1,'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skips':len(result.skipped),'pythonVersion':sys.version,'guardBeforeSubjectImports':True,'realProcessSessionGroupSignalTimerWaitSocketCalls':0,'liveApiAttempts':offline.ATTEMPTS,'RustRuns':0,'NodeRuns':0,'mockedCustodyIsLiveEvidence':False,'scratchRemaining':[p.name for p in HERE.glob('pure-*')]}
    (HERE/'controls-result.json').write_text(json.dumps(record,sort_keys=True,indent=2)+'\n')
    if not result.wasSuccessful():raise SystemExit(1)
