#!/usr/bin/env python3
"""Adapt the reviewed F02 stock delivery lifecycle to the distinct F08 transaction assertions."""
import hashlib
import os
from pathlib import Path
import subprocess
import sys

F02 = "3e6e884b7ddc60507bd008bde38fa8ecb1fdb4db"
F02_PATH = "tests/integration/fieldlog-d8-f02-signed"
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tests/integration/fieldlog-entry-sync"))

ROOF = "F0800000-0000-4000-8000-000000000004"
DELIVERY = "F0800000-0000-4000-8000-000000000005"
PROJECT = "F0800000-0000-4000-8000-000000000002"
SEED = "fc96e23f6ae6cfdad5d14aca37c9890fc358c4268a3464eaf65e2909a546f239"


def f02_source(name):
    return subprocess.check_output(
        ["git", "show", f"{F02}:{F02_PATH}/{name}"], cwd=ROOT, env=dict(os.environ, GIT_NO_LAZY_FETCH="1"), text=True,
    )


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise RuntimeError(f"F02 driver seam changed: {old}")
    return text.replace(old, new, 1)


def require(condition, reason):
    if not condition:
        raise RuntimeError(reason)


def release_source():
    source = f02_source("Release.swift")
    for old, new in [
        ("d8-f02", "d8-f08"), ("fieldlog-f02", "fieldlog-f08"), ("f02.control", "f08.control"),
        ('platform: "ios"', 'platform: "android"'),
        ("1587d2d4f02ab2dad9914df97f878727dd622296", "00c8fe0400bc9a06242371ce7b02cd440f64f31e"),
        ("32c063e748e48db391e878890edeb247a71d08d9", "c6562ba80b992016c0c963cf4c67a59f1f605fd0"),
    ]:
        require(old in source, f"Missing pinned release seam: {old}")
        source = source.replace(old, new)
    return replace_once(source, 'var identity = try object(read(fixtures, "identity.json"))',
        'var identity = try object(read(fixtures, "identity.json"))\n'
        '        identity["platform"] = ["os": "android", "architecture": "arm64", "environment": "simulator",\n'
        '                                "minimum_os": "28", "target": "aarch64-unknown-linux-android28"]')


def verify_phases(phases):
    prior, completed, reordered, rollback, offline = phases.values()
    require([row["revision"] for row in phases.values()] == [3, 4, 5, 5, 5], "Cold readback revisions")
    require(len({row["pid"] for row in phases.values()}) == 5 and
            len({row["launch"] for row in phases.values()}) == 5, "Distinct cold processes and launches")
    require(prior["artifact"] == rollback["artifact"] == offline["artifact"] != reordered["artifact"]
            and completed["artifact"] == reordered["artifact"]
            and completed["candidate"] == reordered["candidate"] == rollback["previous"]
            and rollback["candidate"] == offline["candidate"] != prior["candidate"]
            and completed["previous"] == prior["candidate"], "Rollback candidate and artifact chain")
    require([row["writes"] for row in phases.values()] == [[], ["complete-" + ROOF], ["move-up-" + DELIVERY], [], []]
            and all(row["browseWorkspaceUnchanged"] and row["retired"] for row in phases.values()),
            "Separate writes, read-only browsing and closed guest owners")
    require(prior["workspaceSHA256"] == SEED
            and reordered["workspaceSHA256"] == rollback["workspaceSHA256"] == offline["workspaceSHA256"],
            "Exact seed and stable rollback/offline bytes")
    require([row["coldOrder"] for row in phases.values()] ==
            [[ROOF, DELIVERY], [ROOF, DELIVERY], *([[DELIVERY, ROOF]] * 3)]
            and [row["completed"] for row in phases.values()] == [[], *([[ROOF]] * 4)],
            "F08 completion and independent move")
    require(completed["outbox"][:-1] == prior["outbox"]
            and reordered["outbox"][:-1] == completed["outbox"]
            and reordered["outbox"] == rollback["outbox"] == offline["outbox"]
            and len({event["id"] for event in offline["outbox"]}) == 5,
            "Exact prior outbox and cold event lineage")
    require([(row["kind"], row["recordID"], row["revision"]) for row in offline["outbox"][3:]]
            == [("taskSaved", ROOF, 4), ("taskOrderChanged", PROJECT, 5)], "Linked writes")


def adapt_and_run():
    source = f02_source("journey.py")
    source = replace_once(source, 'args.guests, args.vm], env)', 'args.guests, args.vm, args.seed], env)')
    source = replace_once(source, '["down", "up"]', '["complete", "reorder"]')
    source = replace_once(source, '"f02-host"', '"f08-host"')
    source = replace_once(source, '"local F02 restores prior"', '"local F08 restores prior"')
    start = source.index('        prior, down, up, rollback, offline = phases.values()')
    end = source.index('        report["status"] = "passed"', start)
    source = source[:start] + '        verify_f08_phases(phases)\n' + source[end:]
    namespace = {"__name__": "f02_driver", "__file__": __file__}
    exec(compile(source, f"{F02}:{F02_PATH}/journey.py", "exec"), namespace)
    namespace["verify_f08_phases"] = verify_phases
    if len(sys.argv) != 9:
        raise SystemExit("usage: journey.py CONTROL FIXTURES GUESTS VM ORIGIN CLI OUTPUT SEED")
    arguments = namespace["argparse"].Namespace(**dict(zip(
        ("control", "fixtures", "guests", "vm", "origin", "cli", "output", "seed"),
        (Path(arg).resolve() for arg in sys.argv[1:]), strict=True,
    )))
    if hashlib.sha256(arguments.seed.read_bytes()).hexdigest() != SEED:
        raise SystemExit("F08 seed SHA-256 mismatch")
    namespace["run_journey"](arguments)


if __name__ == "__main__":
    os.umask(0o077)
    if sys.argv[1:] == ["--release-source"]:
        print(release_source(), end="")
    else:
        adapt_and_run()
