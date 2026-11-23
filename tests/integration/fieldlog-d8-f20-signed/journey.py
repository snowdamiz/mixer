#!/usr/bin/env python3
"""Run the F20 assertions through the pinned F08/F02 signed local journey."""
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parents[3]
SEED = "ea178afd68bd143837e0ef09405ac99a6efe59563d238adad41dc8d6a9aa9a8c"
PROJECTION = "d23b40f1bd285ba2e7f63655084b0e79d2ed10b813288a9f057759eeebdb0649"
PROJECT = "F2000000-0000-4000-8000-000000000001"
DRAFT = "F2000000-0000-4000-8000-000000000220"


def require(condition, reason):
    if not condition:
        raise RuntimeError(reason)


def replace(source, old, new):
    require(source.count(old) == 1, f"Pinned F02 seam changed: {old}")
    return source.replace(old, new, 1)


def read_pinned(path, digest):
    raw = path.read_bytes()
    require(sha256(raw).hexdigest() == digest, f"Wrong archived fixture: {path}")
    return json.loads(raw)


def archive_pages(seed, projection):
    result = {}
    for family in ("drafts", "entries"):
        rows = {row["title"]: row for row in seed[family] if row["projectID"] == PROJECT}
        for index, archived in enumerate(projection[family]):
            ids = []
            labels = []
            for label in archived["rows"]:
                title, _, suffix = label.partition(" · ")
                row = rows.pop(title)
                ids.append(row["id"])
                if family == "entries":
                    date = datetime(2001, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=row["occurredAt"])
                    require(suffix == f'{row["category"]} · {date.strftime("%b")} {date.day}, {date.year}',
                            "Pair25 label disagrees with the exact fixture")
                    label = f'{title} · {row["category"]} · {date.strftime("%Y-%m-%dT%H:%M:%SZ")}'
                labels.append(label)
            result[family, index] = dict(family=family, ids=ids, labels=labels, **{
                key: archived[key] for key in ("position", "previousEnabled", "nextEnabled")
            })
        require(not rows, f"Archived pages incomplete: {family}")
    return result


def verify(phases, seed_path):
    seed = read_pinned(seed_path, SEED)
    projection = read_pinned(seed_path.with_name("pair25-projection.json"), PROJECTION)
    pages = archive_pages(seed, projection)
    visits = [("drafts", 0), ("drafts", 1), ("drafts", 1), ("entries", 0), ("entries", 1),
              ("drafts", 1), ("drafts", 0), ("entries", 1), ("entries", 2), ("entries", 1), ("entries", 0)]
    draft = next(row for row in seed["drafts"] if row["id"] == DRAFT)
    prior, exact, cold, rollback, offline = phases.values()
    require(len({row["pid"] for row in phases.values()}) == len(phases) and
            len({row["launch"] for row in phases.values()}) == len(phases), "Distinct process and guest launches")
    require([row["sequence"] for row in phases.values()] == [1, 2, 2, 3, 3], "Signed sequence history")
    require(prior["artifact"] == rollback["artifact"] == offline["artifact"] != exact["artifact"]
            and exact["artifact"] == cold["artifact"] and exact["candidate"] == cold["candidate"] == rollback["previous"]
            and rollback["candidate"] == offline["candidate"] != prior["candidate"]
            and exact["previous"] == prior["candidate"], "Signed artifact and candidate lineage")
    require(len({tuple(row["fileIdentity"]) for row in phases.values()}) == 1 and
            len({row["outboxSHA256"] for row in phases.values()}) == 1, "Stable file identity and entire outbox")
    for name, row in phases.items():
        require(row["workspaceSHA256"] == SEED and row["revision"] == 1 and row["outboxCount"] == 46
                and row["writeAttempts"] == 0 and row["retired"], "Read-only workspace and retired owner")
        if name in ("exact", "exact-cold"):
            require(row["pages"] == [pages[key] for key in visits], f"Exact archived page identity/order: {name}")
            require(row["openedDraft"] == {key: draft[key] for key in ("id", "title", "note")},
                    f"Second-page saved draft open: {name}")
            reads = [f"{family}-{page}" for family, page in visits]
            reads.insert(2, f"draft-{DRAFT}")
            reads.insert(0, "workspace")
            require(row["reads"] == reads and row["deliveredEvents"] == 13, "Exact storage reads and routed actions")
        else:
            require(row["initialNodes"] == ["workspace.home"]
                    and row["reads"] == ["workspace"]
                    and not any(row[key] for key in ("pages", "openedDraft", "deliveredEvents")),
                    "Absent Android route in prior and rollback")


