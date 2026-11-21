#!/usr/bin/env python3
"""Exercise the Pair25 composition and ZIP readback without building or signing an APK."""

import argparse
import ast
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile

HERE = Path(__file__).resolve().parent
SCRIPTS = "Integrations/GeneratedReport/scripts"
INNER = f"{SCRIPTS}/build-signed-checklist-android.py"
OUTER = f"{SCRIPTS}/pair25/package-entry-commit.py"
NOTICE = HERE / "Rust-1.99.0-Android-NOTICES.txt"
RUST_MEMBER = "third-party-notices/" + NOTICE.name


def sha(data):
    return hashlib.sha256(data).hexdigest()


def git(directory, *args, data=None):
    return subprocess.run(
        ["git", "-C", str(directory), *args], input=data, stdout=subprocess.PIPE,
        check=True, timeout=15,
    ).stdout


def platform_notices(mixer, mixer_revision, swift_sdk, android_sdk):
    source = git(mixer, "show", f"{mixer_revision}:cli/Sources/MixerBuild/Resources/android-build.py")
    icu = next(
        ast.literal_eval(node.value).encode()
        for node in ast.parse(source).body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "APPLE_ICU_LICENSE" for target in node.targets)
    )
    ndk = android_sdk / "ndk/27.1.12297006"
    return {
        "third-party-notices/Android-NDK-NOTICE.toolchain.txt": (ndk / "NOTICE.toolchain").read_bytes(),
        "third-party-notices/Android-NDK-NOTICE.txt": (ndk / "NOTICE").read_bytes(),
        "third-party-notices/Apple-ICU-76.1-LICENSE.txt": icu,
        "third-party-notices/Swift-SDK-LICENSE.txt": (
            swift_sdk / "swift-resources/usr/share/swift/LICENSE.txt"
        ).read_bytes(),
    }


