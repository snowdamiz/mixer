"""Second and final bounded repro: terminal delay after actual handler delivery."""
import difflib
import json
import signal
import sys
import time
import unittest
from unittest import mock
from local_support import HERE, original_source, save, workspace, write_guard

write_guard()
source = original_source().decode()
instrumented = source.replace("  clock={'held':None,'offset':0.0,'last':None};timers=[];pending=[]",
    "  clock={'held':None,'offset':0.0,'last':None};timers=[];pending=[];events=[]")
instrumented = instrumented.replace("   return clock['last']",
    "   events.append({'event':'clock','wall':time.monotonic(),'value':clock['last'],'held':clock['held'],'offset':clock['offset']})\n   return clock['last']")
instrumented = instrumented.replace("   state['stage_timer_started']=True",
    "   state['stage_timer_started']=True\n   events.append({'event':'stage-arm','wall':time.monotonic(),'seconds':pending[0]})")
instrumented = instrumented.replace("  receipt=json.loads((out/'receipt.json').read_bytes());self.assertEqual(status,1);self.assertTrue(receipt['cleanup']['deadline_expired'])",
    "  receipt=json.loads((out/'receipt.json').read_bytes());save_observation(HERE,stage,status,state,clock,events,receipt,out)\n  self.assertEqual(status,1);self.assertTrue(receipt['cleanup']['deadline_expired'])")
(HERE / 'reproduction-instrumentation.diff').write_text(''.join(difflib.unified_diff(source.splitlines(True),instrumented.splitlines(True),fromfile='previous-corrected-controls',tofile='observation-only-controls')))
observations = []
for label, injected_terminal_seconds in [('repro-2-terminal-delay', .16)]:
    module, destination = workspace(label, instrumented.encode())
    handler_events = []
    real_signal, real_setitimer = signal.signal, signal.setitimer
    def register(signum, handler):
        if signum == signal.SIGALRM and getattr(handler, '__name__', '') == 'cleanup_alarm':
            def observed(number, frame):
                handler_events.append({'event':'cleanup-handler-entry','wall':time.monotonic()})
                try:
                    return handler(number, frame)
                except BaseException as error:
                    handler_events.append({'event':'cleanup-handler-raise','wall':time.monotonic(),'type':type(error).__name__})
                    raise
            return real_signal(signum, observed)
        return real_signal(signum, handler)
    def timer(which, seconds, interval=0):
        if seconds == 0 and handler_events and injected_terminal_seconds:
            handler_events.append({'event':'injected-terminal-delay','seconds':injected_terminal_seconds,'wall':time.monotonic()})
            time.sleep(injected_terminal_seconds)
        return real_setitimer(which, seconds, interval)
    def capture(here, stage, status, state, clock, events, receipt, out):
        observation = {'label':label,'scope':'Original helper with observational instrumentation; second case deliberately delays terminal cancellation only. No CI latency attribution.', 'status':status,'stage':stage,'state':state,'clock':clock,'events':events,'handler_events':handler_events,'receipt':receipt,'scratch_marker':json.loads((out/'scratch/ownership.json').read_bytes()),'injected_terminal_seconds':injected_terminal_seconds,'retained_before_assertions_and_teardown':True}
        save(here / 'raw-before-assertions.json', observation)
        observations.append(observation)
    module.save_observation = capture
    case = module.RunnerControls('test_postflight_deadline_is_terminal_and_preserves_scratch')
    with mock.patch.object(signal, 'signal', register), mock.patch.object(signal, 'setitimer', timer), mock.patch.object(module.r.platform, 'platform', return_value='pure control; platform probe disabled'), mock.patch.object(module.r.shutil, 'which', return_value=None), mock.patch.object(module.r.subprocess, 'Popen', side_effect=RuntimeError('No child allowed')):
        result = unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite([case]))
    save(destination / 'result.json', {'tests':result.testsRun,'failures':[(str(c),e) for c,e in result.failures],'errors':[(str(c),e) for c,e in result.errors],'timer_disarmed':signal.getitimer(signal.ITIMER_REAL)==(0.0,0.0),'scratch_test_directory_removed':not case.base.exists()})
    if result.errors or (label.endswith('baseline') and result.failures) or (label.endswith('delay') and len(result.failures) != 1):
        raise RuntimeError('Unexpected reproduction result; raw observations preserved')
save(HERE / 'evidence/reproduction-summary.json', [{'label':o['label'],'cleanup_elapsed_seconds':o['receipt']['cleanup_elapsed_seconds'],'handler_events':o['handler_events'],'stage_arm':[e for e in o['events'] if e['event']=='stage-arm'],'injected_terminal_seconds':o['injected_terminal_seconds']} for o in observations])
