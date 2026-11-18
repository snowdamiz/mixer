#!/usr/bin/env python3
"""Exercise the public inspector against a private FieldLog provenance run."""
import argparse
import base64
from contextlib import ExitStack, contextmanager
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import mkdtemp

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "release-tools"))
from fieldlog_provenance import LocalCommands


@contextmanager
def replaced(path, payload, commands):
    original = path.read_bytes()
    try:
        path.write_bytes(payload)
        yield
    finally:
        if commands.custody_resolved:
            path.write_bytes(original)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mixer", type=Path)
    parser.add_argument("run", type=Path)
    parser.add_argument("--producer-trust", type=Path, required=True)
    parser.add_argument("--openssl", type=Path, required=True, help="The pinned OpenSSL from the producer inventory")
    if not __debug__:
        parser.error("Run without Python optimization to enable assertions")
    args = parser.parse_args()
    os.umask(0o077)
    run = args.run.resolve()
    scratch = Path(mkdtemp(prefix="inspection-controls-", dir=run / "tmp"))
    commands = LocalCommands(scratch, os.environ | {"TMPDIR": str(scratch / "tmp")})
    try:
        check(args, run, commands)
    finally:
        if commands.custody_resolved:
            shutil.rmtree(scratch)


def check(args, run, commands):
    trust = args.producer_trust.resolve()
    compatible = commands.work / "compatible"
    shutil.copytree(run / "compatible", compatible)
    permission = run / "permission-change"
    project = run / "review-source"

    def inspect(case, root, qualification, anchor, status, code, reason=None):
        command = [args.mixer.resolve(), "release", "inspect", "--directory", root]
        if qualification:
            command += ["--qualification", qualification, "--producer-trust", anchor]
        try:
            outcome = json.loads(commands.run(*command, expected=status, timeout=20, mixer_cli=True))
        except subprocess.CalledProcessError as failure:
            raise AssertionError((case, failure.returncode, failure.stdout, failure.stderr)) from failure
        actual = outcome.get("technicalEligibility", outcome.get("code"))
        assert actual == code, (case, outcome)
        if "technicalEligibility" in outcome:
            assert outcome["publicationAllowed"] is False, (case, outcome)
        if reason:
            assert any(reason in blocker for blocker in outcome["blockers"]), (case, outcome)
        print(json.dumps({"case": case, "exit": status, "report": outcome}, sort_keys=True))
        return outcome

    inspect("normal inspection fails closed", project, None, None, 2, "blocked")
    valid = inspect("trusted same-project compiled edit", project, compatible, trust, 0, "ota-compatible")
    assert [(target["platform"], target["status"]) for target in valid["targets"]] == [
        ("ios", "ota-compatible"), ("android", "ota-compatible")]
    binary = inspect("real Android permission", run / "permission-source", permission, trust, 2,
                     "ota-compatible-one-platform", "Effective native permissions changed")
    assert [(target["platform"], target["status"]) for target in binary["targets"]] == [
        ("ios", "ota-compatible"), ("android", "store-build-required")]
    inspect("candidate source mismatch", run / "baseline-source", compatible, trust, 1, "release.project-binding")
    fake = json.loads(trust.read_bytes())
    fake["publicKey"] = base64.b64encode(bytes(range(32))).decode()
    with commands.temporary() as temporary:
        false_trust = temporary / "trust.json"
        false_trust.write_text(json.dumps(fake))
        inspect("untrusted signer", project, compatible, false_trust, 1, "release.producer-signature")
    with commands.temporary(compatible / "android") as temporary:
        bundled_trust = temporary / "trust.json"
        bundled_trust.write_bytes(trust.read_bytes())
        inspect("bundled trust refused", project, compatible, bundled_trust, 1, "release.producer-trust")
    index = compatible / "qualification.json"
    with replaced(index, index.read_bytes() + b" ", commands):
        inspect("changed signed index", project, compatible, trust, 1, "release.producer-signature")
    with replaced(compatible / "android/behavior.json", b'{"passed":true}', commands):
        inspect("handwritten behavior", project, compatible, trust, 2, "ota-compatible-one-platform", "release.behavior")
    with replaced(compatible / "android/installed.permissions.json", b"{}", commands):
        inspect("substituted native permissions", project, compatible, trust, 2,
                "ota-compatible-one-platform", "release.native-build")
    with replaced(compatible / "android/installed.native", b"other local archive", commands):
        inspect("substituted packaged Android archive", project, compatible, trust, 2,
                "ota-compatible-one-platform", "release.native-build")
    with replaced(compatible / "android/candidate.wasm", b"\x00asm", commands):
        inspect("substituted guest bytes", project, compatible, trust, 2, "ota-compatible-one-platform", "v3.payload")
    # Re-sign each substituted receipt as a trusted local fixture producer.
    # The inspector must reject the target/offer binding even after the index
    # signature and receipt digest have been made internally consistent.
    with commands.temporary() as scratch:
        inventory = json.loads((compatible / "toolchain.json").read_bytes())
        if "toolSHA256" in inventory:
            openssl_sha256 = inventory["toolSHA256"]["openssl"]
        else:
            openssl_sha256 = inventory["tools"]["openssl"]["sha256"]
        openssl = args.openssl.resolve()
        with openssl.open("rb") as executable:
            assert hashlib.file_digest(executable, "sha256").hexdigest() == openssl_sha256
        key = scratch / "fixture.key"
        commands.run(openssl, "genpkey", "-algorithm", "ED25519", "-out", key, timeout=10)
        public = commands.run(openssl, "pkey", "-in", key, "-pubout", "-outform", "DER", timeout=10)
        test_anchor = scratch / "trust.json"
        local_trust = json.loads(trust.read_bytes())
        local_trust["publicKey"] = base64.b64encode(public[-32:]).decode()
        test_anchor.write_text(json.dumps(local_trust))

        def signed_case(case, target, replacements, status, eligibility, problem=None):
            changed = json.loads(index.read_bytes())
            receipt = compatible / target / "behavior.json"
            changed["targets"][target]["behaviorReceiptSHA256"] = hashlib.sha256(
                replacements.get(receipt, receipt.read_bytes())).hexdigest()
            index_bytes = json.dumps(changed, sort_keys=True).encode()
            message = scratch / "message"
            message.write_bytes(b"mixer.local.build-provenance.v1\0" + index_bytes)
            signature = commands.run(openssl, "pkeyutl", "-sign", "-rawin", "-inkey", key, "-in", message, timeout=10)
            with ExitStack() as stack:
                stack.enter_context(replaced(index, index_bytes, commands))
                stack.enter_context(replaced(compatible / "qualification.ed25519", signature, commands))
                for path, substitute in replacements.items():
                    stack.enter_context(replaced(path, substitute, commands))
                report = inspect(case, project, compatible, test_anchor, status, eligibility, problem)
            if problem:
                results = {result["platform"]: result for result in report["targets"]}
                assert results[target]["status"] == "blocked" and problem in results[target]["reason"]
                assert all(result["status"] == "ota-compatible" for p, result in results.items() if p != target)

        signed_case("trusted test signer control", "ios", {}, 0, "ota-compatible")
        for target, other in (("ios", "android"), ("android", "ios")):
            receipt = compatible / target / "behavior.json"
            wrong = (compatible / other / "behavior.json").read_bytes()
            signed_case(f"trusted {other} receipt for {target}", target, {receipt: wrong}, 2,
                        "ota-compatible-one-platform", "release.behavior")
        ios = compatible / "ios"
        wrong = (permission / "ios/behavior.json").read_bytes()
        signed_case("trusted iOS receipt for different assignment with the same Wasm", "ios",
                    {ios / "behavior.json": wrong}, 2, "ota-compatible-one-platform", "release.behavior")
        foreign_trace = (permission / "ios/candidate.host-observation.json").read_bytes()
        behavior = json.loads((ios / "behavior.json").read_bytes())
        behavior["candidate"]["hostObservationSHA256"] = hashlib.sha256(foreign_trace).hexdigest()
        signed_case("trusted iOS host trace for different signed offer", "ios",
                    {ios / "behavior.json": json.dumps(behavior).encode(), ios / "candidate.host-observation.json": foreign_trace},
                    2, "ota-compatible-one-platform", "release.behavior")

    old = commands.run(args.mixer.resolve(), "release", "inspect", "--directory", project, "--qualification", compatible,
                       "--qualification-sha256", "0" * 64, expected=1, timeout=20, mixer_cli=True)
    assert json.loads(old)["code"] == "arguments.option"
    print(json.dumps({"case": "caller supplied digest cannot authorize inspection", "exit": 1}))


if __name__ == "__main__":
    main()