def f08(stage):
    return runpy.run_path(str(stage / "tests/integration/fieldlog-d8-f08-signed/journey.py"))


def release_source(stage):
    source = f08(stage)["release_source"]()
    return source.replace("f08", "f20").replace("TaskStorage", "PagerStorage")


def run(stage, argv):
    source = f08(stage)["f02_source"]("journey.py")
    source = replace(source, 'args.guests, args.vm], env)', 'args.guests, args.vm, args.seed], env)')
    source = replace(source, '"local F02 restores prior"', '"local F20 restores prior"')
    source = replace(source, '"f02-host"', '"f20-host"')
    source = replace(source, 'for launch in ["down", "up"] if phase == "exact" else [phase]:', 'for launch in [phase]:')
    source = replace(source, '    def close_origin():', '    origin_stops = []\n\n    def close_origin():')
    source = replace(source, 'report["originCleanup"] = {"pid": child.pid, "exit": status, "groupAbsent": True}',
                     'stop = {"pid": child.pid, "exit": status, "groupAbsent": True, "port": port}\n'
                     '        origin_stops.append(stop)\n        report["originCleanup"] = origin_stops')
    source = replace(source, 'report["originCleanup"]["portRefused"] = True', 'stop["portRefused"] = True')
    start = source.index('        with (output / "origin.log").open("xb")')
    end = source.index('        publisher_env', start)
    launch = source[start:end].replace('.open("xb")', '.open("ab")')
    source = source[:start] + '        def start_origin():\n            nonlocal child\n' + ''.join(
        '    ' + line for line in launch.splitlines(keepends=True)) + '\n        start_origin()\n' + source[end:]
    socket_test = '''            if phase == "exact":
                close_origin()
                child = None
                report["phases"]["exact-cold"] = json.loads(record(
                    "exact-cold", [args.control, "exact-cold", output, str(port)], env))
                start_origin()
'''
    source = replace(source, '        status, raw = get(PROJECT + "/audit", token)',
                     socket_test + '        status, raw = get(PROJECT + "/audit", token)')
    source = replace(source, 'if child is not None and "originCleanup" not in report:', 'if child is not None:')
    start = source.index('        prior, down, up, rollback, offline = phases.values()')
    end = source.index('        report["status"] = "passed"', start)
    source = source[:start] + '        verify_f20_phases(phases, args.seed)\n' + source[end:]
    scope = {"__name__": "pinned_signed_journey", "__file__": __file__, "verify_f20_phases": verify}
    exec(compile(source, "F02 stock journey with F20 assertions", "exec"), scope)
    require(len(argv) == 8, "Expected CONTROL FIXTURES GUESTS VM ORIGIN CLI OUTPUT SEED")
    args = scope["argparse"].Namespace(**dict(zip(
        ("control", "fixtures", "guests", "vm", "origin", "cli", "output", "seed"),
        (Path(value).resolve() for value in argv), strict=True,
    )))
    read_pinned(args.seed, SEED)
    read_pinned(args.seed.with_name("pair25-projection.json"), PROJECTION)
    scope["run_journey"](args)


if __name__ == "__main__":
    os.umask(0o077)
    stage = Path(sys.argv[1]).resolve(strict=True)
    if sys.argv[2:] == ["--release-source"]:
        print(release_source(stage), end="")
    else:
        run(stage, sys.argv[2:])
