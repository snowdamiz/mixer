"""Copy the unsigned products to an independent path and verify their linkage."""
import hashlib
import json
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inspect(work, kit):
    products = work / "derived/Build/Products"
    source_run, = products.glob("F11NativeWitness_*.xctestrun")
    configuration = "Debug-iphonesimulator"
    app_name = "F11NativeWitness.app"
    runner_name = "F11NativeWitnessUITests-Runner.app"
    test_name = "F11NativeWitnessUITests.xctest"
    kit.mkdir(parents=True, exist_ok=False)
    run = kit / source_run.name
    shutil.copy2(source_run, run)
    for name in (app_name, runner_name):
        shutil.copytree(products / configuration / name, kit / configuration / name, symlinks=True)

    target = plistlib.loads(run.read_bytes())["F11NativeWitnessUITests"]
    assert target["TestHostPath"] == f"__TESTROOT__/{configuration}/{runner_name}"
    assert target["UITargetAppPath"] == f"__TESTROOT__/{configuration}/{app_name}"
    assert target["TestBundlePath"] == f"__TESTHOST__/PlugIns/{test_name}"
    for name in target["DependentProductPaths"]:
        assert name.startswith("__TESTROOT__/") and (kit / name.removeprefix("__TESTROOT__/")).exists()
    assert str(work).encode() not in run.read_bytes()
    app = kit / configuration / app_name
    runner = kit / configuration / runner_name
    test = runner / "PlugIns" / test_name / "F11NativeWitnessUITests"
    dylib = app / "F11NativeWitness.debug.dylib"
    assert all(not (bundle / "_CodeSignature").exists() for bundle in (app, runner, test.parent))
    for executable in (dylib, test):
        architecture = subprocess.check_output(["lipo", "-archs", executable], text=True).strip()
        platform = subprocess.check_output(["xcrun", "vtool", "-show-build", executable], text=True)
        assert architecture == "arm64" and "IOSSIMULATOR" in platform and "minos 26.0" in platform
    symbols = subprocess.check_output(["nm", dylib], text=True)
    for name in ("fieldLogNoteFixtureGeneration", "privateDevelopmentFieldLogNoteFixture",
                 "F11NativeNote", "mixer_vm_capability_guest_ui_validate_deferred_v1"):
        assert any(f" T " in line and name in line for line in symbols.splitlines()), name
    assert "testPasteSaveAndCommitRestoredNote" in subprocess.check_output(["nm", test], text=True)
    sealed = app / "SealedInput"
    staged = work / "export/source/capability-activation/verification/f11-native/Witness/SealedInput"
    for file in staged.iterdir():
        assert digest(sealed / file.name) == digest(file)
    identity = json.loads((sealed / "identity.json").read_bytes())
    vm = work / "libmixer_vm_capability_experimental.a"
    assert identity["engine"]["artifact_sha256"] == digest(vm)
    log = (work / "xcode.log").read_text()
    assert "-lmixer_vm_capability_experimental" in log and str(work) in log
    assert "\nCodeSign " not in log
    manifest = kit / "MEMBERS.sha256"
    members = [file for file in sorted(kit.rglob("*")) if file.is_file() and not file.is_symlink()]
    manifest.write_text("".join(f"{digest(file)}  {file.relative_to(kit)}\n" for file in members))
    subprocess.run(["shasum", "-a", "256", "-c", manifest.name], cwd=kit, check=True, stdout=subprocess.DEVNULL)
    return {
        "memberManifestSHA256": digest(manifest),
        "appDylibSHA256": digest(dylib),
        "xctestSHA256": digest(test),
        "xctestrunSHA256": digest(run),
        "sealedInputSHA256": {file.name: digest(file) for file in sorted(sealed.iterdir())},
        "vmArchiveSHA256": digest(vm),
        "trustExpiresUnix": json.loads((sealed / "roots.json").read_bytes())[0]["not_after_unix"],
        "runtimeFingerprint": json.loads((sealed / "assignment.json").read_bytes())["assignment"]["runtime"],
    }


if __name__ == "__main__":
    work, kit = map(Path, sys.argv[1:])
    print(json.dumps(inspect(work.resolve(strict=True), kit.resolve()), indent=2))