class Packaging(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="pair25-notice-case-")
        self.addCleanup(self.tmp.cleanup)
        self.work = Path(self.tmp.name)
        self.assets = {"assets/MixerAppearanceV2/descriptor.json": b"fixture"}
        self.library = self.work / "libmixer_public_android_jni.so"
        self.library.write_bytes(b"ELF placeholder")
        self.dex = self.work / "classes.dex"
        self.dex.write_bytes(b"DEX placeholder")
        self.manifest = self.work / "manifest.apk"
        with zipfile.ZipFile(self.manifest, "x") as archive:
            for name in PACKAGER["MANIFEST_MEMBERS"]:
                archive.writestr(name, name.encode())
        self.args = SimpleNamespace(
            output=self.work / "output.apk", mixer_project=self.work, installed_checklist=self.work,
            checklist_sha256=self.work / "checklist.json", java_home=self.work,
            android_sdk=self.work, swift_android_sdk=self.work, manifest_apk=self.manifest,
            dex=self.dex, jni_library=self.library, development_keystore=self.dex,
            pair25_rust_notice=NOTICE,
        )

    def assemble(self, notices=None, *, omit=False, stale=False, duplicate=False, phase=None):
        # Only emulate the external tools. The composed production packager
        # writes the unsigned ZIP and verifies both ZIPs before exposing output.
        def inspect(path):
            with zipfile.ZipFile(path) as archive:
                for name, data in PLATFORM.items():
                    self.assertEqual(archive.read(name), data)
                self.assertEqual(archive.read(RUST_MEMBER), NOTICE.read_bytes())

        def mutate(path):
            with zipfile.ZipFile(path) as archive:
                entries = {name: archive.read(name) for name in archive.namelist()}
            if omit:
                entries.pop(RUST_MEMBER)
            if stale:
                entries[RUST_MEMBER] += b"stale"
            with zipfile.ZipFile(path, "w") as archive:
                for name, data in entries.items():
                    archive.writestr(name, data)
                if duplicate:
                    with self.assertWarns(UserWarning):
                        archive.writestr(RUST_MEMBER, entries[RUST_MEMBER])

        def tool(env, executable, action, *args):
            if executable.name == "zipalign" and action == "-P":
                inspect(args[-2])
                shutil.copyfile(args[-2], args[-1])
            elif executable.name == "apksigner" and action == "sign":
                output = args[args.index("--out") + 1]
                shutil.copyfile(args[-1], output)
                with zipfile.ZipFile(output, "a") as archive:
                    archive.writestr("META-INF/test-only", b"no signature")
                if phase == "signed":
                    mutate(output)
            elif executable.name == "apksigner" and action == "verify":
                return "Verified using v3 scheme (APK Signature Scheme v3): true"
            elif executable.name == "aapt2":
                return "\n".join((
                    "minSdkVersion:'36'", "targetSdkVersion:'37'", "native-code: 'arm64-v8a'",
                    "package: name='dev.fieldlog.generatedr90' versionCode='1'",
                    "launchable-activity: name='dev.fieldlog.generatedr90.androidhost.PublicActivity' label='FieldLog'",
                ))
            return ""

        def verify_image(path, *args, **kwargs):
            if phase == "unsigned" and path.name == "unsigned.apk":
                mutate(path)
            return PACKAGER["verify_image"](path, *args, **kwargs)

        functions = PACKAGER["build"].__globals__
        notice_bytes = PLATFORM if notices is None else notices
        with patch.dict(functions, {
            "appearance_asset": lambda _: next(iter(self.assets.values())),
            "checklist_assets": lambda *_: {},
            "native_libraries": lambda *_: {self.library.name: self.library},
            "runtime_notices": lambda *_: dict(notice_bytes),
            "run": tool,
            "verify_image": verify_image,
        }), patch.dict("os.environ", {PACKAGER["SIGNER_PASSWORD"]: "unused"}):
            with contextlib.redirect_stdout(io.StringIO()):
                PACKAGER["build"](self.args)
        inspect(self.args.output)

    def test_exact_upstream_text_slices(self):
        sources = json.loads((HERE / "sources.json").read_bytes())
        data = NOTICE.read_bytes()
        self.assertEqual({"bytes": len(data), "sha256": sha(data)}, sources["bundle"])
        self.assertEqual(sha(data), PACKAGER["PAIR25_RUST_NOTICE_SHA256"])
        self.assertEqual(len(sources["texts"]), 20)
        self.assertEqual(sum(len(item["sources"]) for item in sources["texts"]), 27)
        for item in sources["texts"]:
            with self.subTest(source=item["sources"][0]["label"]):
                start = item["offset"]
                self.assertEqual(sha(data[start:start + item["bytes"]]), item["sha256"])

    def test_exact_notices_in_unsigned_and_signed_zip_shape(self):
        self.assemble()

    def test_missing_or_stale_input_notice(self):
        for file, failure in ((self.work / "missing", FileNotFoundError), (self.work / "stale", ValueError)):
            with self.subTest(file=file):
                if file.name == "stale":
                    file.write_bytes(NOTICE.read_bytes() + b"stale")
                self.args.pair25_rust_notice = file
                with self.assertRaises(failure):
                    self.assemble()
                self.assertFalse(self.args.output.exists())

    def test_missing_or_stale_platform_notice(self):
        platform = dict(PLATFORM)
        first = next(iter(platform))
        for value in (None, b"stale"):
            with self.subTest(value=value):
                if value is None:
                    platform.pop(first)
                else:
                    platform[first] = value
                with self.assertRaisesRegex(ValueError, "pinned inventory"):
                    self.assemble(platform)
                self.assertFalse(self.args.output.exists())

    def test_missing_stale_and_duplicate_unsigned_and_signed_zip_notice(self):
        for phase in ("unsigned", "signed"):
            for change in ("omit", "stale", "duplicate"):
                with self.subTest(phase=phase, change=change):
                    with self.assertRaisesRegex(ValueError, "APK runtime notice|Duplicate APK entry"):
                        self.assemble(phase=phase, **{change: True})
                    self.assertFalse(self.args.output.exists())

    def test_notice_cannot_be_omitted_from_successor_cli(self):
        with patch.object(sys, "argv", ["package-entry-commit.py", "work", "project", "out"]):
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                WRAPPER["main"]()
        self.assertEqual(error.exception.code, 2)

    def test_vm_toolchain_must_match_notice(self):
        version = "\n".join(sorted(PRODUCERS["RUST_VERSION_FIELDS"]))
        PRODUCERS["require_notice_toolchain"]({"rustc": version})
        for invalid in ({}, {"rustc": 0}, {"rustc": version + "\nrelease: 1.98.0"},
                        {"rustc": version.replace("1.99.0", "1.98.0")},
                        {"rustc": version.replace("b940084d7e", "0000000000")},
                        {"rustc": version.replace("23.1.1", "23.1.0")}):
            with self.subTest(invalid=invalid):
                with self.assertRaisesRegex(ValueError, "pinned Rust"):
                    PRODUCERS["require_notice_toolchain"](invalid)


