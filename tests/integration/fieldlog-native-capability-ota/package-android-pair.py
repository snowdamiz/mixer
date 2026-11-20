"""Build the development APK pair from the reviewed calculation build and HTTPS overlay."""

import argparse
import hashlib
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import sys
import zipfile

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
CALC = HERE.parent / "fieldlog-task-calculation/android-packaging"
sys.path.insert(0, str(CALC))
from package import ADAPTED_DISTRIBUTOR, GUESTS, JNI, PACKAGE, capture, digest, inventory, pin, read, require, tree, verify_jni, write

BASE = "6bcd5aa3f03383682b77188ce46c83ba730f3627"
OLD_TREE = "7753563b91fe162cfb058cb175ccde979b430033"
SUCCESSOR_TREE = "0e490c5982e67fa777ce36c83308dd482a7e65b2"
CAPABILITY = "network.http.v1"
ASSETS = "assets/ChecklistRelease/"
HTTPS = {
    "http.json": "11efd17b79bd175692020f23c6673cac9a93a9638077e546163846d7f5576a0d",
    "http-grant.json": "dd4db5148d7e5e4461a53df405a63ffb368dc668c3cba81e6183c2383e960f95",
}


def compose(work):
    require(subprocess.run(["git", "-C", REPO, "merge-base", "--is-ancestor", BASE, "HEAD"],
                           timeout=15).returncode == 0, "Use the pinned public mixer base or a descendant")
    fieldlog = work / "fieldlog"
    git = ["git", "-C", fieldlog]
    require(capture(os.environ, *git, "write-tree").strip() == OLD_TREE
            and not capture(os.environ, *git, "diff", "--name-only").strip(),
            "Expected the verified storage-only FieldLog tree")
    capture(os.environ, *git, "apply", "--index", "--whitespace=error", HERE / "android-successor.patch")
    require(capture(os.environ, *git, "write-tree").strip() == SUCCESSOR_TREE,
            "Unreviewed successor source tree")


def distributor(work, calculation):
    path = work / "https-distributor.py"
    original = calculation / "calculation-distributor.py"
    pin(original, ADAPTED_DISTRIBUTOR)
    shutil.copyfile(original, path)
    subprocess.run(["patch", "--batch", "--fuzz=0", path, HERE / "calculation-apk-signer.patch"],
                   capture_output=True, check=True, timeout=15)
    source = path.read_text()
    anchor = '    "calculation-seed.json": 3530,'
    require(source.count(anchor) == 1, "Expected calculation asset limit")
    limits = "".join(f'\n    "{name}": 65536,' for name in HTTPS)
    # The maintained packager verifies an exact asset set for each invocation.
    successor = path.with_name("successor-distributor.py")
    successor.write_text(source.replace(anchor, anchor + limits))
    return path, successor


def stage_materials(work, calculation, packet):
    reviewed = calculation / "delivery-android/Installed"
    build = read(calculation / "build-receipt.json")
    seed = work / "guests/reviewed.wasm"
    pin(seed, GUESTS["reviewed"])
    shutil.copyfile(seed, packet / "reviewed.wasm")
    (packet / "refused").mkdir()
    source = work / "fieldlog"
    fieldlog = source / "Integrations/GeneratedReport"
    inputs = build["linkedInputs"]
    vm = work / "android-engine/lib/libmixer_vm_capability_experimental.a"
    pin(vm, inputs["vm"])
    for label, java, native in (("old", work / "java", work / "payload"),
                                ("successor", work / "https-java", work / "https-payload")):
        folder = packet / label
        installed = folder / "Installed"
        installed.mkdir(parents=True)
        identity = read(reviewed / "identity.json")
        link = dict(inputs)
        for name, expected in read(calculation / "installed.sha256.json").items():
            if name not in {"identity.json", "roots.json"}:
                pin(reviewed / name, expected)
                shutil.copyfile(reviewed / name, installed / name)
        jni = native / Path(JNI).name
        dex = java / "dex/classes.dex"
        manifest = java / "manifest.apk"
        if label == "old":
            for name, path in (("jni", jni), ("dex", dex), ("linkedManifest", manifest)):
                pin(path, link[name])
        else:
            fixture = work / "mixer/capability-activation/Tests/MixerCapabilityActivationTests/Fixtures"
            http, = [item for item in read(fixture / "identity.json")["capabilities"]
                     if item["id"] == CAPABILITY]
            for name, expected in HTTPS.items():
                shutil.copyfile(fixture / name, installed / name)
                pin(installed / name, expected)
                link["installed/" + name] = expected
            require(http["configuration_sha256"] == HTTPS["http.json"] and http["grants_sha256"] == HTTPS["http-grant.json"]
                    and http["native_sha256"] == identity["capabilities"][0]["native_sha256"], "HTTPS identity differs")
            identity["capabilities"].insert(0, http)
            fallback = inventory(source, fieldlog / "Sources") | inventory(source, source / "Integrations/InstalledGuest")
            link.update(jni=digest(jni), dex=digest(dex), linkedManifest=digest(manifest),
                        fieldlogFallbackInventory=tree(fallback),
                        fieldlogAndroidPlatformInventory=tree(inventory(source, fieldlog / "Platforms/Android")))
            link.update({"bridge/" + path.name: digest(path) for path in native.glob("*.o")})
            identity["build"].update(link_inputs_sha256=tree(link), native_fallback_sha256=tree(fallback),
                                     permissions_sha256=digest(java / "AndroidManifest.xml"))
        write(folder / "identity-input.json", identity)
        write(folder / "linked-inputs.json", link)


