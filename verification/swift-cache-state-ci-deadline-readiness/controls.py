"""One-shot controls for the stage-ready deadline test, not the product runner."""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import unittest

OUT = Path(__file__).resolve().parent


def digest(path):
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def child(mode):
    source = OUT / "control-cases" / mode
    spec = importlib.util.spec_from_file_location("deadline_test", source / "test_runner.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if mode == "slow-postflight":
        original = module.r.verify_pack
        calls = []

        def slow(base):
            calls.append(str(base))
            if len(calls) == 3:
                time.sleep(.4)
            return original(base)

        module.r.verify_pack = slow
    suite = unittest.TestSuite([module.RunnerControls("test_retention_deadline_is_terminal_and_preserves_scratch")])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


def parent():
    assert not (OUT / "additional-controls.json").exists(), "One-shot controls"
    source = OUT / "candidate-source"
    manifest = json.loads((OUT / "candidate-source.json").read_bytes())
    for row in manifest["members"]:
        assert digest(OUT / row["path"]) == {k: row[k] for k in ("bytes", "sha256")}
    substitutions = {
        "missing-cleanup-timer": (
            "signal.signal(signal.SIGALRM,cleanup_alarm);signal.setitimer(signal.ITIMER_REAL,max(0.000001,cleanup_deadline-time.monotonic()))",
            "signal.signal(signal.SIGALRM,cleanup_alarm);signal.setitimer(signal.ITIMER_REAL,0)",
        ),
        "wrong-alarm-handler": (
            "def cleanup_alarm(signum,frame):raise CleanupDeadlineExpired('Fixed cleanup deadline exhausted')",
            "def cleanup_alarm(signum,frame):raise TimeoutError('Deliberately wrong test alarm handler')",
        ),
    }
    records = []
    for mode in ["slow-postflight", *substitutions]:
        folder = OUT / "control-cases" / mode
        folder.mkdir(parents=True)
        for row in manifest["members"]:
            relative = Path(row["path"]).relative_to("candidate-source")
            target = folder / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((source / relative).read_bytes())
        (folder / "logs").mkdir()
        if mode in substitutions:
            runner = folder / "check_cache_state.py"
            old, new = substitutions[mode]
            text = runner.read_text()
            assert text.count(old) == 1
            runner.write_text(text.replace(old, new))
        argv = [sys.executable, "-B", str(Path(__file__).resolve()), "--child", mode]
        started = time.monotonic()
        with (folder / "stdout").open("xb") as stdout, (folder / "stderr").open("xb") as stderr:
            process = subprocess.Popen(argv, stdout=stdout, stderr=stderr, start_new_session=True)
            try:
                code = process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
                raise
        expected = 0 if mode == "slow-postflight" else 1
        record = {"mode": mode, "argv": argv, "exit": code, "expected_exit": expected,
                  "elapsed_seconds": time.monotonic() - started, "child_waited": True,
                  "runner": digest(folder / "check_cache_state.py"),
                  "test_source": digest(folder / "test_runner.py"),
                  "stdout": digest(folder / "stdout"), "stderr": digest(folder / "stderr")}
        (folder / "command.json").write_text(json.dumps(record, indent=2) + "\n")
        records.append(record)
        assert code == expected, record
        if expected:
            assert b"FAILED (failures=1)" in (folder / "stderr").read_bytes()
    report = {"at": datetime.now(timezone.utc).isoformat(), "python": sys.version,
              "controls": records, "passed": True,
              "scope": "Test-only stage readiness and required real-timer/handler detection; no native run or compiler fixture",
              "production_runner_unchanged": True}
    (OUT / "additional-controls.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"passed": True, "controls": len(records)}))


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--child":
        raise SystemExit(child(sys.argv[2]))
    assert len(sys.argv) == 1
    parent()
