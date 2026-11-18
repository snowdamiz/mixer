"""Inspect the actual unsigned Android APK before discarding the build tree."""

from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
from zipfile import ZipFile


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def run(*args):
    return subprocess.check_output(args, text=True, stderr=subprocess.STDOUT, timeout=30)


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main(scratch, prepared, compatibility):
    project = scratch / "FieldLogGenerated"
    output = project / ".mixer/android-build"
    raw = output / "build-receipt.json"
    build = json.loads(raw.read_text())
    apk = output / "FieldLogGenerated-unsigned.apk"
    platform = Path(os.environ["ANDROID_HOME"]) / "build-tools/37.0.0"
    ndk = Path(os.environ["NDK_R27D"])
    llvm = ndk / "toolchains/llvm/prebuilt/darwin-x86_64/bin"
    permission = "uses-permission: name='android.permission.INTERNET'"
    identity = [line for line in run(platform / "aapt2", "dump", "badging", apk).splitlines()
                if line.startswith(("package:", "minSdkVersion:", "targetSdkVersion:", "launchable-activity:", "native-code:"))]
    require(permission in run(platform / "aapt2", "dump", "permissions", apk).splitlines(),
            "INTERNET missing from the packaged manifest")
    require(build["android_host"] == "public-v4" and build["source_profile"]["id"] == "mixer.android-source-pair.23",
            "expected generated public-v4 FieldLog with Pair23 admission")
    require(build["source_tree_sha256"] == build["source_tree_after_sha256"], "source inputs changed during build")
    require(build["apk_sha256"] == digest(apk), "APK does not match build receipt")
    run(platform / "zipalign", "-c", "-P", "16", "4", apk)

    integration = prepared / "app/Integrations/GeneratedReport"
    app_inputs = {
        **{path: project / "Sources" / path.relative_to(integration / "Sources")
           for folder in ("FieldLogStorage", "FieldLogModels", "FieldLogFeatures")
           for path in (integration / "Sources" / folder).glob("*.swift")},
        **{path: project / "Platforms/Android/Sources/AppAndroid" / path.name
           for path in (integration / "Sources/FieldLogAndroid").glob("*.swift")},
        **{path: project / "Platforms/Android/Tests/AppAndroidTests" / path.name
           for path in (integration / "Tests/FieldLogAndroidTests").glob("*.swift")},
        **{path: project / path.relative_to(integration)
           for path in (integration / "Platforms/Android/Java").rglob("*.java")},
        **{integration / name: project / name
           for name in ("Platforms/Android/AndroidManifest.xml", "Platforms/Android/Bridge/PublicBridge.c",
                        "Platforms/Android/Package.swift", "Platforms/Android/Package.resolved")},
        integration / "Platforms/Android/ApplicationPackage.swift": project / "Package.swift",
    }
    require(all(digest(before) == digest(after) for before, after in app_inputs.items()),
            "generated app inputs differ from the prepared patch")

    packages = build["native_dependencies"]
    libraries = output / "apk/lib/arm64-v8a"
    require("libFoundationNetworking.so" in packages["libAppAndroid.so"], "Swift lacks the Android networking dependency")
    require("libz.so" in packages["libFoundationNetworking.so"], "missing FoundationNetworking zlib dependency")
    system = json.loads((ndk / "meta/system_libs.json").read_text())
    require(int(system["libz.so"]) <= int(build["application_min_api"]), "zlib unavailable at the app API floor")
    require(not (libraries / "libz.so").exists(), "system zlib was bundled")
    with ZipFile(apk) as archive:
        names = archive.namelist()
        require(len(set(names)) == len(names), "duplicate APK entry")
        require(not any(name.endswith("/libz.so") for name in names), "unexpected private zlib in APK")
        require({name: sha256(archive.read(name)).hexdigest() for name in names} == build["apk_entries"],
                "packaged bytes differ from build receipt")
    for path in libraries.glob("*.so"):
        header = run(llvm / "llvm-readelf", "-h", path)
        require("ELF64" in header and "AArch64" in header, f"wrong target for {path.name}")
        segments = [line.split() for line in run(llvm / "llvm-readelf", "-lW", path).splitlines()
                    if line.lstrip().startswith("LOAD ")]
        require(segments and all(int(row[-1], 16) >= 16384 and
                                 (int(row[1], 16) - int(row[2], 16)) % 16384 == 0 for row in segments),
                f"16 KiB segment alignment missing for {path.name}")
    symbols = {"mixer_public_android_submit", "mixer_public_android_poll"}
    swift = libraries / "libAppAndroid.so"
    jni = libraries / "libmixer_public_android_jni.so"
    for name, kind, library in [(symbol, "--defined-only", swift) for symbol in symbols] + [
        (symbol, "--undefined-only", jni) for symbol in symbols
    ] + [("JNI_OnLoad", "--defined-only", jni)]:
        observed = {line.split()[-1] for line in run(llvm / "llvm-nm", "-D", kind, library).splitlines() if line}
        require(name in observed, f"missing {name} in {library.name}")
    dex = run(platform / "dexdump", "-d", output / "dex/classes.dex")
    require("refreshQueueNative" in dex and "Ldev/fieldlog/generatedr90/androidhost/PublicActivity;" in dex,
            "queue JNI declaration or Activity missing from DEX")

    swift_build = next(item for item in build["commands"] if "--product" in item["command"] and
                       "--show-bin-path" not in item["command"])
    strict_jni = next(item for item in build["commands"] if "-Wl,--no-undefined" in item["command"])
    require(swift_build["exit_code"] == strict_jni["exit_code"] == 0, "cross build or strict JNI link failed")
    recipe = json.loads((project / ".fieldlog-build/commands.json").read_text())
    require(all(item["exitCode"] == 0 and item["ownedGroupAbsent"] for item in recipe), "recipe custody unresolved")
    inputs = list((scratch / "work/tmp").glob("mixer-command-receipts-*/command-*/receipt.json"))
    groups = [json.loads(path.read_text()) for path in inputs]
    require(groups and all(item["terminalCustody"] and item["directChildReaped"] and item["ownedGroupAbsent"]
                           and item["stdoutEOF"] and item["stderrEOF"] and item["descriptorsClosed"] for item in groups),
            "nested command custody unresolved")
    strict_source = scratch / "link-closure.c"
    strict_source.write_text("int fieldlog_android_link_check(void) { return 0; }\n")
    strict_command = [str(llvm / "aarch64-linux-android28-clang"), "-shared", "-Wl,--no-undefined",
                      "-Wl,--no-allow-shlib-undefined", "-Wl,--no-as-needed",
                      f"-Wl,-rpath-link,{libraries}", f"-L{libraries}", str(strict_source),
                      "-lmixer_public_android_jni", "-lAppAndroid", "-lz",
                      "-o", str(scratch / "link-closure.so")]
    link = subprocess.run(strict_command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30)
    require(link.returncode == 0, f"Android native closure link failed: {link.stdout[-4096:]}")
    receipt = {
        "status": "pass",
        "scope": "Unsigned arm64 Android cross-build and static APK inspection; no device runtime",
        "candidateTree": run("git", "-C", prepared / "app", "write-tree").strip(),
        "pair23": "735ecec14e10e2dfed1e58a122c3fab08e569bef",
        "pair23CompatibilityPatchSHA256": digest(compatibility),
        "cliSHA256": digest(scratch / "work/cli-build/debug/mixer"),
        "sourceProfile": build["source_profile"],
        "sourceTreeSHA256": build["source_tree_sha256"],
        "appInputsByteMatched": len(app_inputs),
        "lock": build["platform_dependency_lock"],
        "toolchain": {
            "versions": {key: build["toolchain"][key] for key in ("swift_version", "javac_version", "python_version", "sdk_id")},
            "xcode": run("xcodebuild", "-version").splitlines(),
            "ndk": "r27d 27.3.13750724",
        },
        "apk": {
            "bytes": apk.stat().st_size, "sha256": digest(apk), "payloadSHA256": build["apk_content_sha256"],
            "identity": identity, "permissionsChecked": [permission], "countOfARM64Libraries": len(packages),
            "swiftELFSHA256": digest(swift), "jniELFSHA256": digest(jni), "zipAndELF16KiBAlignment": True,
            "foundationNetworkingRequired": True, "unbundledSystemZlibRequired": True,
        },
        "commands": {
            "recipe": recipe, "swiftRelease": swift_build["command"], "strictJniLink": strict_jni["command"],
            "nativeClosureLink": {"command": strict_command, "exitCode": link.returncode, "output": link.stdout[-4096:]},
            "nestedTerminalGroups": len(groups), "rawBuildReceiptSHA256": digest(raw),
        },
    }
    (scratch / "android.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(f"PASS unsigned arm64 APK {receipt['apk']['sha256']}")


if __name__ == "__main__":
    main(*map(Path, sys.argv[1:]))
