#!/usr/bin/env python3
"""Bind the selected-draft Android build to a fresh scenario 22.2.4 delivery."""
import argparse
from hashlib import file_digest, sha256
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import zipfile

MIXER = "5dea19db36610e312b51918b384364ba590b6ef8"
FIELDLOG = "552559d2d3278abb9b1aa7dcf0288102c09a202b"
APPEARANCE = "MixerAppearanceV2/descriptor.json"
APP = "Integrations/GeneratedReport"
GUEST = "Integrations/InstalledGuest"
INSTALLED = {"identity.json", "bridge.json", "port.txt", "roots.json", "storage.json", "storage-grant.json"}
PRIOR_PINS = {
    "Installed/bridge.json": "6f05eb3fa8780ee6102d181b0710765214e51168b1429c52dd10dfd1b96873e5",
    "Installed/storage.json": "a5946bce4d20c315896cac254404f5fd2910b39e7982ba53744592d5d6e84f67",
    "Installed/storage-grant.json": "f630fb1bca6042918d6c29b88027dd8c8da28771599469aee06ff3cd5a3789be",
    "Installed/identity.json": "c50ed73f0cac8637072145126be747b85afa866f29702980a01600191209a1d4",
    "Installed/port.txt": "7fca5d6fb48cc8ce3d27ffb4d179bef3cf6f24a59e1dabddfc1f7964e15ee5b3",
    "baseline.manifest.json": "981c4b7dc99c9c8d292ca16b969090edfa1433a702a9a183f41cc7461edaf536",
}


def digest(path):
    with path.open("rb") as stream:
        return file_digest(stream, "sha256").hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def inventory(root, paths):
    return {path.relative_to(root).as_posix(): digest(path)
            for folder in paths for path in folder.rglob("*") if path.is_file()}


def tree(pins):
    return sha256("".join(f"{value}  {name}\n" for name, value in sorted(pins.items())).encode()).hexdigest()


