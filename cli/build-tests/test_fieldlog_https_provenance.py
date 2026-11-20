"""Producer controls. The calculation APKs may only exercise native material."""
import argparse
import base64
from copy import deepcopy
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
import warnings
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "release-tools"))
import fieldlog_provenance as producer


class ProducerTests(unittest.TestCase):
    def test_closed_inventory_rejects_extra_files_directories_links_and_missing_leaves(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            expected = producer.HTTPS_INPUT_FILES | {"project-template/Generated/locked"}
            for name in expected:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch()
            self.assertEqual(producer.https_input_files(root), sorted(expected))
            extra = root / "unapproved"
            for create, remove in ((extra.touch, extra.unlink), (extra.mkdir, extra.rmdir),
                                   (lambda: extra.symlink_to(root / "roots.json"), extra.unlink)):
                create()
                with self.assertRaises(ValueError):
                    producer.https_input_files(root)
                remove()
            (root / producer.HTTPS_ROOTS).unlink()
            with self.assertRaises(ValueError):
                producer.https_input_files(root)

    def test_independent_approvals_bind_apk_roles_probe_and_roots(self):
        approved = dict(installed="a" * 64, proposed="b" * 64, probe="c" * 64, roots="d" * 64)
        files = {name: approved[role] for role, name in producer.HTTPS_APKS.items()} | {producer.HTTPS_ROOTS: approved["roots"]}
        tools = {"probe": {"sha256": approved["probe"]}}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            seal = root / producer.HTTPS_SEAL
            seal.parent.mkdir()
            seal.write_text("".join(f"{digest}  {name.removeprefix('handoff/')}\n" for name, digest in files.items()))
            approved["handoff"] = files[producer.HTTPS_SEAL] = producer.file_hash(seal)
            producer.check_https_approvals(root, files, tools, approved)
            for field in approved:
                with self.subTest(field=field), self.assertRaises(ValueError):
                    producer.check_https_approvals(root, files, tools, approved | {field: "0" * 64})
            with self.assertRaisesRegex(ValueError, "full independent file seal"):
                producer.check_https_approvals(root, files | {"handoff/extra": "0" * 64}, tools, approved)

    def test_duplicate_zip_and_json_entries_are_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            apk = Path(directory) / "duplicate.apk"
            with zipfile.ZipFile(apk, "w") as archive, warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                archive.writestr("classes.dex", b"")
                archive.writestr("classes.dex", b"")
            with self.assertRaisesRegex(ValueError, "Ambiguous .* APK member"):
                producer.apk_contents(apk)
        with self.assertRaisesRegex(ValueError, "Duplicate JSON field"):
            producer.strict_json(b'{"schema":1,"schema":2}')

    def test_https_origins_require_canonical_tls_authority(self):
        for origin in ("https://a.example", "https://a.example:8443"):
            self.assertTrue(producer.https_origin(origin), origin)
        for origin in ("http://a.example", "https://a.example:443", "https://a.example:65536",
                       "https://a.example/path", "https://user@a.example", "https://a..example",
                       "https://A.example", "https://a.example:08443", "https://-a.example"):
            self.assertFalse(producer.https_origin(origin), origin)


def run_native_control(args):
    handoff = args.native_control.resolve(strict=True)
    permissions = (handoff / "old/permissions.json").read_bytes()
    application = producer.ANDROID_APP | {"bundle_id": producer.ANDROID_PACKAGE + ".calculation"}
    seals = dict(line.split("  ", 1)[::-1] for line in (handoff / "SHA256SUMS").read_text().splitlines())
    paths = {role: handoff / f"{variant}/FieldLog.apk"
             for role, variant in (("installed", "old"), ("proposed", "successor"))}
    work = Path(tempfile.mkdtemp(prefix="mixer-fieldlog-https-native-control.")).resolve()
    build = producer.HTTPSBuild.__new__(producer.HTTPSBuild)
    producer.LocalCommands.__init__(build, work, {"JAVA_HOME": str(args.java_home.resolve(strict=True)),
                                                   "PATH": "/usr/bin:/bin", "TMPDIR": str(work / "tmp"),
                                                   "HOME": str(work), "LC_ALL": "C"})
    build.tools = {name: args.build_tools.resolve(strict=True) / name for name in ("aapt2", "apksigner", "zipalign")}
    build.approvals = {role: seals[apk.relative_to(handoff).as_posix()] for role, apk in paths.items()}
    tests = unittest.TestCase()
    try:
        contents, signers = {}, {}
        for role, apk in paths.items():
            tests.assertEqual(producer.file_hash(apk), build.approvals[role])
            signers[role] = build.signer(apk)
            tests.assertEqual(build.android_contract(apk, application["bundle_id"]), producer.strict_json(permissions))
            contents[role] = producer.apk_contents(apk)
            material, _ = contents[role]
            tests.assertEqual(producer.strict_json(material["identity.json"])["build"]["permissions_sha256"],
                              producer.sha(permissions))
            if role == "installed":
                with tests.assertRaisesRegex(ValueError, "different installed package"):
                    build.android_contract(apk)
            target = work / role
            target.mkdir()
            pin = build.package_evidence(target, role, apk, material, permissions)
            tests.assertEqual(pin["archiveSHA256"], build.approvals[role])
            tests.assertEqual(pin["identitySHA256"], producer.sha(material["identity.json"]))
            tests.assertEqual((target / f"{role}.permissions.json").read_bytes(), permissions)
        old, new = contents["installed"], contents["proposed"]
        tests.assertEqual(signers["installed"], signers["proposed"])
        changes = producer.check_https_delta(old, new, application=application)
        tests.assertEqual(changes, ["classes.dex", "lib/arm64-v8a/libmixer_public_android_jni.so"])
        with tests.assertRaisesRegex(ValueError, "FieldLog Android development identity"):
            producer.check_https_delta(old, new)
        with tests.assertRaisesRegex(ValueError, "byte-identical manifest"):
            producer.check_https_delta(old, (new[0], new[1] | {"AndroidManifest.xml": "0" * 64}),
                                       application=application)
        with tests.assertRaisesRegex(ValueError, "genuine compiled"):
            producer.check_https_delta(old, (new[0], old[1]), application=application)
        with tests.assertRaisesRegex(ValueError, "differs from its versioned descriptor"):
            producer.check_https_delta(old, (new[0] | {"http-grant.json": b"{}"}, new[1]), application=application)
        with tests.assertRaisesRegex(ValueError, "roots or bridge"):
            producer.check_https_delta(old, (new[0] | {"roots.json": b"[]"}, new[1]), application=application)
        bad = deepcopy(new[0])
        identity = producer.strict_json(bad["identity.json"])
        grant = producer.strict_json(bad["http-grant.json"])
        grant["origins"] = ["http://a.example"]
        bad["http-grant.json"] = producer.encoded(grant)
        identity["capabilities"][0]["grants_sha256"] = producer.sha(bad["http-grant.json"])
        bad["identity.json"] = producer.encoded(identity)
        with tests.assertRaisesRegex(ValueError, "HTTPS-only grant"):
            producer.check_https_delta(old, (bad, new[1]), application=application)
        aliases = producer.stock_material(new[0])
        tests.assertEqual(aliases["configuration.network.http.v1.json"], new[0]["http.json"])
        tests.assertEqual(aliases["grant.network.http.v1.json"], new[0]["http-grant.json"])
        for role, material in (("old", old[0]), ("successor", new[0])):
            expected = producer.load(handoff / role / "manifest.json")["manifest"]
            bindings = producer.https_manifest_capabilities(producer.strict_json(material["identity.json"]), material)
            tests.assertEqual(bindings, {field: expected[field] for field in bindings})
        print(json.dumps({"archives": build.approvals, "signerSHA256": signers["installed"],
                          "compiledManifestSHA256": old[1]["AndroidManifest.xml"], "changedCompiledMembers": changes,
                          "scope": "calculation APK material control only", "commands": build.commands}, sort_keys=True))
    finally:
        if build.custody_resolved:
            shutil.rmtree(work)
        else:
            print(f"Preserve unresolved native control: {work}", file=sys.stderr)


def run_key_control(args):
    work = Path(tempfile.mkdtemp(prefix="mixer-fieldlog-https-key-control.")).resolve()
    build = producer.HTTPSBuild.__new__(producer.HTTPSBuild)
    run = work / "run"
    run.mkdir()
    producer.LocalCommands.__init__(build, run, {"PATH": "/usr/bin:/bin", "TMPDIR": str(run / "tmp"),
                                                 "HOME": str(work), "LC_ALL": "C"})
    build.tools = {"openssl": args.openssl.resolve(strict=True)}
    build.inputs = work / "input"
    build.inputs.mkdir()
    tests = unittest.TestCase()
    try:
        key = work / "control.key"
        public = build.key(key)
        roots = build.inputs / producer.HTTPS_ROOTS
        roots.parent.mkdir(parents=True)
        producer.save(roots, [{"artifact": True, "assignment": True, "key_id": producer.ANDROID_OTA_KEY_ID,
                               "public_key": public, "scope": producer.ANDROID_SCOPE, "not_before_unix": 1,
                               "not_after_unix": 0, "revoked": False}])
        build.approvals = {"roots": producer.file_hash(roots)}
        message = work / "message"
        message.write_bytes(b"FieldLog Ed25519 key binding control")
        public_der = work / "public.der"
        public_der.write_bytes(bytes.fromhex("302a300506032b6570032100") + base64.b64decode(public))
        signature = work / "signature"
        with build.ota_key(key) as signer:
            first = build.sign(signer, message.read_bytes())
            tests.assertEqual(first, build.sign(signer, message.read_bytes()))
            signature.write_bytes(first)
        build.run(build.tools["openssl"], "pkeyutl", "-verify", "-pubin", "-keyform", "DER", "-inkey", public_der,
                  "-rawin", "-in", message, "-sigfile", signature)
        other = work / "other.key"
        build.key(other)
        with tests.assertRaisesRegex(ValueError, "does not derive"):
            with build.ota_key(other):
                tests.fail("Wrong key was accepted")
        print("Ed25519 approved-root derivation, signature verification and wrong-key rejection passed")
    finally:
        if build.custody_resolved:
            shutil.rmtree(work)
        else:
            print(f"Preserve unresolved key control: {work}", file=sys.stderr)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-control", type=Path)
    parser.add_argument("--build-tools", type=Path)
    parser.add_argument("--java-home", type=Path)
    parser.add_argument("--openssl", type=Path)
    args = parser.parse_args()
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ProducerTests))
    if not result.wasSuccessful():
        sys.exit(1)
    if args.native_control:
        if args.build_tools is None or args.java_home is None:
            parser.error("--native-control requires --build-tools and --java-home")
        run_native_control(args)
    if args.openssl:
        run_key_control(args)
