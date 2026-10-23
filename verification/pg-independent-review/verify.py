#!/usr/bin/env python3
"""Reproduce the pinned independent PostgreSQL review in disposable local clusters.

No configured database is used. The original private-cluster harness is exported
from the reviewed Git commit; only its test selector is changed. Fixed checks add
the explicitly owned release-file overlay and independent tests to another export.
"""
from pathlib import Path
import argparse
import datetime
import hashlib
import io
import json
import os
import re
import shutil
import struct
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[2]
REVIEW = Path(__file__).resolve().parent
PIN = "b70a8774c13763ceced909d925a539e1f149381c"
OVERLAY = ["services/release/postgres.go", "services/release/postgres_guards_integration_test.go", "services/release/POSTGRES.md"]
TESTS = ["review_postgres_test.go", "review_roles_test.go"]
ENV = {k: v for k, v in os.environ.items() if not k.startswith(("PG", "MIXER_TEST_", "DYLD_", "LD_"))}
ENV.update(GOTOOLCHAIN="go1.26.4", GOWORK="off", GOFLAGS="")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def entries(directory):
    result = []
    for path in sorted(p for p in directory.rglob("*") if p.is_file()):
        data = path.read_bytes()
        result.append(dict(path=str(path.relative_to(directory)), bytes=len(data), sha256=digest(data)))
    return result


def export(destination, archive):
    destination.mkdir(parents=True)
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        tar.extractall(destination, filter="data")
    return destination / "services"


def install_tests(source, select):
    for name in TESTS:
        shutil.copyfile(REVIEW / name, source / "release" / name)
    harness = (source / "verification/postgres.py").read_text()
    if harness.count("'^TestPostgres'") != 1:
        raise ValueError("reviewed harness selector changed")
    derived = harness.replace("'^TestPostgres'", repr(select))
    path = source / "verification/review-postgres.py"
    path.write_text(derived)
    return dict(originalSHA256=digest(harness.encode()), derivedSHA256=digest(derived.encode()),
                change="One Go test selection regex only; isolated cluster safety/lifecycle unchanged", selector=select)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="new private evidence/build directory")
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    output.chmod(0o700)
    records = []

    def run(name, command, cwd, timeout=240):
        result = subprocess.run(command, cwd=cwd, env=ENV, text=True, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, timeout=timeout)
        log = output / (name + ".log")
        log.write_text(result.stdout)
        records.append(dict(name=name, command=command, cwd=str(cwd), exitCode=result.returncode,
                            output=log.name, outputSHA256=digest(log.read_bytes())))
        print(json.dumps(dict(name=name, exitCode=result.returncode)), flush=True)
        return result

    archive = git("archive", PIN, "services")
    original = export(output / "original", archive)
    claim = json.loads((original / "verification/postgres-2026-10-22.json").read_text())["sourceTree"]
    checksum = hashlib.sha256()
    for item in claim["files"]:
        data = (output / "original" / item["path"]).read_bytes()
        if len(data) != item["bytes"] or digest(data) != item["sha256"]:
            raise ValueError("pinned implementation receipt mismatch: " + item["path"])
        checksum.update(item["path"].encode() + b"\0" + struct.pack(">Q", len(data)) + data)
    if checksum.hexdigest() != claim["sha256"]:
        raise ValueError("implementation source-tree digest mismatch")
    fixed = export(output / "fixed", archive)
    for name in OVERLAY:
        shutil.copyfile(ROOT / name, output / "fixed" / name)
    versions = run("versions", ["go", "version"], original)
    baseline = run("baseline-unit", ["go", "test", "-race", "-count=1", "-json", "./..."], original)
    vet = run("baseline-vet", ["go", "vet", "./..."], original)
    modules = run("modules", ["go", "mod", "verify"], original)
    baseline_pg = run("baseline-postgres", ["python3", "verification/postgres.py", "--output", str(output / "baseline-postgres")], original)
    original_derivation = install_tests(original, "^TestPostgresReview")
    original_before = entries(original)
    failing = run("original-adversarial", ["python3", "verification/review-postgres.py", "--output", str(output / "original-postgres")], original)
    fixed_derivation = install_tests(fixed, "^TestPostgres")
    fixed_before = entries(fixed)
    fixed_unit = run("fixed-unit", ["go", "test", "-race", "-count=1", "-json", "./..."], fixed)
    fixed_vet = run("fixed-vet", ["go", "vet", "./..."], fixed)
    fixed_pg = run("fixed-postgres", ["python3", "verification/review-postgres.py", "--output", str(output / "fixed-postgres")], fixed)
    original_text = (output / "original-postgres/real-postgres-tests.stdout").read_text()
    expected = {"TestPostgresReviewRejectsRuntimeSchemaOwnership", "TestPostgresReviewRejectsUnknownMigrationVersion", "TestPostgresReviewRejectsRuntimeGuardFunctionOwnership"}
    failed = set(re.findall(r"^--- FAIL: (\w+)", original_text, re.MULTILINE))
    clean = all(json.loads((output / folder / "receipt.json").read_text()).get("privateClusterRemoved")
                for folder in ["baseline-postgres", "original-postgres", "fixed-postgres"])
    passed = all(r.returncode == 0 for r in [versions, baseline, vet, modules, baseline_pg, fixed_unit, fixed_vet, fixed_pg])
    source_stable = original_before == entries(original) and fixed_before == entries(fixed)
    receipt = dict(schema=1, createdAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        reviewer=dict(model="gpt-6.1-sol", reasoningEffort="xhigh", baselineReviewIndependent=True,
                      fixesImplementedByReviewer=True, ownerIndependentFixedReviewPending=True),
        source=dict(baseCommit=PIN, repositoryTree=git("rev-parse", PIN + "^{tree}").decode().strip(),
                    servicesGitTree=git("rev-parse", PIN + ":services").decode().strip(), archiveSHA256=digest(archive),
                    implementationSourceDigestVerified=claim["sha256"],
                    originalAfterTestInjection=original_before, fixedOverlayAndTests=fixed_before,
                    sourceUnchangedDuringChecks=source_stable),
        harnessDerivation=dict(original=original_derivation, fixed=fixed_derivation),
        commands=records, originalNegativeTests=dict(exitCode=failing.returncode, expectedFailures=sorted(expected), observedFailures=sorted(failed)),
        checksPassed=passed and failing.returncode == 1 and failed == expected and clean and source_stable,
        privateClustersRemoved=clean, physicalDevices=False, productionDatabaseUsed=False,
        limitations=["Local PostgreSQL17.11 only; PostgreSQL14/15/16/18 target matrix pending",
            "Private Unix-socket trust authentication only; no hosted auth/TLS/SCRAM qualification",
            "No backup/restore, managed failover, dispatcher, operational RPO/RTO, external audit or GA acceptance",
            "Fixes require an independent owner review; signed schema2 protocol composition is a separate lane"])
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(dict(receipt=str(output / "receipt.json"), checksPassed=receipt["checksPassed"]), indent=2))
    if not receipt["checksPassed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
