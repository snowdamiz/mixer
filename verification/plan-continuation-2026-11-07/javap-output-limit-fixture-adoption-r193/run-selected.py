import importlib.util,json,os,sys,unittest
from pathlib import Path
p=Path(__file__).parent;root=p.parents[2]
def deny_real_process(event,args):
 if event in {'subprocess.Popen','os.killpg','os.kill','os.fork','os.exec','os.posix_spawn'}:raise AssertionError('Selected synthetic control attempted real process operation: '+event)
sys.addaudithook(deny_real_process)
path=root/'scripts/ci/tests/test_android_generated_java_runner.py';spec=importlib.util.spec_from_file_location('r193_candidate',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
names=['test_javap_stdout_ceiling_refuses_one_extra_byte_without_silent_success','test_javap_overflow_unknown_custody_still_takes_priority','test_invalid_stdout_budgets_fail_before_spawning','test_denied_signal_retains_receipt_even_after_child_exits','test_denied_or_unknown_group_observation_cannot_pass','test_live_child_denied_cleanup_still_persists_unknown_terminal_facts','test_one_stream_read_error_cannot_be_reported_as_eof','test_nested_reap_and_selector_cleanup_errors_still_persist','test_command_receipt_write_failure_retains_in_memory_facts','test_exited_fake_parent_with_inherited_pipes_cannot_hang_runner']
r=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(m.RunnerControls(n) for n in names));d={'mode':'optimized' if sys.flags.optimize else 'normal','optimizedFlag':sys.flags.optimize,'passed':r.wasSuccessful(),'testsRun':r.testsRun,'failures':len(r.failures),'errors':len(r.errors),'skips':len(r.skipped),'realProcessOperationsForbidden':True};(p/(d['mode']+'-result.json')).write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d));sys.exit(0 if r.wasSuccessful() else 1)
