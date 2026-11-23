#!/usr/bin/env python3
"""Run an Android-scoped signed F09 projection through the F02 stock delivery path."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
F08_REV = "36bd74d936bef076b3e1fb23167e4385fbfc3191"
F08_PATH = "tests/integration/fieldlog-d8-f08-signed/journey.py"
sys.path.insert(0, str(ROOT / "tests/integration/fieldlog-entry-sync"))


def pinned_f08():
    source = subprocess.check_output(["git", "show", f"{F08_REV}:{F08_PATH}"],
                                     cwd=ROOT, env={**os.environ, "GIT_NO_LAZY_FETCH": "1"}, text=True)
    namespace = {"__name__": "f08_driver", "__file__": __file__}
    exec(compile(source, f"{F08_REV}:{F08_PATH}", "exec"), namespace)
    return namespace


def verify_phases(phases, output):
    prior, move, successor, rollback, offline = phases.values()
    rows = list(phases.values())
    require([row["revision"] for row in rows] == [1, 2, 2, 2, 2], "One workspace revision")
    require([row["outboxCount"] for row in rows] == [27, 28, 28, 28, 28], "One outbox append")
    require(len({row["pid"] for row in rows}) == len({row["launch"] for row in rows}) == 5,
            "Five distinct cold processes and launches")
    require(prior["artifact"] == rollback["artifact"] == offline["artifact"] != move["artifact"]
            and move["artifact"] == successor["artifact"]
            and rollback["previous"] == move["candidate"] == successor["candidate"]
            and rollback["candidate"] == offline["candidate"] != prior["candidate"]
            and move["previous"] == prior["candidate"], "Signed candidate and artifact rollback chain")
    require(prior["workspaceSHA256"] == "9f60598bdeed93f8e9ddf5d0a1b89e5f6b44d52d9f650108923e8fc1f0c21242"
            and len({row["workspaceSHA256"] for row in rows[1:]}) == 1
            and all(row["retired"] and row["browseWorkspaceUnchanged"] for row in rows),
            "Exact archived seed and stable committed bytes after every cold launch")
    require(all(row["unaffectedWorkspaceFiles"] == prior["unaffectedWorkspaceFiles"] for row in rows),
            "Unchanged workspace lock identity and content across phases")
    readonly = [prior, successor, rollback, offline]
    require(move["writes"] == ["task.f0900000-0000-4000-8000-000000000120.up"]
            and all(not row["writes"] for row in readonly), "Exactly one committed Guest UI action")
    order = prior["coldOrder"].copy()
    require(len(order) == 23 and order[19:21] == [
        "F0900000-0000-4000-8000-000000000119", "F0900000-0000-4000-8000-000000000120"],
        "Archived task identities at page boundary")
    order[19], order[20] = order[20], order[19]
    require(all(row["coldOrder"] == order for row in rows[1:]), "Exact adjacent swap")
    require([[visit["rows"] for visit in row["visits"]] for row in rows] ==
            [[23], [20, 3, 20, 3, 20, 3, 20], [20, 3, 20, 3], [23], [23]],
            "Baseline and rollback show all tasks unpaged. Successor follows the moved task to page one.")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, reason):
    if not condition:
        raise RuntimeError(reason)


def run(args):
    shared = pinned_f08()
    replace = shared["replace_once"]
    source = shared["f02_source"]("journey.py")
    source = replace(source, "args.guests, args.vm], env)", "args.guests, args.vm, args.seed, args.pages], env)")
    source = replace(source, '["down", "up"]', '["move", "successor-cold"]')
    source = replace(source, '"f02-host"', '"f09-host"')
    source = replace(source, '"local F02 restores prior"', '"local F09 restores prior"')
    start = source.index("        prior, down, up, rollback, offline = phases.values()")
    end = source.index('        report["status"] = "passed"', start)
    source = source[:start] + '''        verify_f09_phases(phases, output)
        require(all(all(digest(output / phase / name) == value for name, value in packet.items())
                    for phase, packet in report["packets"].items()), "Signed packet files changed")
        report["signedPacketFilesUnchanged"] = True
''' + source[end:]
    namespace = {"__name__": "f02_driver", "__file__": __file__, "verify_f09_phases": verify_phases}
    exec(compile(source, f'{shared["F02"]}:{shared["F02_PATH"]}/journey.py', "exec"), namespace)
    if len(args) != 9:
        raise SystemExit("usage: journey.py CONTROL FIXTURES GUESTS VM ORIGIN CLI OUTPUT SEED PAGES")
    arguments = namespace["argparse"].Namespace(**dict(zip(
        ("control", "fixtures", "guests", "vm", "origin", "cli", "output", "seed", "pages"),
        (Path(arg).resolve() for arg in args), strict=True,
    )))
    before = [digest(arguments.seed), digest(arguments.pages)]
    try:
        namespace["run_journey"](arguments)
    finally:
        require(before == [digest(arguments.seed), digest(arguments.pages)], "Archived files changed")


if __name__ == "__main__":
    os.umask(0o077)
    if sys.argv[1:] == ["--release-source"]:
        print(pinned_f08()["release_source"]().replace("f08", "f09").replace("F08", "F09"), end="")
    else:
        run(sys.argv[1:])
