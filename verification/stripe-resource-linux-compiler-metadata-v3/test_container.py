"""Finite host policy controls; no Docker/native/tool execution."""
import copy
from pathlib import Path
import unittest

import run_container as candidate


class PolicyControls(unittest.TestCase):
    def setUp(self):
        self.name = "mixer-private-tool-payload-test"
        self.token = "owned-test-token"
        self.identifier = "a" * 64
        self.snapshot = Path("/tmp/mixer-input-policy-fixture")
        self.info = {"Id": self.identifier, "Name": "/" + self.name, "Image": candidate.IMAGE.split("@")[1], "Platform": "linux",
            "ImageManifestDescriptor": {"digest": candidate.CHILD,
                "mediaType": "application/vnd.oci.image.manifest.v1+json",
                "platform": {"architecture": "arm64", "os": "linux"}},
            "Config": {"Image": candidate.IMAGE, "User": "65534:65534",
                "Labels": {candidate.LABEL: self.token}, "Entrypoint": ["/bin/sh"],
                "Cmd": ["-c", "exec sleep 120"]},
            "HostConfig": {"NetworkMode": "none", "ReadonlyRootfs": True, "CapDrop": ["ALL"],
                "SecurityOpt": ["no-new-privileges"], "PidsLimit": 128, "Memory": 1073741824,
                "NanoCpus": 2000000000, "Privileged": False, "CapAdd": None, "Devices": None,
                "VolumesFrom": None, "Binds": None, "PidMode": "",
                "Ulimits": [{"Name": "core", "Hard": 0, "Soft": 0}],
                "Tmpfs": {"/tmp": "rw,noexec,nosuid,nodev,size=134217728,mode=1777"}},
            "Mounts": [{"Type": "bind", "Source": str(self.snapshot), "Destination": "/inputs", "RW": False}]}

    def check(self, info):
        candidate.checked_policy(info, self.name, self.token, self.snapshot, self.identifier)

    def test_selected_policy_accepts(self):
        self.check(self.info)

    def test_identity_and_cleanup_fence_rejects_other_container(self):
        for key, bad in (("Id", "b" * 64), ("Name", "/another-project")):
            changed = copy.deepcopy(self.info)
            changed[key] = bad
            self.assertFalse(candidate.owned(changed, self.name, self.token, self.identifier))
            with self.assertRaises(ValueError):
                self.check(changed)
        changed = copy.deepcopy(self.info)
        changed["Config"]["Labels"][candidate.LABEL] = "another-owner"
        self.assertFalse(candidate.owned(changed, self.name, self.token, self.identifier))

    def test_mutable_or_other_image_refuses(self):
        changed = copy.deepcopy(self.info)
        changed["Config"]["Image"] = "hexpm/elixir:latest"
        with self.assertRaises(ValueError):
            self.check(changed)

    def test_privilege_network_user_changes_refuse(self):
        for key, value in (("Privileged", True), ("NetworkMode", "host"), ("ReadonlyRootfs", False),
                ("CapAdd", ["NET_ADMIN"]), ("CapDrop", []), ("SecurityOpt", []), ("PidMode", "host")):
            changed = copy.deepcopy(self.info)
            changed["HostConfig"][key] = value
            with self.assertRaises(ValueError):
                self.check(changed)
        changed = copy.deepcopy(self.info)
        changed["Config"]["User"] = "0:0"
        with self.assertRaises(ValueError):
            self.check(changed)

    def test_resource_limit_changes_refuse(self):
        for key, value in (("PidsLimit", 256), ("Memory", 2147483648), ("NanoCpus", 4000000000),
                ("Ulimits", [{"Name": "core", "Hard": -1, "Soft": -1}]), ("Tmpfs", {"/tmp": "rw"})):
            changed = copy.deepcopy(self.info)
            changed["HostConfig"][key] = value
            with self.assertRaises(ValueError):
                self.check(changed)

    def test_writable_or_extra_or_other_source_mount_refuses(self):
        for key, value in (("RW", True), ("Source", "/Users/example/project"), ("Destination", "/workspace")):
            changed = copy.deepcopy(self.info)
            changed["Mounts"][0][key] = value
            with self.assertRaises(ValueError):
                self.check(changed)
        changed = copy.deepcopy(self.info)
        changed["Mounts"].append({"Type": "bind", "Source": "/var/run/docker.sock", "Destination": "/socket", "RW": True})
        with self.assertRaises(ValueError):
            self.check(changed)

    def test_alternate_entrypoint_refuses(self):
        changed = copy.deepcopy(self.info)
        changed["Config"]["Cmd"] = ["-c", "an-unselected-command"]
        with self.assertRaises(ValueError):
            self.check(changed)

    def test_parent_address_and_exact_child_image_accept(self):
        candidate.checked_image({"RepoDigests": [candidate.IMAGE], "Id": candidate.CHILD,
            "Descriptor": {"digest": candidate.CHILD, "mediaType": "application/vnd.oci.image.manifest.v1+json",
                "platform": {"architecture": "arm64", "os": "linux"}}, "Os": "linux", "Architecture": "arm64"})

    def test_changed_missing_or_wrong_platform_image_refuses(self):
        image = {"RepoDigests": [candidate.IMAGE], "Id": candidate.CHILD,
            "Descriptor": {"digest": candidate.CHILD, "mediaType": "application/vnd.oci.image.manifest.v1+json",
                "platform": {"architecture": "arm64", "os": "linux"}}, "Os": "linux", "Architecture": "arm64"}
        for key, value in (("RepoDigests", []), ("RepoDigests", ["hexpm/elixir:latest"]),
                ("Id", "sha256:" + "a" * 64), ("Descriptor", {}), ("Architecture", "amd64"), ("Os", "darwin")):
            changed = copy.deepcopy(image)
            changed[key] = value
            with self.assertRaises(ValueError):
                candidate.checked_image(changed)
        changed = copy.deepcopy(image)
        changed["Descriptor"]["digest"] = "sha256:" + "b" * 64
        with self.assertRaises(ValueError):
            candidate.checked_image(changed)
        with self.assertRaises(ValueError):
            candidate.checked_image({})

    def test_container_child_mismatch_refuses_before_start(self):
        changed = copy.deepcopy(self.info)
        changed["ImageManifestDescriptor"]["digest"] = "sha256:" + "b" * 64
        with self.assertRaisesRegex(ValueError, "platform image"):
            self.check(changed)

    def test_container_missing_parent_child_or_platform_refuses(self):
        for key in ("Image", "ImageManifestDescriptor", "Platform"):
            changed = copy.deepcopy(self.info)
            del changed[key]
            with self.assertRaises(ValueError):
                self.check(changed)
        changed = copy.deepcopy(self.info)
        del changed["Config"]["Image"]
        with self.assertRaises(ValueError):
            self.check(changed)

    def test_container_wrong_parent_or_child_platform_refuses(self):
        for key, value in (("Image", candidate.CHILD), ("Platform", "darwin")):
            changed = copy.deepcopy(self.info)
            changed[key] = value
            with self.assertRaises(ValueError):
                self.check(changed)
        for field, value in (("platform", {"architecture": "amd64", "os": "linux"}),
                ("mediaType", "application/vnd.oci.image.index.v1+json"), ("digest", "sha256:" + "c" * 64)):
            changed = copy.deepcopy(self.info)
            changed["ImageManifestDescriptor"][field] = value
            with self.assertRaises(ValueError):
                self.check(changed)


if __name__ == "__main__":
    unittest.main(verbosity=2)