def write(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def pin(path, expected):
    require(digest(path) == expected, f"Input digest mismatch: {path}")


def capture(command, env, timeout=90):
    return subprocess.check_output(list(map(str, command)), env=env, stderr=subprocess.STDOUT,
                                   text=True, timeout=timeout)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("work", "project", "java", "native", "reference", "output"):
        parser.add_argument(f"--{key}", required=True, type=lambda p: Path(p).resolve())
    parser.add_argument("--seal-only", action="store_true")
    args = parser.parse_args()
    os.umask(0o077)
    work, out, project = args.work, args.output, args.project
    require(out.is_dir(), "Output directory must already exist")
    apk = out / "FieldLog-selected-draft-dev-arm64.apk"
    require(not apk.exists() and not apk.is_symlink(), "Use a fresh output")
    env = os.environ | {"TMPDIR": str(work / "tmp")}
    sdk = Path(env.get("ANDROID_HOME", "/opt/homebrew/share/android-commandlinetools"))
    jdk = Path(env.get("MIXER_JDK", "/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home"))
    env["JAVA_HOME"] = str(jdk)
    tools = sdk / "build-tools/36.0.0"
    ndk = sdk / "ndk/27.1.12297006/toolchains/llvm/prebuilt/darwin-x86_64/bin"
    swift_artifact = Path(env.get("MIXER_ANDROID_ARTIFACT_PATH", str(Path.home() /
        ".swiftpm/swift-sdks/swift-6.3.3-RELEASE_android.artifactbundle/swift-android")))
    compiler = Path(env.get("MIXER_SWIFT", str(Path.home() /
        "Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin/swift"))).with_name("swift-frontend")
    fieldlog, mixer = work / "fieldlog", work / "mixer"
    app, engine = fieldlog / APP, work / "android-engine"
    vm = engine / "lib/libmixer_vm_capability_experimental.a"
    java, native = args.java, args.native
    descriptor = project / "Generated/MixerAndroid/app/assets" / APPEARANCE
    lock_path = project / "mixer.lock"
    profile = json.loads(lock_path.read_text())["android"]["profile"]
    require(profile["id"] == "mixer.android-source-pair.24", "Expected Pair24 admission")
    pin(descriptor, profile["default_descriptor"]["sha256"])
    require(descriptor.stat().st_size == profile["default_descriptor"]["bytes"], "Descriptor size mismatch")
    engine_receipt = json.loads((engine / "receipt.json").read_text())
    require(engine_receipt["source_revision"] == MIXER, "Wrong VM source revision")
    pin(vm, engine_receipt["library"]["sha256"])

    jni = native / "libmixer_public_android_jni.so"
    dex = java / "dex/classes.dex"
    manifest = java / "manifest.apk"
    headers = list((java / "jni").glob("*ChecklistPanel.h"))
    require(len(headers) == 1, "Expected the nested checklist's javac-generated JNI header")
    symbols = capture([ndk / "llvm-nm", "--dynamic", "--defined-only", jni], env)
    exported = {line.split()[-1] for line in symbols.splitlines() if line.strip()}
    expected = set(re.findall(r"Java_\w+", headers[0].read_text()))
    require(len(expected) == 5 and expected <= exported and "mxis_guest_ui_witness" in exported,
            "Java checklist JNI declarations and rebuilt ELF exports differ")

    previous = args.reference
    for relative, expected_hash in PRIOR_PINS.items():
        pin(previous / relative, expected_hash)
    delivery = out / "delivery-android"
    installed = delivery / "Installed"
    if args.seal_only:
        installed.mkdir(parents=True)
        for name in ("bridge.json", "port.txt", "storage.json", "storage-grant.json"):
            shutil.copyfile(previous / "Installed" / name, installed / name)

    fallback = inventory(fieldlog, (app / "Sources", app / "Platforms", fieldlog / GUEST))
    link = {"app/" + key: value for key, value in fallback.items()}
    link.update(inventory(work, [mixer / name for name in
        ("sdk", "capability-activation", "experimental-capability-runtime", "runtime-identity", "updates",
         "native/android/signed-guest-ui", "verification/android-binding-stage4/host-bridge")]))
    link.update({"generated/" + key: value for key, value in inventory(project, (project / "Generated/MixerAndroid",)).items()})
    recipe = Path(__file__).resolve().parent
    bindings = {"classes.dex": dex, "manifest.apk": manifest, "libmixer_public_android_jni.so": jni,
                "vm.a": vm, "descriptor.json": descriptor, "mixer.lock": lock_path,
                "apk-packager": app / "scripts/build-signed-checklist-android.py",
                "checklist-network": app / "Platforms/Android/res/xml/checklist_network.xml"}
    bindings.update({f"bridge/{path.name}": path for path in native.glob("*.o")})
    bindings.update({f"recipe/{path.name}": path for path in
                     [recipe / name for name in ("build-java.zsh", "build-payload.zsh", "Package.swift",
                                                 "Package.resolved", "manifest.py", "offline-swiftpm.zsh")]})
    bindings["recipe/seal-and-package.py"] = Path(__file__).resolve()
    bindings["recipe/SealDraftScenario.swift"] = recipe / "SealDraftScenario.swift"
    link.update({f"payload/{name}": digest(path) for name, path in bindings.items()})
    binding = {
        "engine": {"version": MIXER, "source_sha256": engine_receipt["source_manifest_sha256"],
                   "artifact_sha256": digest(vm)},
        "toolchain": {"compiler_version": capture([compiler, "-version"], env).splitlines()[0],
                      "compiler_sha256": digest(compiler), "sdk_version": "android28",
                      "sdk_sha256": digest(swift_artifact.parent / "info.json"),
                      "build_tools_sha256": sha256(capture([tools / "aapt2", "version"], env).strip().encode()).hexdigest()},
        "build": {"settings_sha256": digest(work / "android-package/Package.swift"),
                  "link_inputs_sha256": tree(link), "native_fallback_sha256": tree(fallback),
                  "permissions_sha256": digest(java / "AndroidManifest.xml"),
                  "entitlements_sha256": sha256(b"{}").hexdigest(),
                  "resource_policy_sha256": digest(installed / "bridge.json")},
    }
    if args.seal_only:
        write(delivery / "binding.json", binding)
        runtime = capture([work / "sealer2/SealDraftScenario", previous, delivery, work / "guests"], env).strip()
    else:
        require(json.loads((delivery / "binding.json").read_text()) == binding,
                "Sealed binding differs from this build")
        runtime = json.loads((delivery / "host.json").read_text())["runtime"]
    identity = json.loads((installed / "identity.json").read_text())
    host = json.loads((delivery / "host.json").read_text())
    require(host["runtime"] == runtime and runtime != "6de8b1d7df939cb270947fa24c7fd45978fd49db254e59cd3cc06363aec12337",
            "Sealer did not emit a new matching runtime fingerprint")
    require(all(identity[key][field] == value for key, fields in binding.items() for field, value in fields.items())
            and identity["build"]["trust_roots_sha256"] == digest(installed / "roots.json"),
            "Sealed identity differs from the new build or trust roots")
    require({path.name for path in installed.iterdir()} == INSTALLED, "Unexpected Installed file inventory")
    pins = {name: digest(installed / name) for name in INSTALLED}
    if args.seal_only:
        write(out / "installed.sha256.json", pins)
        write(out / "materials.sha256.json", inventory(out, [delivery]))
        print(f"Sealed Android runtime {runtime}")
        return
    require(json.loads((out / "installed.sha256.json").read_text()) == pins,
            "Installed material changed after sealing")
    require(json.loads((out / "materials.sha256.json").read_text()) == inventory(out, [delivery]),
            "Delivery material changed after sealing")

    commands = {
        "package": [sys.executable, "-B", app / "scripts/build-signed-checklist-android.py",
                    "--mixer-project", project, "--manifest-apk", manifest, "--dex", dex, "--jni-library", jni,
                    "--installed-checklist", installed, "--checklist-sha256", out / "installed.sha256.json",
                    "--android-sdk", sdk, "--swift-android-sdk", swift_artifact, "--java-home", jdk, "--output", apk],
        "apksigner": [tools / "apksigner", "verify", "--verbose", "--print-certs", "-Werr", apk],
        "zipalign": [tools / "zipalign", "-c", "-P", "16", "4", apk],
        "badging": [tools / "aapt2", "dump", "badging", apk],
    }
    for label, command in commands.items():
        print(label, flush=True)
        (work / "logs" / f"{label}.log").write_text(capture(command, env))
    members = {"classes.dex": dex, "lib/arm64-v8a/" + jni.name: jni, "assets/" + APPEARANCE: descriptor}
    members.update({f"assets/ChecklistRelease/{name}": installed / name for name in INSTALLED})
    with zipfile.ZipFile(apk) as signed, zipfile.ZipFile(manifest) as linked_manifest:
        for name, path in members.items():
            require(sha256(signed.read(name)).hexdigest() == digest(path), f"Final APK member differs: {name}")
        for name in linked_manifest.namelist():
            require(signed.read(name) == linked_manifest.read(name), f"Final APK manifest member differs: {name}")
        member_pins = {name: sha256(signed.read(name)).hexdigest() for name in signed.namelist()}
    shutil.copyfile(lock_path, out / "mixer.lock")
    write(out / "source-capture.json", {
        "fieldLogBase": FIELDLOG, "fieldLogTree": capture(["git", "-C", fieldlog, "write-tree"], env).strip(),
        "mixerRevision": MIXER, "publicProfile": profile, "binding": binding, "androidRuntime": runtime,
        "payload": {name: digest(path) for name, path in bindings.items()}, "linkFiles": link, "fallbackFiles": fallback,
        "apkSHA256": digest(apk), "apkBytes": apk.stat().st_size, "apkMembersSHA256": member_pins,
        "jniDeclaredAndExported": sorted(expected), "publicWitnessExported": True,
        "commands": {label: list(map(str, c)) for label, c in commands.items()},
    })
    print(f"{apk}\nAndroid runtime {runtime}")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as error:
        sys.exit(f"{error}\n{error.output}")
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        sys.exit(str(error))
