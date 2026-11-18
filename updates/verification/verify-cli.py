#!/usr/bin/env python3
"""Check the built mixer-update commands against the shared release vectors."""

import base64
import json
from pathlib import Path
import subprocess
import sys
import tempfile


FIXTURES = Path(__file__).resolve().parents[1] / "Tests/MixerUpdatesTests/Fixtures"


def check_vectors(executable, scratch):
    for version in (1, 2, 3):
        vector = json.loads((FIXTURES / f"signed-release-v{version}.json").read_text())
        payload = base64.b64decode(vector["payload"], validate=True)
        manifest = vector["signed_manifest"]["manifest"]
        assignment = vector["signed_assignment"]["assignment"]
        directory = scratch / f"v{version}"
        directory.mkdir()
        options = {
            "channel": assignment["channel"],
            "installation": vector["installation"],
            "last-sequence": str(vector["last_sequence"]),
            "now": str(vector["verification_time_unix"]),
        }
        for option, key in (
            ("manifest", "signed_manifest"),
            ("assignment", "signed_assignment"),
            ("host", "host"),
            ("roots", "roots"),
        ):
            path = directory / f"{option}.json"
            path.write_text(json.dumps(vector[key]), encoding="utf-8")
            options[option] = str(path)
        path = directory / "payload"
        path.write_bytes(payload)
        options["payload"] = str(path)

        command = "verify-v3" if version == 3 else "verify"

        def run(case, command=command, exit_code=1, code=None, omit_option=None, **overrides):
            argv = [str(executable)]
            if command is not None:
                argv.append(command)
            for option, value in (options | overrides).items():
                if option != omit_option:
                    argv.extend((f"--{option}", value))
            result = subprocess.run(argv, capture_output=True, text=True, check=False, timeout=10)
            if result.returncode != exit_code or result.stderr:
                raise AssertionError(f"{case}: {result}")
            report = json.loads(result.stdout)
            if exit_code:
                if report.get("status") != "error" or not report.get("message"):
                    raise AssertionError(f"{case}: expected an error with a message, got {report}")
                if code is None and "code" in report:
                    raise AssertionError(f"{case}: expected no code field, got {report}")
                if code is not None and report.get("code") != code:
                    raise AssertionError(f"{case}: expected code {code}, got {report}")
            print(json.dumps({"case": case, "exit": result.returncode, "report": report}))
            return report

        report = run(f"v{version} shared signed release", exit_code=0)
        expected = {
            "status": "protocol-verified",
            "artifactSHA256": vector["artifact_sha256"],
            "releaseID": manifest["release_id"],
            "payloadBytes": len(payload),
            "assignmentSequence": assignment["sequence"],
            "cohortBucket": vector["cohort_bucket"],
            "executableProfileVerified": False,
            "policyApproved": False,
            "activated": False,
        }
        if report != expected:
            raise AssertionError(f"v{version}: expected {expected}, got {report}")

        if version < 3:
            run(f"v{version} legacy replay", **{"last-sequence": str(assignment["sequence"])})
            run(f"v{version} installed host on explicit v3 route", command="verify-v3", code="v3.host.invalid")
            continue

        run("v3 options without a command", command=None)
        for option in options:
            run(f"v3 missing --{option}", code="arguments", omit_option=option)
        run("v3 installed host on legacy route", command="verify")
        run("v3 replay", code="v3.assignment.replay", **{"last-sequence": str(assignment["sequence"])})
        run("v3 wrong channel", code="v3.assignment.binding", channel="stable")
        changed = directory / "changed-payload"
        changed.write_bytes(bytes([payload[0] ^ 1]) + payload[1:])
        run("v3 changed payload", code="v3.payload.integrity", payload=str(changed))
        oversized = directory / "oversized-payload"
        with oversized.open("wb") as file:
            file.truncate(4_194_305)
        run("v3 payload over 4 MiB", code="file.size", payload=str(oversized))
        smaller_host = directory / "smaller-host.json"
        smaller_host.write_text(json.dumps(vector["host"] | {"max_payload_bytes": len(payload) - 1}), encoding="utf-8")
        run("v3 payload over a smaller installed limit", code="file.size", host=str(smaller_host))
        wider_host = directory / "wider-host.json"
        wider_host.write_text(json.dumps(vector["host"] | {"max_payload_bytes": 16_777_216}), encoding="utf-8")
        run("v3 host with legacy payload limit", code="v3.host.invalid", host=str(wider_host))
        abi3_host = directory / "abi3-host.json"
        abi3_host.write_text(json.dumps(vector["host"] | {"guest_abi": 3}), encoding="utf-8")
        run("v3 host with guest ABI 3", code="v3.host.invalid", host=str(abi3_host))
        foreign_host = directory / "foreign-host.json"
        foreign_scope = vector["host"]["scope"] | {"app": "different-app"}
        foreign_host.write_text(json.dumps(vector["host"] | {"scope": foreign_scope}), encoding="utf-8")
        run("v3 manifest for a different app", code="v3.manifest.compatibility", host=str(foreign_host))
        for option in ("manifest", "assignment"):
            envelope = vector[f"signed_{option}"]
            path = directory / f"missing-{option}-signature.json"
            path.write_text(json.dumps({option: envelope[option]}), encoding="utf-8")
            run(f"v3 missing {option} signature", code="v3.document.fields", **{option: str(path)})
            signature = base64.b64decode(envelope["signature"], validate=True)
            changed_signature = base64.b64encode(bytes([signature[0] ^ 1]) + signature[1:]).decode("ascii")
            path = directory / f"changed-{option}-signature.json"
            path.write_text(json.dumps(envelope | {"signature": changed_signature}), encoding="utf-8")
            run(f"v3 changed {option} signature", code="v3.signature.invalid", **{option: str(path)})
        oversized_document = directory / "oversized-document.json"
        oversized_document.write_bytes(b" " * 65_537)
        for option in ("manifest", "assignment"):
            run(f"v3 {option} over 64 KiB", code="file.size", **{option: str(oversized_document)})


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("Usage: python3 updates/verification/verify-cli.py MIXER_UPDATE OWNED_SCRATCH")
    with tempfile.TemporaryDirectory(prefix="update-cli-vectors-", dir=sys.argv[2]) as scratch:
        check_vectors(Path(sys.argv[1]).resolve(strict=True), Path(scratch))
