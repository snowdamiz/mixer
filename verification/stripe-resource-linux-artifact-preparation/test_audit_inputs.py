"""Adversarial host controls; only newly owned temporary files are mutated."""
import copy
from pathlib import Path
import tempfile
import unittest

import audit_inputs as candidate


class HostControls(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory(prefix="mixer-linux-artifact-input-control-")
        self.addCleanup(self.scratch.cleanup)
        self.root = Path(self.scratch.name).resolve()
        for name in ("ordinary", "PLAN.md"):
            (self.root / name).write_text(name)

    def test_known_input_matches(self):
        self.assertEqual(candidate.checked_files(self.root, {"ordinary": candidate.sha(self.root / "ordinary")}), 1)

    def test_changed_input_refuses(self):
        expected = candidate.sha(self.root / "ordinary")
        (self.root / "ordinary").write_text("changed")
        with self.assertRaises(ValueError):
            candidate.checked_files(self.root, {"ordinary": expected})

    def test_missing_input_refuses(self):
        with self.assertRaises(ValueError):
            candidate.checked_files(self.root, {"absent": "0" * 64})

    def test_final_symlink_refuses(self):
        (self.root / "link").symlink_to("ordinary")
        with self.assertRaises(ValueError):
            candidate.checked_files(self.root, {"link": candidate.sha(self.root / "ordinary")})

    def test_parent_escape_refuses(self):
        with self.assertRaises(ValueError):
            candidate.checked_files(self.root, {"../ordinary": "0" * 64})

    def test_absolute_path_refuses(self):
        with self.assertRaises(ValueError):
            candidate.checked_files(self.root, {str(self.root / "ordinary"): "0" * 64})

    def test_empty_component_refuses(self):
        with self.assertRaises(ValueError):
            candidate.checked_files(self.root, {"one//ordinary": "0" * 64})

    def test_mutable_plan_is_explicit_and_historical(self):
        self.assertEqual(candidate.checked_files(self.root, {"PLAN.md": "0" * 64}, ("PLAN.md",)), 0)
        with self.assertRaises(ValueError):
            candidate.checked_files(self.root, {"PLAN.md": "0" * 64})

    def test_changed_closure_refuses_before_reading_seals(self):
        with self.assertRaisesRegex(ValueError, "historical source closure"):
            candidate.audit(self.root, {"schema": 1, "runtimeAuthorized": False,
                "historicalMutablePath": "PLAN.md", "historicalSourceInputs": {},
                "sourceClosureDigest": "0" * 64})

    def test_runtime_authorization_refuses(self):
        with self.assertRaisesRegex(ValueError, "cannot authorize"):
            candidate.audit(self.root, {"schema": 1, "runtimeAuthorized": True})

    def test_wrong_mutable_path_refuses(self):
        with self.assertRaisesRegex(ValueError, "historical source closure"):
            candidate.audit(self.root, {"schema": 1, "runtimeAuthorized": False,
                "historicalMutablePath": "ordinary", "historicalSourceInputs": {},
                "sourceClosureDigest": candidate.digest({})})

    def test_platform_image_binds_digest_os_arch_and_media(self):
        image = {"Os": "linux", "Architecture": "arm64", "Descriptor": {"digest": "sha256:" + "a" * 64,
            "mediaType": "application/vnd.oci.image.manifest.v1+json"}}
        digest = image["Descriptor"]["digest"]
        media = image["Descriptor"]["mediaType"]
        candidate.checked_image(image, digest, media)
        for key, bad in (("Os", "darwin"), ("Architecture", "amd64")):
            changed = copy.deepcopy(image)
            changed[key] = bad
            with self.assertRaises(ValueError):
                candidate.checked_image(changed, digest, media)
        for key, bad in (("digest", "sha256:" + "b" * 64), ("mediaType", "application/vnd.oci.image.index.v1+json")):
            changed = copy.deepcopy(image)
            changed["Descriptor"][key] = bad
            with self.assertRaises(ValueError):
                candidate.checked_image(changed, digest, media)


if __name__ == "__main__":
    unittest.main(verbosity=2)
