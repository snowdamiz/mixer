#!/usr/bin/env python3
"""Stage only completed, root-reviewed diagnostic slices; exclude active lanes."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
BASE = Path(__file__).resolve().parent
CONTEXT = "6403eea98031207f6e40a72b55dfd3bd4e7e6ec2"
DIRECTORIES = [
    "verification/swift-exact-reactor-after-plan-reuse",
    "verification/swift-exact-reactor-after-plan-reuse-root-selection",
    "verification/swift-plan-cache-remaining-work-diagnosis",
    "verification/apple-focus-system-runtime-preparation",
    "verification/apple-focus-system-runtime-review",
    "verification/apple-focus-system-runtime-root-review",
    "verification/apple-focus-system-native",
    "verification/apple-focus-system-native-root-selection",
    "verification/apple-focus-system-native-result",
    "verification/github-ci-6403eea9-engine",
    "verification/github-delivery-decode-plan",
]
FILES = [
    "PLAN.md", "STATUS.md", "work-graph.json", "gates/ga.json",
    "docs/swift-exact-reactor-after-plan-reuse.md",
    "docs/swift-exact-reactor-after-plan-reuse-result.md",
    "docs/swift-plan-cache-remaining-work-diagnosis.md",
    "docs/apple-focus-system-runtime-preparation.md",
    "docs/apple-focus-system-runtime-review.md",
    "docs/apple-focus-system-native-result.md",
]


def git(*args, **kwargs):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                          check=True, timeout=120, **kwargs).stdout


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write(name, value):
    with (BASE / name).open("x") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, ensure_ascii=False)
        stream.write("\n")


def main():
    assert git("rev-parse", "HEAD").decode().strip() == CONTEXT
    assert not git("diff", "--cached", "--name-only", "-z")
    paths = {ROOT / name for name in FILES}
    for directory in DIRECTORIES:
        for path in (ROOT / directory).rglob("*"):
            assert not path.is_symlink(), path
            if path.is_file():
                paths.add(path)
    rows = {}
    for path in sorted(paths):
        assert path.is_file() and path.resolve() == path
        assert "__pycache__" not in path.parts and path.suffix != ".pyc"
        raw = path.read_bytes()
        assert len(raw) < 50_000_000, path
        rows[str(path.relative_to(ROOT))] = {"bytes": len(raw), "sha256": sha(raw)}
    names = sorted(rows)
    raw_names = b"\0".join(name.encode() for name in names) + b"\0"
    ignored = subprocess.run(["git", "check-ignore", "--stdin", "-z"],
        cwd=ROOT, input=raw_names, capture_output=True, timeout=30)
    assert ignored.returncode == 1 and ignored.stdout == b"", ignored.stdout
    git("diff", "--check", "--", *FILES)
    write("selected-files.json", {
        "schema": 1, "observedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "baseRevision": CONTEXT, "files": rows,
        "bytes": sum(row["bytes"] for row in rows.values()),
        "excludedActiveLanes": ["swift-cache-current-attribution-observer",
                                "apple-reference-focus-lifecycle-diagnosis"],
        "scope": "Completed diagnostics and observed failures, not native/full-workload acceptance",
        "rootVerification": {
            "fullSwiftResult": {"members": 311, "passed": True, "fullWorkloadPassed": False},
            "cacheDiagnosis": {"members": 46, "passed": True},
            "nativePreparationReview": {"members": 26, "inputs": 720, "passed": True},
            "nativeResultAudit": {"members": 10, "recordedFiles": 2367,
                                  "passed": True, "nativePassed": False},
            "priorHostCI": {"run": 40174672304, "jobsPassed": 3,
                            "stepsPassed": 38, "skips": 0},
        },
    })
    names += [str(Path(__file__).relative_to(ROOT)),
              str((BASE / "selected-files.json").relative_to(ROOT))]
    git("add", "--pathspec-from-file=-", "--pathspec-file-nul",
        input=b"\0".join(name.encode() for name in names) + b"\0")
    staged = [name.decode() for name in git("diff", "--cached", "--name-only", "-z").split(b"\0") if name]
    assert set(staged) <= set(names)
    for name, row in rows.items():
        assert sha((ROOT / name).read_bytes()) == row["sha256"], name
    git("diff", "--cached", "--check", "--", *FILES)
    check = subprocess.run(["git", "diff", "--cached", "--check"],
                           cwd=ROOT, capture_output=True, timeout=30)
    (BASE / "evidence-whitespace.stdout").write_bytes(check.stdout)
    (BASE / "evidence-whitespace.stderr").write_bytes(check.stderr)
    # Preserve sealed raw logs and source excerpts exactly, including their whitespace.
    diagnostics = [line for line in check.stdout.decode().splitlines()
                   if ": trailing whitespace." in line or ": new blank line at EOF." in line]
    assert check.returncode in (0, 2) and check.stderr == b""
    assert all(line.startswith("verification/") for line in diagnostics)
    write("staging.json", {"schema": 1, "stagedFiles": len(staged),
          "selectedDataBytes": sum(row["bytes"] for row in rows.values()),
          "sourceAndDocsWhitespacePass": True, "allEvidenceWhitespaceExitCode": check.returncode,
          "preservedEvidenceWhitespaceDiagnostics": len(diagnostics),
          "activeLanesExcluded": True, "stagedPaths": staged})
    print(json.dumps({"stagedFiles": len(staged), "selectedDataBytes": sum(row["bytes"] for row in rows.values()),
                      "preservedEvidenceWhitespaceDiagnostics": len(diagnostics)}))


if __name__ == "__main__":
    main()
