"""Use the pinned F04 stock driver for F11 delivery, rollback and refusal."""
import argparse
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
PIN = "4bcfe774f70794b86c014680a351a5f1dbfff3f1"
F04 = "tests/integration/fieldlog-d8-f04-signed"
sys.path.insert(0, str(ROOT / "tests/integration/fieldlog-entry-sync"))


def source(name):
    return subprocess.check_output(["git", "show", f"{PIN}:{F04}/{name}"], cwd=ROOT,
                                   env=dict(os.environ, GIT_NO_LAZY_FETCH="1"), text=True)


def replace(text, old, new):
    if old not in text:
        raise RuntimeError(f"Pinned F04 seam changed: {old}")
    return text.replace(old, new)


def release_source(repo_digest):
    text = source("Release.swift")
    for old, new in {
        "d8-f04": "d8-f11", "fieldlog-f04": "fieldlog-f11", "f04.control": "f11.control",
        'platform: "ios"': 'platform: "android"',
        "9a69cb9d97728f5f8f85f78193e1ed5d09059b54": "00c8fe0400bc9a06242371ce7b02cd440f64f31e",
        "d51adf50de7e20549e87062e4569609342cdfe25": "c6562ba80b992016c0c963cf4c67a59f1f605fd0",
        "TaskStorage.namespace": "(privateRetry ? FieldLogEditorDevelopment.taskRetryNamespace : NoteStorage.namespace)",
        "db9e4e490263d4b0779b03fadfdc07cfca5d23df2501c5c900b54abb904b86fb": repo_digest,
    }.items():
        text = replace(text, old, new)
    return replace(text, '        identity["application"]', '''        if !privateRetry {
            identity["platform"] = ["os": "android", "architecture": "arm64", "environment": "simulator",
                                    "minimum_os": "28", "target": "aarch64-unknown-linux-android28"]
        }
        identity["application"]''')


def run_journey(args):
    s = source("journey.py")
    s = replace(s, "args.guests, args.vm], env)", "args.guests, args.vm, args.seed], env)")
    s = replace(s, "f04-host", "f11-host")
    s = replace(s, "local F04 restores prior", "local F11 restores prior")
    start = s.index("            try:\n                raw_evidence = record(phase,")
    end = s.index('            report["phases"][phase] = evidence', start)
    s = s[:start] + '''            evidence = json.loads(record(phase, [args.control, phase, output, str(port)], env))
            require(evidence["sequence"] == sequence and evidence["artifact"] == artifact, "Launch release identity")
            if phase == "successor":
                require(evidence["refusal"] == "ui_protocol_after_effects"
                        and evidence["presentationAdmitted"] is False
                        and evidence["previousHealthy"] == report["phases"]["prior"]["candidate"],
                        "Public successor did not preserve the healthy prior")
''' + s[end:]
    start = s.index("        prior, rollback, offline = phases.values()")
    end = s.index('        report["status"] = "observed_signed_editor_refusal"', start)
    s = s[:start] + '''        prior, successor, rollback, offline = phases.values()
        require(len({row["pid"] for row in phases.values()}) == 4
                and len({row["launch"] for row in phases.values()}) == 4
                and prior["artifact"] == rollback["artifact"] == offline["artifact"] != successor["artifact"]
                and rollback["candidate"] == offline["candidate"]
                and all(row["retired"] and row["workspaceSHA256"] == digest(args.seed)
                        and row["workspaceReads"] == 1 and row["workspaceWrites"] == 0 for row in phases.values()),
                "Rollback, offline, or byte-identical signed refusal")
        require(all(all(digest(output / phase / name) == value for name, value in packet.items())
                    for phase, packet in report["packets"].items()), "Signed packet files changed")
        report["signedPacketFilesUnchanged"] = True
''' + s[end:]
    namespace = {"__name__": "f04_driver", "__file__": __file__}
    exec(compile(s, f"{PIN}:{F04}/journey.py", "exec"), namespace)
    namespace["run_journey"](args)


if __name__ == "__main__":
    os.umask(0o077)
    if len(sys.argv) == 3 and sys.argv[1] == "--release-source":
        print(release_source(sys.argv[2]), end="")
        sys.exit()
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("control", "fixtures", "guests", "vm", "origin", "cli", "output", "seed"):
        parser.add_argument(name, type=lambda value: Path(value).resolve())
    run_journey(parser.parse_args())