class Handoff(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="handoff-", dir=WORK)
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name)
        self.project = self.directory / "prepared"
        self.tools = self.directory / "tools"
        self.tools.mkdir()
        self.registry = self.directory / "sdk"
        self.sdk = self.registry / "swift-6.3.3-RELEASE_android.artifactbundle/swift-android"
        self.ndk = self.tools / "ndk/27.1.12297006"
        self.rust = self.directory / NOTICE.name
        self.rust.write_bytes(NOTICE.read_bytes())
        self.driver = self.project / "Generated/MixerAndroid/android-build.py"
        self.put(self.driver, (WORK / "mixer/cli/Sources/MixerBuild/Resources/android-build.py").read_bytes())
        adapter = WORK / "mixer/native/android"
        for source in (adapter / "app/src/dev/mixer/android").glob("*.java"):
            if source.name not in {"MixerActivity.java", "AdapterInstrumentation.java",
                                   "AppearanceDescriptorV1.java", "AppearanceResolutionV1.java"}:
                self.put(self.driver.parent / "app/src/dev/mixer/android" / source.name, source.read_bytes())
        descriptor = adapter / "tests/EditorTransactionPackets/descriptor.json"
        self.put(self.driver.parent / "app" / WRAPPER["APPEARANCE"], descriptor.read_bytes())
        for name in ("Package.resolved", "Sources/MixerCapabilities/GeneratedIdentity.swift"):
            self.put(self.project / "Generated/MixerSDK" / name, (WORK / "mixer/sdk" / name).read_bytes())
        self.put(self.project / "mixer.lock", json.dumps({
            "android": {"profile": WRAPPER["ADMISSION"]["PAIR25_PROFILE"]}
        }).encode())
        self.platform_paths = {
            self.ndk / "NOTICE": "third-party-notices/Android-NDK-NOTICE.txt",
            self.ndk / "NOTICE.toolchain": "third-party-notices/Android-NDK-NOTICE.toolchain.txt",
            self.sdk / "swift-resources/usr/share/swift/LICENSE.txt": "third-party-notices/Swift-SDK-LICENSE.txt",
        }
        for path, name in self.platform_paths.items():
            self.put(path, PLATFORM[name])
        self.put(self.sdk.parent / "info.json", b"{}")
        self.put(self.tools / "build-tools/36.0.0/aapt2", b"inert tool")
        for name in ("swift-frontend", "swiftc", "wasm-ld"):
            self.put(self.directory / name, b"inert tool")
        for name in ("java", "jni", "android-engine", "android-package"):
            self.addCleanup(lambda name=name: shutil.rmtree(WORK / name, ignore_errors=True))
        self.snapshot = WORK / PRODUCERS["NOTICE_SNAPSHOT"]
        self.addCleanup(lambda: self.snapshot.unlink(missing_ok=True))
        self.engine_path = WORK / "android-engine/receipt.json"
        self.archive = WORK / PRODUCERS["VM_ARCHIVE"]
        self.put(self.archive, b"inert VM archive")
        self.put(WORK / "android-engine/source.tar", b"inert VM source archive")
        self.engine = {
            "rustc": "\n".join(sorted(PRODUCERS["RUST_VERSION_FIELDS"])),
            "source_revision": REVISION,
            "target_selector": "android",
            "rust_target": "aarch64-linux-android",
            "library": {"sha256": sha(self.archive.read_bytes())},
            "source_manifest_sha256": sha(b"inert VM source manifest"),
            "source_archive_sha256": sha(b"inert VM source archive"),
        }
        self.engine_path.write_text(json.dumps(self.engine))
        self.start_patch(patch.dict(os.environ, {
            "ANDROID_HOME": str(self.tools), "MIXER_SWIFT_SDKS_PATH": str(self.registry),
            "MIXER_SWIFT": str(self.directory / "swift"), "FIELDLOG_SWIFT_BIN": str(self.directory),
        }))
        self.effects = []
        self.start_patch(patch.dict(PRODUCERS["main"].__globals__, {
            "subprocess": SimpleNamespace(check_output=subprocess.check_output, run=self.produce),
        }))
        self.start_patch(patch.dict(WRAPPER["assemble"].__globals__, {
            "capture": self.unexpected_effect,
            "subprocess": SimpleNamespace(check_output=self.unexpected_effect,
                                           CalledProcessError=subprocess.CalledProcessError,
                                           TimeoutExpired=subprocess.TimeoutExpired,
                                           SubprocessError=subprocess.SubprocessError),
        }))
        self.start_patch(patch.dict(PACKAGER, {"local_development_signer": self.unexpected_effect}))

    def start_patch(self, change):
        change.start()
        self.addCleanup(change.stop)

    @staticmethod
    def put(path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def unexpected_effect(self, *command, **kwargs):
        self.effects.append(("unexpected", str(command[0])))
        self.fail(f"Unexpected tool launch: {command}")

    def produce(self, command, cwd, **kwargs):
        kind = "java" if Path(command[2]).name == "build-java.zsh" else "jni"
        self.assertEqual(cwd, WORK)
        self.assertEqual(command[:2], ["/bin/zsh", "-f"])
        self.effects.append(("producer", kind))
        fingerprint = PRODUCERS["ADMISSION"]["PAIR25_RESEALED_FINGERPRINT"]
        for name in PRODUCERS["PRODUCTS"][kind]:
            self.put(WORK / name, fingerprint.encode())
        if kind == "java":
            header = WORK / PRODUCERS["PRODUCTS"]["java"][-1]
            header.write_text("\n".join(f"JNICALL Java_stub_{i}" for i in range(5)))
            with zipfile.ZipFile(WORK / "java/manifest.apk", "w") as archive:
                for name in PACKAGER["MANIFEST_MEMBERS"]:
                    archive.writestr(name, name.encode())

    def producer(self, phase):
        with patch.object(sys, "argv", ["build-products.py", phase, str(WORK),
                                       str(self.project), "--rust-notice", str(self.rust)]):
            PRODUCERS["main"]()

    def pack(self, name="out"):
        output = self.directory / name
        with patch.object(sys, "argv", ["package-entry-commit.py", str(WORK), str(self.project),
                                       str(output), "--rust-notice", str(self.rust)]):
            WRAPPER["main"]()
        return output

    def build_producers(self):
        for phase in ("preflight", "java", "jni"):
            self.producer(phase)
        self.assertEqual(self.effects, [("producer", "java"), ("producer", "jni")])
        self.effects.clear()
        snapshot = json.loads(self.snapshot.read_bytes())
        self.assertEqual(snapshot, {
            "vmReceiptSHA256": sha(self.engine_path.read_bytes()),
            "runtimeNoticesSHA256": {name: sha(data) for name, data in PLATFORM.items()} |
                                   {RUST_MEMBER: sha(self.rust.read_bytes())},
        })
        for kind in ("java", "jni"):
            receipt_path = PRODUCERS["receipt_path"](kind, WORK)
            self.assertEqual(json.loads(receipt_path.read_bytes())["inputs"]["noticeSnapshot"], snapshot)
        return snapshot

    def test_producers_require_preflight_and_bind_the_same_snapshot(self):
        for kind in ("java", "jni"):
            with self.assertRaises(FileNotFoundError):
                self.producer(kind)
        self.assertEqual(self.effects, [])
        self.build_producers()
        with self.assertRaisesRegex(ValueError, "precede both producers"):
            self.producer("preflight")

    def test_preflight_refuses_changed_notice_bytes(self):
        paths = list(self.platform_paths) + [self.driver, self.rust]
        for path in paths:
            with self.subTest(path=path.name):
                original = path.read_bytes()
                if path == self.driver:
                    path.write_bytes(original.replace(b"UNICODE LICENSE V3", b"UNICODE LICENSE V0", 1))
                else:
                    path.write_bytes(original + b"changed")
                with self.assertRaisesRegex(ValueError, "pinned inventory|SHA-256 pin"):
                    self.producer("preflight")
                path.write_bytes(original)
                self.assertFalse(self.snapshot.exists())
        self.assertEqual(self.effects, [])

    def test_preflight_refuses_nonregular_and_oversized_inputs(self):
        for path in (*self.platform_paths, self.driver, self.rust, self.engine_path):
            original = path.with_name(path.name + ".original")
            path.rename(original)
            for shape in ("missing", "symlink", "fifo", "directory", "oversized"):
                with self.subTest(path=path.name, shape=shape):
                    if shape == "symlink":
                        path.symlink_to(original)
                    elif shape == "fifo":
                        os.mkfifo(path)
                    elif shape == "directory":
                        path.mkdir()
                    elif shape == "oversized":
                        with path.open("xb") as stream:
                            stream.truncate(2 * 1024 * 1024 + 1)
                    with self.assertRaises((OSError, ValueError)):
                        self.producer("preflight")
                    if shape == "directory":
                        path.rmdir()
                    else:
                        path.unlink(missing_ok=True)
                    self.assertFalse(self.snapshot.exists())
            original.rename(path)
        self.assertEqual(self.effects, [])

    def test_preflight_refuses_oversized_vm_archive_without_reading_it(self):
        with self.archive.open("wb") as stream:
            stream.truncate(512 * 1024 * 1024 + 1)
        with self.assertRaisesRegex(ValueError, "bounded, regular VM archive"):
            self.producer("preflight")
        self.assertFalse(self.snapshot.exists())
        self.assertEqual(self.effects, [])

    def test_reformatted_vm_receipt_refuses_before_either_producer(self):
        self.producer("preflight")
        old = self.engine_path.read_bytes()
        self.engine_path.write_bytes(old + b"\n")
        for kind in ("java", "jni"):
            with self.subTest(kind=kind), self.assertRaisesRegex(ValueError, "VM receipt bytes differ"):
                self.producer(kind)
        self.assertEqual(self.effects, [])
        self.assertFalse((WORK / "java").exists())
        self.assertFalse((WORK / "jni").exists())

    def test_wrong_vm_receipt_with_identical_jni_archive_refuses_before_effects(self):
        snapshot = self.build_producers()
        jni = json.loads(PRODUCERS["receipt_path"]("jni", WORK).read_bytes())
        self.engine["unbound_by_old_jni"] = "replacement receipt"
        self.engine_path.write_text(json.dumps(self.engine))
        self.assertEqual(jni["inputs"]["vmArchiveSHA256"], self.engine["library"]["sha256"])
        self.assertEqual(jni["inputs"]["vmArchiveSHA256"], sha(self.archive.read_bytes()))
        self.assertNotEqual(snapshot["vmReceiptSHA256"], sha(self.engine_path.read_bytes()))
        with self.assertRaisesRegex(ValueError, "VM receipt bytes differ"):
            self.pack()
        self.assertEqual(self.effects, [])
        out = self.directory / "out"
        self.assertIn("VM receipt bytes differ", (out / "package.log").read_text())
        self.assertEqual({path.name for path in out.iterdir()}, {"package.log"})

    def test_packaging_refuses_a_different_snapshot_in_either_receipt(self):
        self.build_producers()
        for kind in ("java", "jni"):
            path = PRODUCERS["receipt_path"](kind, WORK)
            original = path.read_bytes()
            old_binding = json.loads(original)
            del old_binding["inputs"]["noticeSnapshot"]
            path.write_text(json.dumps(old_binding))
            with self.subTest(kind=kind), self.assertRaisesRegex(ValueError, f"Pair25 {kind} products differ"):
                self.pack(kind)
            path.write_bytes(original)
        self.assertEqual(self.effects, [])

    def test_late_sidecar_collision_preserves_bytes_and_log(self):
        self.package_with_inert_tools(collision=True)

    def test_publication_writes_matching_sidecar_and_apk(self):
        self.package_with_inert_tools(collision=False)

    def test_drift_during_guest_build_refuses_before_sealer_and_signer(self):
        self.package_with_inert_tools(collision=False, drift="guest")

    def test_drift_during_sealing_refuses_before_apk_signer(self):
        self.package_with_inert_tools(collision=False, drift="seal")

    def package_with_inert_tools(self, *, collision, drift=None):
        snapshot = self.build_producers()
        payload = b"inert Wasm"
        cert = b"inert certificate"
        fingerprint = PRODUCERS["ADMISSION"]["PAIR25_RESEALED_FINGERPRINT"]
        original_digest = WRAPPER["digest"]

        def signer(stage, jdk, env):
            self.effects.append(("inert", "keytool key generation"))
            return stage / "unused.p12", env

        def cert_export(*args, **kwargs):
            self.effects.append(("inert", "keytool certificate export"))
            return cert

        def capture(*args, **kwargs):
            executable = Path(args[0]).name
            action = str(args[1])
            self.effects.append(("inert", executable + " " + action))
            if executable == "bash":
                self.put(args[-1] / "entry-commit.wasm", payload)
                if drift == "guest":
                    self.engine_path.write_bytes(self.engine_path.read_bytes() + b"\n")
            elif "export-native-preimage.py" in str(args[2] if len(args) > 2 else ""):
                args[-1].write_bytes(b"inert preimage")
                return json.dumps({"sources": 18, "nativeImplementationSHA256": fingerprint})
            elif executable == "llvm-nm":
                return "\n".join([*(f"Java_stub_{i}" for i in range(5)), "JNI_OnLoad", "mxis_guest_ui_witness"])
            elif executable == "git":
                return subprocess.check_output(args, text=True, timeout=10).strip()
            elif executable == "swift-frontend":
                return "inert Swift version"
            elif executable == "FieldLogEntryCommitSeal":
                if action == "seal":
                    origin, binding, guest, installed = args[2:]
                    for name in ("bridge.json", "port.txt", "storage-grant.json", "storage.json"):
                        shutil.copyfile(origin / "Installed" / name, installed / name)
                    shutil.copyfile(guest, installed / guest.name)
                    (installed / "entry-commit-v1.txt").write_bytes(b"fieldlog-entry-commit-v1\n")
                    identity = json.loads(binding.read_bytes())
                    identity["application"] = {"bundle_id": WRAPPER["APP_ID"]}
                    identity["capabilities"] = [{"native_sha256": fingerprint}]
                    identity["capability_execution"] = "inert"
                    identity["build"]["generated_bridge_sha256"] = fingerprint
                    (installed / "identity.json").write_text(json.dumps(identity))
                    if drift == "seal":
                        self.engine_path.write_bytes(self.engine_path.read_bytes() + b"\n")
                return "inert runtime"
            elif str(args[2] if len(args) > 2 else "").endswith(INNER):
                paths = {arg: Path(args[index + 1]) for index, arg in enumerate(args[:-1])
                         if arg in ("--output", "--installed-checklist", "--manifest-apk", "--dex", "--jni-library")}
                with (zipfile.ZipFile(paths["--output"], "x") as apk,
                      zipfile.ZipFile(paths["--manifest-apk"]) as manifest):
                    for name in manifest.namelist():
                        apk.writestr(name, manifest.read(name))
                    apk.write(paths["--dex"], "classes.dex")
                    native = paths["--jni-library"]
                    apk.write(native, "lib/arm64-v8a/" + native.name)
                    apk.write(self.driver.parent / "app" / WRAPPER["APPEARANCE"], WRAPPER["APPEARANCE"])
                    for file in paths["--installed-checklist"].iterdir():
                        apk.write(file, WRAPPER["ASSETS"] + file.name)
                    for name, data in PLATFORM.items():
                        apk.writestr(name, data)
                    apk.writestr(RUST_MEMBER, self.rust.read_bytes())
                return "inert APK signer output"
            elif executable == "apksigner":
                return "Signer #1 certificate SHA-256 digest: " + sha(cert)
            elif executable in {"zipalign", "aapt2"}:
                return "inert verification"
            else:
                self.fail(f"Unexpected packaging command: {args}")
            return "inert tool output"

        real_link = os.link
        competing = b'{"owner":"competing evidence"}\n'
        out = self.directory / "out"

        def link(src, dst):
            if collision and dst == out / "apk-evidence.json":
                with dst.open("xb") as stream:
                    stream.write(competing)
            real_link(src, dst)

        with (patch.dict(WRAPPER["assemble"].__globals__, {
                  "PAYLOAD_BYTES": len(payload), "PAYLOAD_SHA256": sha(payload),
                  "digest": lambda path: fingerprint if path.name == "native-preimage.json" else original_digest(path),
                  "capture": capture,
              }), patch.dict(PACKAGER, {"local_development_signer": signer}),
              patch.object(WRAPPER["assemble"].__globals__["subprocess"], "check_output", cert_export),
              patch("os.link", side_effect=link), contextlib.redirect_stdout(io.StringIO())):
            if drift:
                with self.assertRaisesRegex(ValueError, "VM receipt bytes differ"):
                    self.pack()
            elif collision:
                with self.assertRaises(FileExistsError):
                    self.pack()
            else:
                self.pack()
        log = (out / "package.log").read_text()
        if drift:
            self.assertNotIn("inert APK signer output", log)
            self.assertEqual({path.name for path in out.iterdir()}, {"package.log"})
            self.assertEqual(("inert", "FieldLogEntryCommitSeal seal") in self.effects, drift == "seal")
            self.assertEqual(("inert", "keytool key generation") in self.effects, drift == "seal")
            return
        self.assertIn("inert APK signer output", log)
        evidence = out / "apk-evidence.json"
        apks = list(out.glob("*.apk"))
        self.assertFalse(list(out.glob(".seal-*")))
        if collision:
            self.assertEqual(evidence.read_bytes(), competing)
            self.assertEqual(apks, [])
            self.assertIn("Packaging failed", log)
        else:
            self.assertEqual(len(apks), 1)
            data = json.loads(evidence.read_bytes())
            self.assertEqual(data["apkSHA256"], sha(apks[0].read_bytes()))
            self.assertEqual(data["linkInputs"]["native/vm-receipt.json"], snapshot["vmReceiptSHA256"])
            self.assertEqual(data["linkInputs"]["runtimeNoticesSHA256"], snapshot["runtimeNoticesSHA256"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mixer", type=Path, required=True)
    parser.add_argument("--android-sdk", type=Path, required=True)
    parser.add_argument("--swift-sdk", type=Path, required=True)
    parser.add_argument("--scratch", type=Path, required=True, help="Existing owned scratch parent")
    args = parser.parse_args()
    successor = runpy.run_path(str(HERE / "prepare-successor.py"))
    with tempfile.TemporaryDirectory(prefix="pair25-notice-sources-", dir=args.scratch) as tmp:
        WORK = Path(tmp) / "work"
        pins = successor["prepare"](WORK, args.mixer.resolve(strict=True))
        REVISION = pins["mixer"]["revision"]
        PLATFORM = platform_notices(args.mixer, REVISION, args.swift_sdk, args.android_sdk)
        WRAPPER = runpy.run_path(str(WORK / "fieldlog" / OUTER))
        PRODUCERS = WRAPPER["PRODUCERS"]
        PACKAGER = PRODUCERS["PACKAGING"]
        result = unittest.main(argv=[sys.argv[0]], verbosity=2, exit=False).result
    sys.exit(0 if result.wasSuccessful() else 1)