def verify_image(apk, installed, java, native, work, tools, ndk, env, version):
    signature = capture(env, tools / "apksigner", "verify", "--verbose", "--print-certs", "-Werr", apk)
    signer, = re.findall(r"^Signer #1 certificate SHA-256 digest: ([a-f0-9]{64})$", signature, re.M)
    require("Verified using v3 scheme (APK Signature Scheme v3): true" in signature
            and "Number of signers: 1" in signature, "Expected one v3 APK signer")
    capture(env, tools / "zipalign", "-c", "-P", "16", "4", apk)
    badging = capture(env, tools / "aapt2", "dump", "badging", apk)
    for entry in (f"package: name='{PACKAGE}' versionCode='{version}'", "minSdkVersion:'36'", "targetSdkVersion:'36'",
                  "native-code: 'arm64-v8a'", "application-debuggable",
                  "launchable-activity: name='dev.fieldlog.generatedr90.androidhost.PublicActivity'"):
        require(entry in badging, f"Missing APK badging: {entry}")
    permissions = capture(env, tools / "aapt2", "dump", "permissions", apk).splitlines()
    jni = native / Path(JNI).name
    elf = capture(env, ndk / "bin/llvm-readelf", "-h", "-l", "-d", jni)
    load = [line.split()[-1] for line in elf.splitlines() if line.strip().startswith("LOAD ")]
    needed = re.findall(r"\(NEEDED\).*?\[(.*?)\]", elf)
    require("AArch64" in elf and load and all(int(alignment, 16) >= 16384 for alignment in load),
            "JNI must be arm64 with 16 KiB LOAD alignment")
    require("libFoundationNetworking.so" in needed, "JNI is missing the linked HTTP transport dependency")
    jni_exports = None
    if version == 2:
        # The shared verifier reads javac headers from work/java. The package
        # member comparison below separately binds the rebuilt successor DEX.
        require(inventory(work / "java/jni", work / "java/jni") == inventory(java / "jni", java / "jni"),
                "Successor JNI headers changed")
        jni_exports = verify_jni(ndk, jni, work, env)
    with zipfile.ZipFile(apk) as image:
        names = image.namelist()
        require(len(names) == len(set(names)), "Duplicate APK member")
        members = {name: hashlib.sha256(image.read(name)).hexdigest()
                   for name in names if not name.startswith("META-INF/")}
    require({name.removeprefix(ASSETS): value for name, value in members.items() if name.startswith(ASSETS)}
            == inventory(installed, installed), "Packaged installed asset inventory differs")
    with zipfile.ZipFile(java / "manifest.apk") as linked:
        for name in linked.namelist():
            require(members[name] == hashlib.sha256(linked.read(name)).hexdigest(), f"Linked resource differs: {name}")
    require(members[JNI] == digest(jni) and members["classes.dex"] == digest(java / "dex/classes.dex"),
            "Packaged JNI or DEX differs from build output")
    return {"apkSHA256": digest(apk), "signerSHA256": signer, "v3": True, "zipAlignmentKiB": 16,
            "versionCode": version, "badging": badging.splitlines(), "permissions": permissions,
            "jniExports": jni_exports, "elfLoadAlignments": load, "elfNeeded": needed,
            "members": members}


