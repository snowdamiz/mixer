"""Host-only controls; children are harmless owned Python processes."""
import json
import os
from pathlib import Path
import selectors
import signal
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import observer


BASE = Path(__file__).resolve().parent


class ObserverTests(unittest.TestCase):
    def setUp(self):
        self.scratch = BASE / "scratch"
        self.scratch.mkdir(mode=0o700, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix="case-", dir=self.scratch)
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.output = self.root / "observation"
        self.bundle = self.root / "session.xcresult"

    def run_child(self, code, **options):
        config = dict(cwd=self.root, env=dict(os.environ), output_dir=self.output,
                      owned_result_root=self.root, result_bundle=self.bundle,
                      timeout=2, poll_interval=0.02, post_suite_grace=0.04)
        config.update(options)
        return observer.observe_command([sys.executable, "-B", "-c", code], **config)

    def receipt(self):
        return json.loads((self.output / "observer.json").read_text())

    def events(self, kind):
        return [value for value in map(json.loads, (self.output / "timeline.jsonl").read_text().splitlines())
                if value["kind"] == kind]

    def assert_terminal(self, receipt):
        self.assertIsNotNone(receipt["exitCode"])
        self.assertTrue(all(value["eof"] for value in receipt["streams"].values()))
        self.assertFalse(receipt["nativeAcceptanceGranted"])
        self.assertFalse(receipt["successInferredFromConsoleOrMarkers"])
        self.assertEqual(receipt["PID"], receipt["processGroup"])
        self.assertEqual({value["stream"] for value in self.events("stream-eof")}, {"stdout", "stderr"})
        self.assertEqual(len(self.events("main-process-exit")), 1)

    def test_exited_child_preserves_cwd_exact_env_session_and_output(self):
        child_env = {"OBSERVER_TEST_VALUE": "exact supplied environment"}
        code, stdout, stderr = self.run_child(
            "import os,json,sys; print(json.dumps([os.getpid(),os.getpgrp(),os.getcwd(),dict(os.environ)])); print(' diagnostic ',file=sys.stderr)",
            env=child_env)
        self.assertEqual(code, 0)
        pid, pgid, cwd, actual_env = json.loads(stdout)
        self.assertEqual(pid, pgid)
        self.assertEqual(cwd, str(self.root))
        self.assertEqual(actual_env["OBSERVER_TEST_VALUE"], child_env["OBSERVER_TEST_VALUE"])
        self.assertNotIn("PATH", actual_env)
        self.assertEqual(stderr, "diagnostic")
        receipt = self.receipt()
        self.assertEqual(receipt["PID"], pid)
        self.assertEqual(receipt["environmentMode"], "exact-supplied-mapping")
        self.assert_terminal(receipt)
        self.assertFalse(receipt["cleanup"]["attempted"])
        self.assertFalse(receipt["resultMarkers"]["Info.plist"]["exists"])

    def test_check_false_preserves_nonzero_exit_and_separate_streams(self):
        self.assertEqual(self.run_child("import sys; print('out'); print('err',file=sys.stderr); sys.exit(7)", check=False),
                         (7, "out", "err"))
        self.assert_terminal(self.receipt())

    def test_check_true_rejects_nonzero_without_changing_it(self):
        with self.assertRaises(AssertionError):
            self.run_child("import sys; print('retained'); sys.exit(9)")
        receipt = self.receipt()
        self.assertEqual(receipt["exitCode"], 9)
        self.assertEqual(receipt["failure"]["type"], "AssertionError")
        self.assertEqual((self.output / "stdout.log").read_bytes(), b"retained\n")
        self.assertFalse(receipt["cleanup"]["attempted"])

    def test_suite_finished_live_child_gets_only_one_capture_with_marker_growth(self):
        code = (
            "import pathlib,time,sys; "
            "print(\"Test Suite 'Selected tests' failed at 2026-10-24 19:50:39.800.\",flush=True); "
            "time.sleep(.02); p=pathlib.Path('session.xcresult'); p.mkdir(); "
            "(p/'Info.plist').write_text('diagnostic-marker-only'); "
            "print('after suite',flush=True); time.sleep(.18); sys.exit(4)"
        )
        self.assertEqual(self.run_child(code, check=False)[0], 4)
        receipt = self.receipt()
        self.assert_terminal(receipt)
        self.assertEqual(len(self.events("selected-suite-console-line")), 1)
        self.assertEqual(len(self.events("post-suite-grace-capture")), 1)
        capture = receipt["postSuiteCapture"]
        self.assertIsNone(capture["mainProcessExitCode"])
        self.assertTrue(capture["resultMarkers"]["Info.plist"]["exists"])
        self.assertTrue(any(not value["eof"] for value in capture["streams"].values()))
        self.assertLess(capture["observedSeconds"], receipt["mainProcessExitObservedSeconds"])
        samples = self.events("sample")
        self.assertTrue(any(not value["resultMarkers"]["bundle"]["exists"] for value in samples))
        self.assertGreater(receipt["streams"]["stdout"]["retainedBytes"],
                           samples[0]["streams"]["stdout"]["retainedBytes"])

    def test_child_exit_and_inherited_pipe_eof_are_distinct(self):
        code = (
            "import subprocess,sys; "
            "subprocess.Popen([sys.executable,'-B','-c','import time; time.sleep(.25)']); "
            "print(\"Test Suite 'Selected tests' passed at 2026-10-24 19:50:39.800.\",flush=True)"
        )
        self.assertEqual(self.run_child(code)[0], 0)
        receipt = self.receipt()
        self.assert_terminal(receipt)
        self.assertLess(receipt["mainProcessExitObservedSeconds"], receipt["streams"]["stdout"]["eofSeconds"])
        self.assertGreater(receipt["elapsedSeconds"], .2)
        self.assertIsNotNone(receipt["postSuiteCapture"]["mainProcessExitCode"])
        self.assertFalse(receipt["cleanup"]["attempted"])

    def test_inherited_pipe_timeout_signals_owned_group_even_after_main_exit(self):
        code = (
            "import subprocess,sys; "
            "subprocess.Popen([sys.executable,'-B','-c','import time; time.sleep(30)']); "
            "print('leader exiting',flush=True)"
        )
        with self.assertRaises(subprocess.TimeoutExpired) as caught:
            self.run_child(code, timeout=.18)
        receipt = self.receipt()
        self.assertEqual(caught.exception.timeout, .18)
        self.assertEqual(receipt["exitCode"], 0)
        self.assertEqual(receipt["failure"]["type"], "TimeoutExpired")
        self.assert_terminal(receipt)
        self.assertTrue(receipt["cleanup"]["complete"])
        self.assertEqual(receipt["cleanup"]["targetProcessGroup"], receipt["PID"])
        self.assertEqual([value["signal"] for value in receipt["cleanup"]["signals"]], ["SIGTERM"])

    def test_suite_pass_text_never_shortcuts_timeout_or_cleanup(self):
        code = (
            "import time; print(\"Test Suite 'Selected tests' passed at 2026-10-24 19:50:39.800.\",flush=True); "
            "time.sleep(30)"
        )
        with self.assertRaises(subprocess.TimeoutExpired) as caught:
            self.run_child(code, timeout=.14)
        receipt = self.receipt()
        self.assertIn(b"Selected tests", caught.exception.output)
        self.assertEqual(caught.exception.stderr, b"")
        self.assertEqual(receipt["timeoutSeconds"], .14)
        self.assertEqual(receipt["exitCode"], -signal.SIGTERM)
        self.assert_terminal(receipt)
        self.assertGreaterEqual(receipt["cleanup"]["signals"][0]["elapsedSeconds"], .14)
        self.assertLess(receipt["elapsedSeconds"], 1)

    def test_sigkill_follows_original_eight_second_term_grace(self):
        with self.assertRaises(subprocess.TimeoutExpired):
            self.run_child("import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); print('ready',flush=True); time.sleep(30)",
                           timeout=.14)
        receipt = self.receipt()
        self.assert_terminal(receipt)
        self.assertEqual(receipt["exitCode"], -signal.SIGKILL)
        signals = receipt["cleanup"]["signals"]
        self.assertEqual([value["signal"] for value in signals], ["SIGTERM", "SIGKILL"])
        self.assertGreaterEqual(signals[1]["elapsedSeconds"] - signals[0]["elapsedSeconds"], 8)
        self.assertEqual(receipt["cleanup"]["graceSecondsPerSignal"], 8)
        self.assertTrue(receipt["cleanup"]["complete"])
        self.assertLess(receipt["elapsedSeconds"], 10)

    def test_failure_cleanup_kills_closed_pipe_descendants_even_after_leader_exit(self):
        # Neither EOF nor the leader's exit proves that its owned group is gone.
        descendant = (
            "import os,pathlib,signal,time; "
            "signal.signal(signal.SIGTERM,signal.SIG_IGN); "
            "os.close(1); os.close(2); pathlib.Path('descendant-ready').write_text('ready'); "
            "time.sleep(30)"
        )
        for mode in ("parent-exits-on-TERM", "parent-already-exited-nonzero"):
            with self.subTest(mode=mode):
                self.output = self.root / ("observation-" + mode)
                marker = self.root / "descendant-ready"
                if marker.exists():
                    marker.unlink()
                code = (
                    "import pathlib,subprocess,sys,time; "
                    "subprocess.Popen([sys.executable,'-B','-c'," + repr(descendant) + "]); "
                    "p=pathlib.Path('descendant-ready'); "
                    "exec('while not p.exists(): time.sleep(.002)'); "
                    "print('descendant configured',flush=True); "
                    + ("time.sleep(30)" if mode == "parent-exits-on-TERM" else "sys.exit(7)")
                )
                failure_type = subprocess.TimeoutExpired if mode == "parent-exits-on-TERM" else AssertionError
                with self.assertRaises(failure_type):
                    self.run_child(code, timeout=.4)
                receipt = self.receipt()
                self.assertTrue(marker.exists())
                self.assert_terminal(receipt)
                self.assertEqual(receipt["failure"]["type"], failure_type.__name__)
                signals = receipt["cleanup"]["signals"]
                self.assertEqual([value["signal"] for value in signals], ["SIGTERM", "SIGKILL"])
                self.assertGreaterEqual(signals[1]["elapsedSeconds"] - signals[0]["elapsedSeconds"], 8)
                self.assertEqual(receipt["ownedProcessGroup"]["state"], "absent")
                self.assertTrue(receipt["cleanup"]["complete"])
                self.assertEqual(receipt["cleanup"]["lastGroupObservation"]["state"], "absent")

    def test_successful_exit_and_eof_do_not_claim_owned_group_absence(self):
        descendant = (
            "import os,pathlib,time; os.close(1); os.close(2); "
            "pathlib.Path('descendant-ready').write_text('ready'); "
            "time.sleep(.2); pathlib.Path('descendant-finished').write_text('finished')"
        )
        code = (
            "import pathlib,subprocess,sys,time; "
            "subprocess.Popen([sys.executable,'-B','-c'," + repr(descendant) + "]); "
            "p=pathlib.Path('descendant-ready'); exec('while not p.exists(): time.sleep(.002)')"
        )
        try:
            self.assertEqual(self.run_child(code)[0], 0)
            receipt = self.receipt()
            self.assert_terminal(receipt)
            self.assertEqual(receipt["ownedProcessGroup"]["state"], "present-or-zombies")
            self.assertFalse(receipt["cleanup"]["attempted"])
            self.assertIsNone(receipt["cleanup"]["complete"])
        finally:
            # The harmless same-group child exits naturally; wait only on its
            # own output marker before removing this test's temporary directory.
            import time
            until = time.monotonic() + 2
            while not (self.root / "descendant-finished").exists() and time.monotonic() < until:
                time.sleep(.01)
            self.assertTrue((self.root / "descendant-finished").exists())

    def test_split_utf8_and_crlf_match_original_communicate_text_semantics(self):
        code = (
            "import os,time; "
            "os.write(1,b' a\\r'); time.sleep(.02); "
            "os.write(1,b'\\nb\\rc\\n\\xe2'); time.sleep(.02); "
            "os.write(1,b'\\x82'); time.sleep(.02); os.write(1,b'\\xac '); "
            "os.write(2,b' err\\r'); time.sleep(.02); os.write(2,b'\\n '); "
            "os.write(1,b'\\r')"
        )
        actual = self.run_child(code, encoding="utf-8")
        expected = subprocess.run([sys.executable, "-B", "-c", code], cwd=self.root,
                                  env=dict(os.environ), capture_output=True, text=True,
                                  encoding="utf-8", timeout=2, start_new_session=True)
        self.assertEqual(actual, (expected.returncode, expected.stdout.strip(), expected.stderr.strip()))
        self.assertEqual(actual[1], "a\nb\nc\n€")
        self.assertIn(b"\r\n", (self.output / "stdout.log").read_bytes())

    def test_invalid_encoding_output_retains_raw_failure_and_cleans_child(self):
        with self.assertRaises(UnicodeDecodeError):
            self.run_child("import os,time; os.write(1,b'raw-before-error\\xff'); time.sleep(30)", encoding="utf-8")
        receipt = self.receipt()
        self.assertEqual(receipt["failure"]["type"], "UnicodeDecodeError")
        self.assertTrue(receipt["streams"]["stdout"]["readerFailed"])
        self.assertEqual((self.output / "stdout.log").read_bytes(), b"raw-before-error\xff")
        self.assertTrue(receipt["cleanup"]["complete"])
        self.assert_terminal(receipt)

    def test_each_stream_overflow_fails_closed_with_bounded_retained_bytes(self):
        for descriptor, stream in ((1, "stdout"), (2, "stderr")):
            with self.subTest(stream=stream):
                self.output = self.root / ("observation-" + stream)
                with self.assertRaises(observer.OutputLimitExceeded):
                    self.run_child("import os,time; os.write(" + str(descriptor) + ",b'x'*2000); time.sleep(30)",
                                   max_output_bytes_per_stream=1024)
                receipt = self.receipt()
                self.assertEqual(receipt["failure"]["type"], "OutputLimitExceeded")
                self.assertEqual((self.output / (stream + ".log")).stat().st_size, 1024)
                self.assertEqual(receipt["streams"][stream]["retainedBytes"], 1024)
                self.assertGreater(receipt["streams"][stream]["observedBytes"], 1024)
                self.assertTrue(receipt["cleanup"]["complete"])

    def test_reader_oserror_is_recorded_and_propagated(self):
        read_fd, write_fd = os.pipe()
        self.addCleanup(os.close, write_fd)
        with os.fdopen(read_fd, "rb") as pipe:
            self.output.mkdir()
            stream = observer._Stream("stdout", pipe, self.output, "utf-8", 1024)
            with selectors.DefaultSelector() as selector:
                selector.register(pipe, selectors.EVENT_READ, stream)
                try:
                    with mock.patch.object(observer.os, "read", side_effect=OSError("owned descriptor failure")):
                        with self.assertRaisesRegex(OSError, "owned descriptor failure"):
                            stream.read_once(.1, selector)
                    self.assertTrue(stream.failed)
                    self.assertEqual(stream.errors[0]["type"], "OSError")
                finally:
                    stream.log.close()

    def test_result_bundle_symlink_is_not_followed(self):
        outside = self.root / "other-owned-output"
        outside.mkdir()
        (outside / "Info.plist").write_text("must not be read")
        self.run_child("import os,time; os.symlink('other-owned-output','session.xcresult'); time.sleep(.07)")
        receipt = self.receipt()
        self.assertEqual(receipt["resultMarkers"]["bundle"]["kind"], "symlink")
        self.assertFalse(receipt["resultMarkers"]["Info.plist"]["exists"])

    def test_info_plist_symlink_is_not_followed(self):
        (self.root / "other-owned-marker").write_text("must not be read")
        self.run_child("import pathlib,os,time; p=pathlib.Path('session.xcresult'); p.mkdir(); os.symlink('../other-owned-marker',p/'Info.plist'); time.sleep(.07)")
        marker = self.receipt()["resultMarkers"]["Info.plist"]
        self.assertTrue(marker["exists"])
        self.assertEqual(marker["kind"], "symlink")

    def test_invalid_configuration_never_launches_a_child(self):
        cases = [dict(timeout=601), dict(timeout=0), dict(timeout=float("nan")),
                 dict(timeout=float("inf")), dict(timeout=True), dict(poll_interval=.001),
                 dict(poll_interval=2), dict(post_suite_grace=601),
                 dict(max_output_bytes_per_stream=0), dict(max_output_bytes_per_stream=True),
                 dict(max_output_bytes_per_stream=observer.MAX_OUTPUT_BYTES + 1),
                 dict(result_bundle=self.root / "nested" / "session.xcresult"),
                 dict(result_bundle=self.root / "not-a-result"), dict(cwd=Path("relative"))]
        with mock.patch.object(observer.subprocess, "Popen") as launch:
            for options in cases:
                with self.subTest(options=options), self.assertRaises(ValueError):
                    self.run_child("raise SystemExit('must not execute')", **options)
            launch.assert_not_called()
        self.assertFalse(self.output.exists())

    def test_existing_result_or_output_is_rejected_before_launch(self):
        self.bundle.mkdir()
        with mock.patch.object(observer.subprocess, "Popen") as launch:
            with self.assertRaisesRegex(ValueError, "must be absent"):
                self.run_child("pass")
            launch.assert_not_called()
        self.bundle.rmdir()
        self.output.mkdir()
        with mock.patch.object(observer.subprocess, "Popen") as launch:
            with self.assertRaises(FileExistsError):
                self.run_child("pass")
            launch.assert_not_called()

    def test_symlink_owned_root_is_rejected_before_launch(self):
        alias = self.root / "root-alias"
        alias.symlink_to(self.root, target_is_directory=True)
        with mock.patch.object(observer.subprocess, "Popen") as launch:
            with self.assertRaisesRegex(ValueError, "canonical"):
                self.run_child("pass", owned_result_root=alias, result_bundle=alias / "session.xcresult")
            launch.assert_not_called()

    def test_launch_failure_has_receipt_and_preserves_type(self):
        with mock.patch.object(observer.subprocess, "Popen", side_effect=FileNotFoundError("owned test executable missing")):
            with self.assertRaises(FileNotFoundError):
                self.run_child("pass")
        receipt = self.receipt()
        self.assertIsNone(receipt["PID"])
        self.assertEqual(receipt["failure"]["type"], "FileNotFoundError")
        self.assertFalse(receipt["cleanup"]["attempted"])

    def test_keyboard_interrupt_is_preserved_after_owned_cleanup(self):
        real_select = selectors.DefaultSelector.select
        interrupted = False

        def select_once_interrupt(selector, timeout=None):
            nonlocal interrupted
            if not interrupted:
                interrupted = True
                raise KeyboardInterrupt("owned host interruption")
            return real_select(selector, timeout)

        with mock.patch.object(selectors.DefaultSelector, "select", select_once_interrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.run_child("import time; time.sleep(30)")
        receipt = self.receipt()
        self.assertEqual(receipt["failure"]["type"], "KeyboardInterrupt")
        self.assertTrue(receipt["cleanup"]["complete"])
        self.assert_terminal(receipt)

    def test_observer_read_callback_failure_still_cleans_owned_child(self):
        # An observer fault after output fails closed and retains its original
        # type after cleaning the owned child.
        real_read = observer._Stream.read_once
        injected = False

        def read_then_fail(stream, now, selector, **options):
            nonlocal injected
            real_read(stream, now, selector, **options)
            if not options.get("cleanup") and stream.observed and not injected:
                injected = True
                raise OSError("injected observer failure")

        with mock.patch.object(observer._Stream, "read_once", read_then_fail):
            with self.assertRaisesRegex(OSError, "injected observer failure"):
                self.run_child("import time; print('ready',flush=True); time.sleep(30)")
        receipt = self.receipt()
        self.assertEqual(receipt["failure"]["type"], "OSError")
        self.assertTrue(receipt["cleanup"]["complete"])
        self.assert_terminal(receipt)


if __name__ == "__main__":
    unittest.main(verbosity=2)
