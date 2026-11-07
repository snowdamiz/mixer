#!/usr/bin/env python3
"""Verify source identity and scope only; never execute Elixir or network work."""
import sys


def deny(event, args):
    if event.startswith("socket.") or event in {
        "subprocess.Popen", "os.system", "os.posix_spawn", "os.exec", "os.fork",
        "os.forkpty", "pty.spawn",
    }:
        raise RuntimeError("source-only audit denied " + event)


sys.addaudithook(deny)
import hashlib
import json
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RAW = ROOT / "verification/github-delivery-positive-timestamp/ci-review/network"
FIXTURE = "hosted/test/support/identity_tls_fixture.ex"
STARTUP = "hosted/test/mixer_hosted/identity/startup_linux_network_test.exs"
K03 = "hosted/test/mixer_hosted/identity/key_owner_linux_network_test.exs"
CONTROL = "hosted/test/mixer_hosted/identity/tls_fixture_lifecycle_control_test.exs"
OLD_DIGEST = "023df04c9a4599c3d5a6cdf2afb53a95e2faf37765d8b96ba2bcc0e1b007c92e"
NEW_DIGEST = "ab8f8dbec5894ca96dd673db828a01afdc39a54ad008a2a2d4e598c1c62ce2f7"


def sha(body):
    return hashlib.sha256(body).hexdigest()


def canonical_sha(value):
    return sha(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


class SourceScopeControls(unittest.TestCase):
    def test_exact_178_source_delta_is_fixture_plus_executable_control(self):
        old = json.loads((RAW / "product-source-manifest.json").read_bytes())
        new = json.loads((HERE / "candidate-product-source-manifest.json").read_bytes())
        self.assertEqual(canonical_sha(old), OLD_DIGEST)
        self.assertEqual(canonical_sha(new), NEW_DIGEST)
        self.assertEqual(len(old), 177)
        self.assertEqual(len(new), 178)
        self.assertEqual(set(old) | {CONTROL}, set(new))
        self.assertEqual([p for p in old if old[p] != new[p]], [FIXTURE])
        self.assertEqual(old[STARTUP], new[STARTUP])
        self.assertEqual(old[K03], new[K03])
        self.assertEqual(old["hosted/mix.lock"], new["hosted/mix.lock"])

    def test_candidate_bytes_and_patch_target_match(self):
        new = json.loads((HERE / "candidate-product-source-manifest.json").read_bytes())
        body = (HERE / "candidate" / FIXTURE).read_bytes()
        self.assertEqual(new[FIXTURE], {"bytes": len(body), "sha256": sha(body)})
        patch = (HERE / "fixture-candidate.patch").read_text()
        self.assertEqual([line for line in patch.splitlines() if line.startswith("--- ")],
                         ["--- a/" + FIXTURE])
        self.assertEqual([line for line in patch.splitlines() if line.startswith("+++ ")],
                         ["+++ b/" + FIXTURE])
        control = (HERE / "candidate" / CONTROL).read_bytes()
        self.assertEqual(new[CONTROL], {"bytes": len(control), "sha256": sha(control)})
        self.assertEqual(control, (HERE / "tls_fixture_lifecycle_control_test.exs").read_bytes())
        integrated = (HERE / "integration-candidate.patch").read_text()
        self.assertEqual([line for line in integrated.splitlines() if line.startswith("+++ ")],
                         ["+++ b/" + FIXTURE, "+++ b/" + CONTROL])

    def test_canonical_fixture_and_startup_remain_unmodified(self):
        old = json.loads((RAW / "product-source-manifest.json").read_bytes())
        for path in [FIXTURE, STARTUP, K03]:
            self.assertEqual(sha((ROOT / path).read_bytes()), old[path]["sha256"])

    def test_protected_dirty_sources_remain_exact(self):
        expected = {
            "hosted/lib/mixer_hosted/browser_auth/store.ex":
                "8c314b1d3ce288a6dc617251233796bd0a9d8894247ccb15b101e1292e513299",
            ".github/workflows/hosted.yml":
                "fafd2560cc385a4113ea140bf2d4445d456e1f7f396539dfe2c3e7d6302e8b57",
        }
        for path, digest in expected.items():
            self.assertEqual(sha((ROOT / path).read_bytes()), digest)

    def test_failure_log_is_exact_and_retains_failed_original_assertion(self):
        receipt = json.loads((HERE / "source-inspection.json").read_bytes())
        body = (ROOT / receipt["failure_log"]["path"]).read_bytes()
        self.assertEqual(sha(body), receipt["failure_log"]["sha256"])
        self.assertIn(b"startup_linux_network_test.exs:97", body)
        self.assertIn(b"Result: 1/2 passed", body)
        self.assertEqual(receipt["runtime_tests"],
                         "not run; remote CI selection and independent review required")

    def test_child_and_socket_audit_events_are_denied_without_attempting_them(self):
        for event in ["socket.__new__", "socket.connect", "subprocess.Popen", "os.posix_spawn"]:
            with self.assertRaisesRegex(RuntimeError, "source-only audit denied"):
                sys.audit(event, None)


if __name__ == "__main__":
    unittest.main(verbosity=2)