def package(work, calculation, packet):
    stage_materials(work, calculation, packet)
    env = os.environ.copy()
    java_home = Path(env["JAVA_HOME"])
    sdk = Path(env["ANDROID_HOME"])
    tools = sdk / "build-tools/36.0.0"
    ndk = sdk / "ndk/27.1.12297006/toolchains/llvm/prebuilt/darwin-x86_64"
    swift_android = next((work / "swift-sdks").iterdir()) / "swift-android"
    capture(env, work / "host-build/debug/Seal", packet, work / "templates/manifest.json", packet / "reviewed.wasm", BASE)
    scripts = distributor(work, calculation)
    key = work / "https-development.p12"
    password = "FIELDLOG_LOCAL_APK_PASSWORD"
    sign_env = env | {password: secrets.token_hex(24), "FIELDLOG_PAIR_APK_KEYSTORE": str(key)}
    results = {}
    try:
        capture(sign_env, java_home / "bin/keytool", "-genkeypair", "-storetype", "PKCS12", "-keystore", key,
                "-alias", "fieldlog-local", "-storepass:env", password, "-keypass:env", password,
                "-keyalg", "EC", "-groupname", "secp256r1", "-validity", "30", "-dname", "CN=FieldLog Native HTTPS Test Pair")
        for label, java, native, script in zip(
                ("old", "successor"), (work / "java", work / "https-java"),
                (work / "payload", work / "https-payload"), scripts):
            folder = packet / label
            installed = folder / "Installed"
            identity = read(installed / "identity.json")
            host = read(folder / "host.json")
            require(identity["application"]["bundle_id"] == PACKAGE
                    and identity["build"]["link_inputs_sha256"] == tree(read(folder / "linked-inputs.json"))
                    and identity["build"]["trust_roots_sha256"] == digest(installed / "roots.json")
                    and host["runtime"] == read(folder / "assignment.json")["assignment"]["runtime"],
                    "Sealed APK identity does not bind the recorded package, link inputs, roots and offer")
            (folder / "identity-input.json").unlink()
            pins = folder / "installed.sha256.json"
            write(pins, inventory(installed, installed))
            apk = folder / "FieldLog.apk"
            capture(sign_env, sys.executable, "-B", script, "--output", apk, "--mixer-project", work / "project",
                    "--installed-checklist", installed, "--checklist-sha256", pins, "--java-home", java_home,
                    "--android-sdk", sdk, "--swift-android-sdk", swift_android, "--jni-library", native / Path(JNI).name,
                    "--dex", java / "dex/classes.dex", "--manifest-apk", java / "manifest.apk")
            results[label] = verify_image(apk, installed, java, native, work, tools, ndk, env, len(results) + 1)
    finally:
        key.unlink(missing_ok=True)

    old, new = results.values()
    require(digest(packet / "old/Installed/roots.json") == digest(packet / "successor/Installed/roots.json"),
            "APK OTA trust roots differ")
    require(old["signerSHA256"] == new["signerSHA256"] and old["permissions"] == new["permissions"]
            and old["elfNeeded"] == new["elfNeeded"], "Signer, effective permissions or linked dependency drift")
    original = read(calculation / "build-receipt.json")["apkMembersSHA256"]
    require(changed_members(original, old["members"]) == {ASSETS + name for name in ("identity.json", "roots.json")},
            "Re-signed storage-only APK changed beyond the new trust root and runtime")
    changed = changed_members(old["members"], new["members"])
    require(changed == {JNI, "classes.dex", "AndroidManifest.xml", ASSETS + "identity.json"}
            | {ASSETS + name for name in HTTPS}, f"Unexpected APK delta: {sorted(changed)}")
    write(packet / "build.json", {"publicBase": BASE, "fieldlogTrees": {"old": OLD_TREE, "successor": SUCCESSOR_TREE},
                                  "apks": results, "changedMembers": sorted(changed), "workspace": old["members"][ASSETS + "calculation-seed.json"],
                                  "payload": GUESTS["reviewed"], "httpsMaterials": HTTPS,
                                  "overlaySHA256": digest(HERE / "android-successor.patch")})


def changed_members(old, new):
    return {name for name in old.keys() | new.keys() if old.get(name) != new.get(name)}


def seal(work, calculation, packet):
    receipts = ("https-source", "https-native", "https-java", "https-host", "https-package", "https-replay")
    commands = {name: read(work / "logs" / f"{name}.json") for name in receipts}
    require(all(row["custody"] == "closed" and row["exit"] == 0 and "interrupted" not in row
                for row in commands.values()), "Incomplete successor stage")
    shutil.copyfile(calculation / "rebuild-receipt.json", packet / "calculation-rebuild.json")
    for name in ("android-origin.py", "ANDROID-HANDOFF.md"):
        shutil.copyfile(HERE / name, packet / name)
    shutil.copyfile(CALC.parent / "android-readback.py", packet / "android-readback.py")
    write(packet / "commands.json", commands)
    write(packet / "recipe-inputs.json", inventory(REPO, HERE))
    with (packet / "SHA256SUMS").open("x") as sums:
        for name, value in sorted(inventory(packet, packet).items()):
            if name != "SHA256SUMS":
                sums.write(f"{value}  {name}\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["compose", "package", "seal"])
    parser.add_argument("campaign", type=Path)
    args = parser.parse_args()
    campaign = args.campaign.resolve(strict=True)
    if args.stage == "compose":
        compose(campaign / "work")
    else:
        globals()[args.stage](campaign / "work", campaign / "calculation", campaign / "handoff")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as error:
        detail = error.output or error.stderr or str(error)
        raise SystemExit(detail.decode(errors="replace") if isinstance(detail, bytes) else detail) from error
