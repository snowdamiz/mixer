#!/usr/bin/env python3
"""Build fresh, ad hoc signed Simulator products from local Git objects only."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
import plistlib
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

from upgrade_artifacts import (
    ENGINE_PRODUCTS, FIELDLOG_REV, FIELDLOG_TREE, MIXER_TREES, PAIRS, TOOLCHAIN,
    git_command, git_tree, sha, tool_environment, tree_sha,
)

HERE = Path(__file__).resolve().parent
SDK_INPUTS = ("Package.swift", "sdk/Sources", "sdk/Tests")
CHANGED_ENGINE_FILES = ("AppearanceResolutionV2", "NativePacketV1", "Protocol",
                        "Reconciliation", "Validation")
APP = "Debug-iphonesimulator/FieldLog.app"
RUNNER = "Debug-iphonesimulator/FieldLogUITests-Runner.app"


def encode_json(value):
    return json.dumps(value, indent=2, sort_keys=True) + "\n"


def archive(repo, revision, output, members=()):
    output.mkdir()
    tar = output.parent / (output.name + ".tar")
    git_command(repo, "archive", "--format=tar", f"--output={tar}", revision, *members)
    with tarfile.open(tar) as files:
        files.extractall(output, filter="data")
    tar.unlink()


def toolchain():
    return subprocess.check_output(["/usr/bin/xcodebuild", "-version"], text=True,
                                   env=tool_environment()).strip()


def sign(bundle):
    subprocess.run(["/usr/bin/codesign", "--force", "--sign", "-", "--timestamp=none", bundle],
                   check=True)
    subprocess.run(["/usr/bin/codesign", "--verify", "--strict", bundle], check=True)


def retain(side, workspace, output, fieldlog, repo, keep_map):
    version, build, revision = PAIRS[side]
    work = workspace / side
    work.mkdir()
    app, sdk = work / "app", work / "mixer"
    archive(fieldlog, FIELDLOG_REV, app)
    archive(repo, revision, sdk, SDK_INPUTS)
    sdk_tree = tree_sha(sdk)
    subprocess.run([sys.executable, HERE / "prepare-source.py", app], check=True)
    source_tree = tree_sha(app)
    derived = work / "derived"
    tmp = work / "tmp"
    tmp.mkdir()
    argv = [
        "/usr/bin/xcodebuild", "-project", "ios/FieldLog.xcodeproj", "-scheme", "FieldLog",
        "-configuration", "Debug", "-sdk", "iphonesimulator",
        "-destination", "generic/platform=iOS Simulator", "-derivedDataPath", str(derived),
        "-clonedSourcePackagesDirPath", str(work / "packages"),
        "-packageCachePath", str(work / "package-cache"),
        "-disableAutomaticPackageResolution", "-skipPackageUpdates", "-disablePackageRepositoryCache",
        "CODE_SIGNING_ALLOWED=NO", "ARCHS=arm64", "ONLY_ACTIVE_ARCH=NO",
        f"MARKETING_VERSION={version}", f"CURRENT_PROJECT_VERSION={build}",
        "INFOPLIST_KEY_UIFileSharingEnabled=YES", "INFOPLIST_KEY_LSSupportsOpeningDocumentsInPlace=YES",
        "COMPILER_INDEX_STORE_ENABLE=NO", "ENABLE_DEBUG_DYLIB=NO", "LD_GENERATE_MAP_FILE=YES",
        f"CLANG_MODULE_CACHE_PATH={work / 'clang-cache'}",
        f"SWIFT_MODULE_CACHE_PATH={work / 'swift-cache'}", "build-for-testing",
    ]
    log = work / "xcodebuild.log"
    print(f"Building {side} with Mixer SDK {revision}. Log {log}", flush=True)
    with log.open("xb") as file:
        result = subprocess.run(argv, cwd=app, env=tool_environment() | {"TMPDIR": str(tmp) + "/"},
                                stdout=file, stderr=subprocess.STDOUT)
    if result.returncode:
        lines = log.read_text(errors="replace").splitlines()
        print("\n".join(line for line in lines if "error:" in line or "failed" in line.lower())[-8000:],
              file=sys.stderr)
        raise ValueError(f"Generic {side} build-for-testing failed with exit {result.returncode}")
    if "** TEST BUILD SUCCEEDED **" not in log.read_text(errors="replace"):
        raise ValueError(f"Missing success marker: {log}")

    products = derived / "Build/Products"
    app_bundle = products / APP
    runner = products / RUNNER
    template, = products.glob("FieldLog_*.xctestrun")
    maps = list(derived.glob("Build/Intermediates.noindex/**/FieldLog-LinkMap-*-arm64.txt"))
    link_map, = maps
    relative_map = link_map.read_text().replace(str(work), "<BUILD>")
    linked = {}
    for product in ENGINE_PRODUCTS:
        # The link map records the relocatable SDK product actually given to ld.
        inputs = [line.split("]", 1)[1].strip() for line in link_map.read_text().splitlines()
                  if line.lstrip().startswith("[") and line.rstrip().endswith(f"/{product}.o")]
        if len(inputs) != 1:
            lines = [line for line in link_map.read_text().splitlines() if product in line][:8]
            raise ValueError(f"Expected one {product}.o in {link_map.name}. Found {inputs}. Related: {lines}")
        path = Path(inputs[0])
        linked[product] = sha(path)
    changed = {}
    for name in CHANGED_ENGINE_FILES:
        [path] = derived.glob(f"Build/Intermediates.noindex/**/MixerUI-t.build/Objects-normal/arm64/{name}.o")
        changed[name] = sha(path)

    dest = output / side
    dest.mkdir()
    shutil.copytree(app_bundle, dest / "FieldLog.app", symlinks=True)
    shutil.copy2(template, dest / "template.xctestrun")
    bundle = dest / "FieldLog.app"
    info_path = bundle / "Info.plist"
    info = plistlib.loads(info_path.read_bytes())
    if not all(info.get(key) == expected for key, expected in {
        "CFBundleIdentifier": "dev.mixer.fieldlog",
        "CFBundleShortVersionString": version,
        "CFBundleVersion": build,
    }.items()):
        raise ValueError(f"Incorrect built app identity: {info}")
    # The two boolean keys are app metadata for Files, not code-sign entitlements.
    info["UIFileSharingEnabled"] = True
    info["LSSupportsOpeningDocumentsInPlace"] = True
    info_path.write_bytes(plistlib.dumps(info, fmt=plistlib.FMT_BINARY))
    sign(bundle)
    if side == "new":
        dest_runner = output / "FieldLogUITests-Runner.app"
        shutil.copytree(runner, dest_runner, symlinks=True)
        for nested in sorted((dest_runner / "Frameworks").glob("*")):
            if nested.suffix in {".framework", ".dylib"}:
                result = subprocess.run(["/usr/bin/codesign", "--verify", "--strict", nested],
                                        capture_output=True)
                if result.returncode:
                    sign(nested)
        sign(dest_runner / "PlugIns/FieldLogUITests.xctest")
        sign(dest_runner)
        subprocess.run(["/usr/bin/codesign", "--verify", "--deep", "--strict", dest_runner],
                       check=True)
    if keep_map:
        (dest / "link-map.txt").write_text(relative_map)
    receipt = {
        "status": "generic_build_for_testing_passed_runtime_pending",
        "toolchain": TOOLCHAIN,
        "buildCommand": [str(value).replace(str(work), "<BUILD>") for value in argv],
        "fieldLogRevision": FIELDLOG_REV, "fieldLogGitTree": FIELDLOG_TREE,
        "fieldLogPreparedFileTreeSHA256": source_tree,
        "mixerRevision": revision, "mixerGitTree": git_tree(repo, revision),
        "mixerUISourceGitTree": git_tree(repo, revision, "sdk/Sources/MixerUI"),
        "mixerSDKFileTreeSHA256": sdk_tree,
        "linkedSDKObjectSHA256": linked, "compiledMixerUIFileObjectSHA256": changed,
        "linkMapSHA256": hashlib.sha256(relative_map.encode()).hexdigest(),
        "appBundleID": info["CFBundleIdentifier"],
        "appBuild": build, "appVersion": version, "appTreeSHA256": tree_sha(bundle),
        "appInfoFilesSharing": {key: info[key] for key in
                                ("UIFileSharingEnabled", "LSSupportsOpeningDocumentsInPlace")},
        "appExecutableSHA256": sha(bundle / "FieldLog"),
        "xctestrunSHA256": sha(dest / "template.xctestrun"),
    }
    (dest / "build-receipt.json").write_text(encode_json(receipt))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fieldlog-git", type=Path, required=True)
    parser.add_argument("--mixer-git", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--keep-link-maps", action="store_true")
    args = parser.parse_args()
    out = args.output.resolve()
    fieldlog, repo = args.fieldlog_git.resolve(), args.mixer_git.resolve()
    if toolchain() != TOOLCHAIN or os.uname().machine != "arm64":
        raise ValueError(f"Expected arm64 and {TOOLCHAIN}")
    if git_tree(fieldlog, FIELDLOG_REV) != FIELDLOG_TREE:
        raise ValueError("Unexpected public FieldLog tree")
    for side, (_, _, revision) in PAIRS.items():
        if git_tree(repo, revision) != MIXER_TREES[side]:
            raise ValueError(f"Unexpected {side} public Mixer tree")
    out.mkdir(mode=0o700)
    try:
        with tempfile.TemporaryDirectory(prefix=".build-", dir=out.parent) as build:
            workspace = Path(build)
            with ThreadPoolExecutor(max_workers=len(PAIRS)) as executor:
                futures = [executor.submit(retain, side, workspace, out, fieldlog, repo,
                                           args.keep_link_maps) for side in PAIRS]
                for future in futures:
                    future.result()
        prior, new = [json.loads((out / side / "build-receipt.json").read_text()) for side in PAIRS]
        for key in ("appExecutableSHA256", "mixerUISourceGitTree"):
            if prior[key] == new[key]:
                raise ValueError(f"The two builds share {key}")
        if prior["linkedSDKObjectSHA256"]["MixerUI"] == new["linkedSDKObjectSHA256"]["MixerUI"]:
            raise ValueError("The two apps link identical MixerUI objects")

        from seed import write_seed
        write_seed(out / "FieldLog upgrade photo.png")
        subprocess.run(["/usr/bin/swiftc", "-module-cache-path", str(out / ".verifier-cache"),
                        HERE / "verify-draft-photo.swift", "-o", out / "verify-draft-photo"],
                       env=tool_environment(), check=True)
        shutil.rmtree(out / ".verifier-cache")
        files = {
            item: sha(out / item)
            for item in ("prior/build-receipt.json", "new/build-receipt.json",
                         "FieldLog upgrade photo.png", "verify-draft-photo")
        }
        files["FieldLogUITests-Runner.app"] = tree_sha(out / "FieldLogUITests-Runner.app")
        (out / "inputs.json").write_text(encode_json(files))
    except BaseException:
        shutil.rmtree(out)
        raise


if __name__ == "__main__":
    main()
