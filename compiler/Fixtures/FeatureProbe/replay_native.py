#!/usr/bin/env python3
"""Replay the macOS SwiftPM and FeatureStore controls in owned scratch."""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import resource
import shutil
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "compiler/experiments/fieldlog-guest-benchmark"))

from matched_task import Run, require, sha

SDK_TESTS = (
    "authoringBuildsFieldLogEditorAndGuestCodecOnlyRoundTripsValues",
    "validationRejectsDuplicateUnsupportedAndMalformedControls",
    "reducerEffectsReplaceAndCancelWithoutStaleDelivery",
    "guestUIEventCodecPreservesUnicodeAndUInt64WithoutNormalization",
    "malformedJSONAndUnpairedUnicodeFailBeforeFoundationDecoding",
)


def campaign(run):
    call = run.command
    out = run.scratch
    run.env.update(GIT_ALLOW_PROTOCOL="file", GIT_CONFIG_NOSYSTEM="1")
    revision = call("revision", "/usr/bin/git", "rev-parse", "HEAD")[0].strip()
    tree = call("tree", "/usr/bin/git", "rev-parse", "HEAD^{tree}")[0].strip()
    versions = {
        "macOS": call("macos-version", "/usr/bin/sw_vers")[0].strip(),
        "swift": call("swift-version", "/usr/bin/swift", "--version")[0].strip(),
    }

    lock = ROOT / "sdk/Package.resolved"
    fixture = HERE / "EffectCompletion.swift"
    core = ROOT / "sdk/Sources/MixerCore"
    store_sources = [core / "FeatureStore.swift", core / "Lifecycle.swift"]
    inputs = [lock, fixture, *store_sources, HERE / "Sources/FeatureProbe/main.swift",
              HERE / "Package.swift", Path(__file__)]
    hashes = {str(path.relative_to(ROOT)): sha(path.read_bytes()) for path in inputs}
    pins = json.loads(lock.read_text())["pins"]
    reference_cache = Path.home() / "Library/Caches/org.swift.swiftpm/repositories"
    cache = out / "cache"
    repositories = cache / "repositories"
    repositories.mkdir(parents=True)
    for pin in pins:
        name = pin["identity"]
        sources = list(reference_cache.glob(f"{name}-*"))
        require(len(sources) == 1, f"expected one cached repository for {name}")
        call(f"copy-{name}", "/usr/bin/git", "clone", "--mirror", "--no-local",
             sources[0], repositories / sources[0].name, bound=45)

    swiftpm = ["--cache-path", cache, "--config-path", out / "config",
               "--security-path", out / "security"]
    feature = json.loads(call(
        "native-swiftpm-entry", "/usr/bin/swift", "run", *swiftpm, "--package-path", HERE,
        "--scratch-path", out / "native", "feature-probe", bound=45)[0])
    require(feature == dict(status="passed", completionBasisPoints=5000, codableRoundTrip=True,
                            unicodePreserved=True, emptyTitleRejected=True, wrongFieldTypeRejected=True,
                            nonfiniteRejected=True), f"unexpected SwiftPM entry observations: {feature}")

    binary = out / "effect-completion"
    call("effect-completion-build", "/usr/bin/swiftc", "-O", "-swift-version", "6",
         "-target", "arm64-apple-macosx26.0", "-parse-as-library",
         "-module-cache-path", out / "modules", *store_sources, fixture, "-o", binary, bound=45)
    effects = json.loads(call("effect-completion", binary)[0])
    require(effects == dict(joined=[1, 2, 3, 4], returnedAfterCancellation=[1, 3, 4],
                            reducerDeliveries=[2]), f"unexpected FeatureStore observations: {effects}")

    sdk = out / "sdk"
    stdout, stderr, _ = call(
        "native-sdk", "/usr/bin/swift", "test", *swiftpm, "--package-path", ROOT / "sdk",
        "--scratch-path", sdk, "--jobs", 8, "--skip-update", "--disable-prefetching",
        "--force-resolved-versions", "--filter", "|".join(SDK_TESTS), bound=240)
    passed = re.findall(r"^✔ Test (\w+)\(\) passed after ", stdout, re.M)
    counts = [int(count) for count in re.findall(
        r"^✔ Test run with (\d+) tests? in \d+ suites? passed after ", stdout, re.M)]
    require(sorted(passed) == sorted(SDK_TESTS) and sum(counts) == len(SDK_TESTS),
            f"expected all five SDK controls to pass:\n{stdout[-6000:]}")
    for pin in pins:
        name = pin["identity"]
        checked_out = call(f"verify-{name}", "/usr/bin/git", "-C", sdk / "checkouts" / name,
                           "rev-parse", "HEAD")[0].strip()
        require(checked_out == pin["state"]["revision"], f"wrong SDK checkout for {name}")
    require(all(sha((ROOT / path).read_bytes()) == digest for path, digest in hashes.items()),
            "native replay inputs changed")
    return dict(observedUTC=datetime.now(timezone.utc).isoformat(), revision=revision, tree=tree,
                toolVersions={**versions, "python": sys.version.split()[0], "architecture": os.uname().machine},
                inputsSHA256=hashes, nativeSwiftPMEntry=feature, featureStoreCompletion=effects,
                nativeSDK=dict(passed=list(SDK_TESTS), passedPerTestRun=counts,
                               testPlatforms=sorted(set(re.findall(r"^↳ Target Platform: (.+)$", stdout, re.M))),
                               pinnedCheckouts={pin["identity"]: pin["state"]["revision"] for pin in pins},
                               stdoutSHA256=sha(stdout.encode()), stderrSHA256=sha(stderr.encode())),
                commands=run.commands)


def main():
    require((os.uname().sysname, os.uname().machine) == ("Darwin", "arm64"), "requires arm64 macOS")
    require(Path.cwd() == ROOT, "run from the Mixer checkout root")
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_FSIZE, (256 * 1024**2, 256 * 1024**2))
    local = ROOT / "verification/local"
    local.mkdir(exist_ok=True)
    scratch = Path(tempfile.mkdtemp(prefix="w07-swift-native-", dir=local))
    run = Run(scratch)
    run.deadline = time.monotonic() + 360
    try:
        result = campaign(run)
    finally:
        if run.active is not None:
            raise RuntimeError(f"UNKNOWN custody for {run.active}; preserve {scratch}")
        shutil.rmtree(scratch)
    result["custody"] = dict(directReapedAndGroupsObservedAbsent=len(run.commands), unknown=0,
                             observedPeakScratchBytes=run.peak_scratch, scratchRemoved=not scratch.exists())
    require(result["custody"]["scratchRemoved"], f"scratch remains at {scratch}")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
