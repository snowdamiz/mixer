#!/usr/bin/env python3
"""Append independent review cases to exact copied tests without editing old bodies."""
import pathlib
import subprocess

HERE = pathlib.Path(__file__).resolve().parent
subprocess.run(["python3", "-B", str(HERE / "build-review-corpus.py")], check=True)
original = (HERE / "run-1/inputs/probe/probe_test.exs").read_text()
marker = '\nend\n\nif System.get_env("MXAS_FOCUSED")'
assert original.count(marker) == 1
extended = original.replace(marker, "\n\n" + (HERE / "review-cases.exs").read_text() + marker)
(HERE / "probe/probe_test.exs").write_text(extended)
runner = (HERE / "replay-runner.py").read_text()
assert runner.count('expected_total = 83 if args.baseline else 88') == 1
runner = runner.replace('expected_total = 83 if args.baseline else 88', 'expected_total = 83 if args.baseline else 94')
runner = runner.replace('prefix="mxas-display-correction-"', 'prefix="mxas-display-review-"')
(HERE / "adversarial-runner.py").write_text(runner)
