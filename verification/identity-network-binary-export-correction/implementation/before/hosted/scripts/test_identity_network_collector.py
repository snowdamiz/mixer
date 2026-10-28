#!/usr/bin/env python3
"""Independent, pure orchestration controls for the targeted identity collector.

These fixtures deliberately exercise acceptance decisions. They do not run Docker,
product code, processes, sockets, compilers, native runtimes, or version probes.
The contract's immutable roots and exact product method/receipt facts are written
independently here rather than derived from collector constants under test.
"""
import copy
import hashlib
import importlib.util
import io
import json
import signal
from pathlib import Path
import sys
import tarfile
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

sys.dont_write_bytecode = True
COLLECTOR_PATH = Path(__file__).with_name("test-identity-network.py")
spec = importlib.util.spec_from_file_location("identity_network_control_subject", COLLECTOR_PATH)
collector = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = collector
# Import is itself part of the control: an import must never launch work.
with mock.patch("subprocess.Popen", side_effect=AssertionError("process action during import")), \
        mock.patch("os.system", side_effect=AssertionError("shell action during import")), \
        mock.patch("socket.socket", side_effect=AssertionError("socket action during import")), \
        mock.patch("socket.create_connection", side_effect=AssertionError("connection action during import")):
    spec.loader.exec_module(collector)

_execution_guards = []


def setUpModule():
    # Even a producer regression cannot turn a pure control into a child launch.
    for target in ("subprocess.Popen", "os.system", "socket.socket", "socket.create_connection"):
        patcher = mock.patch(target, side_effect=AssertionError("external execution forbidden in pure controls"))
        patcher.start()
        _execution_guards.append(patcher)


def tearDownModule():
    for patcher in reversed(_execution_guards):
        patcher.stop()
    _execution_guards.clear()


PRODUCT_DIGEST = "023df04c9a4599c3d5a6cdf2afb53a95e2faf37765d8b96ba2bcc0e1b007c92e"
LOCK_DIGEST = "1eada39dcaf4863d02d39f51e218d2bad8908b36a0cba47ff2d16037b7bcf837"
ELIXIR_REF = "hexpm/elixir@sha256:ed110657152803079f311913be4effe02874e2c714a1b5a38891873b7f2a16c5"
ELIXIR_CONFIG = "sha256:857e84a618d1f76390220fbff2e7d54d588aea4f772ab1e60dacfe3fa02602cc"
POSTGRES_REF = "library/postgres@sha256:cf5d353f55240ecc2f811827a15c7d1f2d562f08019b49dca12b5a59f4ab5962"
POSTGRES_CONFIG = "sha256:6a35283e53fbe883da6a6ffbce8d3999dc66076cc5c4e2f1d21bdbd9e26bf86f"
KEY_METHOD = (
    "Elixir.MixerHosted.Identity.KeyOwnerLinuxNetworkTest",
    "test K03 production resolver/classifier pins public peer despite rebinding; private sink remains untouched",
)
STARTUP_METHOD = (
    "Elixir.MixerHosted.Identity.StartupLinuxNetworkTest",
    "test IS04 IS05 actual configured startup cold production DNS TLS admission and lifecycle",
)
CID_TEST, CID_PG, CID_PREPARE = "1" * 64, "2" * 64, "3" * 64
RUN_LABEL = "100-1-0123456789abcdef0123456789abcdef"


def canonical_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def exact_events():
    result = [{"event": "suite_started"}]
    for module, name in (KEY_METHOD, STARTUP_METHOD):
        result.extend([
            {"event": "test_started", "module": module, "name": name},
            {"event": "test_finished", "module": module, "name": name, "state": None},
        ])
    result.append({"event": "suite_finished", "total": 2, "failures": 0,
                   "skipped": 0, "excluded": 0, "invalid": 0})
    return result


def exact_semantics():
    return {
        "production-DNS-rebinding.json": {
            "initialQueries": 2, "authenticatedPeer": "8.8.8.8:443",
            "publicConnections": 1, "forbiddenSinkConnections": 0,
            "newPrivateAnswerRejectedBeforeConnect": True,
            "namespace": "disposable network-none Linux lo:1; no product resolver or loopback bypass",
        },
        "startup-production-network.json": {
            "actualApplication": True, "endpointLiveness": 200,
            "namespace": "owned Linux network-none NET_ADMIN; 8.8.8.8 on lo:1",
            "resolver": "127.0.0.1:53", "destination": "8.8.8.8:443",
            "startupDNSQueries": 0, "startupConnections": 0,
            "coldTokenAdmitted": True, "coldDNSQueries": 2, "coldConnections": 1,
            "oldLeaseRejectedAfterRestart": True, "restartColdAdmission": True,
            "shutdownInflightCancelled": True, "allThreeConnectionsClosed": True,
            "fixtureKeyDirectoryRemoved": True,
            "publicAdapter": "ConfiguredVerifier.authenticate/2", "productionPolicyBypasses": 0,
        },
    }


def exact_namespace():
    return {"interfaces": ["lo"], "default_routes": [], "netns": "net:[200]",
            "public_address": "8.8.8.8", "setup_socket_closed": True,
            "cap_eff": "0000000000001400", "cap_prm": "0000000000001400",
            "cap_bnd": "0000000000001400", "open_setup_sockets": 0}


def exact_image(role):
    pg = role == "pg"
    return {"Id": POSTGRES_CONFIG if pg else ELIXIR_CONFIG, "Os": "linux",
            "Architecture": "amd64", "RepoDigests": [POSTGRES_REF if pg else ELIXIR_REF]}


def owned(role):
    cid = {"prepare": CID_PREPARE, "test": CID_TEST, "pg": CID_PG}[role]
    return collector.OwnedContainer(
        cid=cid, name=f"mixer-identity-net-{RUN_LABEL}-{role}", role=role,
        image_id=POSTGRES_CONFIG if role == "pg" else ELIXIR_CONFIG, label=RUN_LABEL,
    )


def exact_container(role):
    pg = role == "pg"
    tmpfs = {"/tmp": "rw,nosuid,nodev,size=67108864,mode=1777"}
    if pg:
        tmpfs.update({"/var/lib/postgresql/data": "rw,nosuid,nodev,size=536870912,mode=0700",
                      "/var/run/postgresql": "rw,nosuid,nodev,size=16777216,mode=0775"})
    else:
        tmpfs["/tmp"] = "rw,nosuid,nodev,noexec,size=67108864,mode=1777"
        tmpfs["/workspace"] = "rw,nosuid,nodev,noexec,size=1006632960,mode=0755"
        tmpfs["/workspace/tooling"] = "rw,nosuid,nodev,exec,size=67108864,mode=0755"
        if role == "test":
            tmpfs["/run"] = "rw,nosuid,nodev,size=16777216,mode=0755"
    return {
        "Id": owned(role).cid, "Name": "/" + owned(role).name,
        "Image": POSTGRES_CONFIG if pg else ELIXIR_CONFIG,
        "Config": {"Labels": {"mixer.identity.run": RUN_LABEL, "mixer.identity.role": role}},
        "HostConfig": {
            "NetworkMode": f"container:{CID_TEST}" if pg else ("none" if role == "test" else "bridge"),
            "ReadonlyRootfs": True, "CapDrop": ["ALL"],
            "CapAdd": (["CHOWN", "DAC_OVERRIDE", "FOWNER", "SETUID", "SETGID"] if pg else
                       ["NET_ADMIN", "NET_BIND_SERVICE"] if role == "test" else []),
            "Privileged": False, "Binds": [], "Devices": [], "PortBindings": {},
            "Memory": 1073741824 if pg else 2147483648,
            "MemorySwap": 1073741824 if pg else 2147483648,
            "NanoCpus": 1000000000 if pg else 2000000000,
            "PidsLimit": 128 if pg else 256,
            "SecurityOpt": ["no-new-privileges:true"],
            "Ulimits": [{"Name": "nofile", "Soft": 4096, "Hard": 4096}], "Tmpfs": tmpfs,
        },
        "Mounts": [],
    }


def archive(entries):
    """Build headers in memory only; entries are (name,type,payload,linkname)."""
    memory = io.BytesIO()
    with tarfile.open(fileobj=memory, mode="w") as out:
        for name, kind, payload, linkname in entries:
            info = tarfile.TarInfo(name)
            info.type = kind
            info.linkname = linkname
            info.size = len(payload) if kind == tarfile.REGTYPE else 0
            out.addfile(info, io.BytesIO(payload) if kind == tarfile.REGTYPE else None)
    memory.seek(0)
    return tarfile.open(fileobj=memory, mode="r:")


class SourceControls(unittest.TestCase):
    def test_frozen_source_has_independent_contract_root_and_lock(self):
        self.assertEqual(177, len(collector.FROZEN_MANIFEST))
        self.assertEqual(PRODUCT_DIGEST, canonical_digest(collector.FROZEN_MANIFEST))
        self.assertEqual(LOCK_DIGEST, collector.FROZEN_MANIFEST["hosted/mix.lock"]["sha256"])
        collector.validate_source_manifest(copy.deepcopy(collector.FROZEN_MANIFEST))

    def test_changed_missing_and_extra_frozen_sources_are_refused(self):
        base = collector.FROZEN_MANIFEST
        mutations = []
        changed = copy.deepcopy(base)
        changed["hosted/mix.lock"]["sha256"] = "0" * 64
        mutations.append(changed)
        changed = copy.deepcopy(base)
        changed.pop(next(path for path in base if path != "hosted/mix.lock"))
        mutations.append(changed)
        changed = copy.deepcopy(base)
        changed["hosted/test/extra_test.exs"] = {"bytes": 0, "sha256": "0" * 64}
        mutations.append(changed)
        for value in mutations:
            with self.subTest(paths=len(value)), self.assertRaises(collector.CollectorError):
                collector.validate_source_manifest(value)

    def test_wrong_lock_cannot_be_authorized_by_a_new_manifest_digest(self):
        value = copy.deepcopy(collector.FROZEN_MANIFEST)
        value["hosted/mix.lock"]["sha256"] = "0" * 64
        with self.assertRaises(collector.CollectorError):
            collector.validate_source_manifest(value, expected_digest=canonical_digest(value), expected_count=177)

    def test_manifest_structure_cannot_be_authorized_by_its_own_digest(self):
        for path in ("/hosted/escape.ex", "hosted/../escape.ex", "hosted\\escape.ex", "hosted//alias.ex", "outside.ex"):
            value = copy.deepcopy(collector.FROZEN_MANIFEST)
            metadata = value.pop("hosted/.formatter.exs")
            value[path] = metadata
            with self.subTest(path=path), self.assertRaises(collector.CollectorError):
                collector.validate_source_manifest(value, expected_digest=canonical_digest(value), expected_count=177)
        for metadata in ({"bytes": -1, "sha256": "a" * 64},
                         {"bytes": True, "sha256": "a" * 64},
                         {"bytes": 1, "sha256": "g" * 64},
                         {"bytes": 1, "sha256": "a" * 63}):
            value = copy.deepcopy(collector.FROZEN_MANIFEST)
            value["hosted/.formatter.exs"] = metadata
            with self.subTest(metadata=metadata), self.assertRaises(collector.CollectorError):
                collector.validate_source_manifest(value, expected_digest=canonical_digest(value), expected_count=177)

    def test_source_mutation_added_deleted_and_changed_are_all_refused(self):
        before = {"hosted/mix.lock": {"bytes": 2, "sha256": "a" * 64},
                  "hosted/lib/a.ex": {"bytes": 1, "sha256": "b" * 64}}
        collector.validate_source_unchanged(before, copy.deepcopy(before))
        for after in ({"hosted/mix.lock": before["hosted/mix.lock"]},
                      dict(before, **{"hosted/lib/extra.ex": {"bytes": 1, "sha256": "c" * 64}}),
                      dict(before, **{"hosted/mix.lock": {"bytes": 2, "sha256": "c" * 64}})):
            with self.subTest(after=after), self.assertRaises(collector.CollectorError):
                collector.validate_source_unchanged(before, after)


class ImageAndEnvironmentControls(unittest.TestCase):
    def test_only_exact_selected_image_and_config_platform_roots_pass(self):
        for role in ("prepare", "test", "pg"):
            collector.validate_image_inspect(role, exact_image(role))

    def test_right_manifest_does_not_excuse_wrong_config_or_platform(self):
        for role in ("test", "pg"):
            for field, value in (("Id", "sha256:" + "0" * 64), ("Os", "darwin"),
                                 ("Architecture", "arm64"), ("RepoDigests", []),
                                 ("RepoDigests", ["hexpm/elixir:1.20.4-erlang-29.1.1-ubuntu-noble-20260911"]),
                                 ("RepoDigests", ["hexpm/elixir@sha256:52ec0f335b9084bcfc0ce3a29b4c0288dc2fc2a07658ff809dc7d07589212cde"])):
                value_inspect = exact_image(role)
                value_inspect[field] = value
                with self.subTest(role=role, field=field, value=value), self.assertRaises(collector.CollectorError):
                    collector.validate_image_inspect(role, value_inspect)

    def test_environment_is_explicit_and_does_not_inherit_caller_values(self):
        result = collector.validate_environment({"UNRELATED_VALUE": "must not enter container"})
        self.assertNotIn("UNRELATED_VALUE", result)
        self.assertNotIn("MIXER_ISOLATED_NETNS", result)
        self.assertEqual("test", result["MIX_ENV"])
        self.assertEqual("/workspace/tooling/rebar3", result["MIX_REBAR3"])
        self.assertEqual("/workspace/home", result["HOME"])

    def test_official_bootstrap_pins_match_independent_contract_selection(self):
        expected = {
            "hex": {"url": "https://builds.hex.pm/installs/1.20.0/hex-2.5.1-otp-29.ez", "version": "2.5.1",
                    "sha512": "6629f4b4bb2e040326151ebb853aad065e342c65ad3a0f2a2674dcf7164eb4328d6c929513d7230309ad75042024e72bef0e0a51ebff373b4173d2746b1772b7"},
            "rebar": {"url": "https://builds.hex.pm/installs/1.18.4/rebar3-3.28.0-otp-29", "version": "3.28.0",
                      "sha512": "b51946058fbe4aa823185bfe27204be59be439982ac3a3e1dbd9f8260b9af046fcfdfbd9066283c3fbba5a2a45dc3570550c12a9a548daf223b80cac222a6d0f"},
        }
        self.assertEqual(expected, collector.BOOTSTRAP)

    def test_caller_isolation_secret_and_startup_overrides_are_refused(self):
        for key, value in (("MIXER_ISOLATED_NETNS", "1"), ("MIXER_OTHER", "x"),
                           ("HEX_API_KEY", "secret"), ("GITHUB_TOKEN", "secret"),
                           ("AWS_ACCESS_KEY_ID", "secret"), ("ERL_FLAGS", "-eval bad"),
                           ("ELIXIR_ERL_OPTIONS", "-eval bad"), ("MIX_HOME", "/attacker")):
            with self.subTest(key=key), self.assertRaises(collector.CollectorError):
                collector.validate_environment({key: value})


def exact_metadata():
    root = COLLECTOR_PATH.resolve().parents[2]
    old_base = "verification/identity-production-network-contract/"
    new_base = "verification/identity-network-image-amendment-v1/metadata/"
    paths = [old_base + "contract.json", old_base + "packet-manifest.json"]
    for label in ("elixir", "postgres"):
        paths += [old_base + "inputs/registry/" + label + suffix for suffix in ("-index.json", "-amd64-manifest.json", "-amd64-config.json")]
    manifest = json.loads((root / new_base / "packet-manifest.json").read_bytes())
    paths += [new_base + "packet-manifest.json"] + [new_base + path for path in manifest["files"]]
    return {path: (root / path).read_bytes() for path in paths}


def exact_prerequisites():
    # Expected immutable source rows are an input fixture, not an execution receipt.
    root = COLLECTOR_PATH.resolve().parents[2]
    amendment = json.loads((root / "verification/identity-network-image-amendment-v1/metadata/image-amendment.json").read_bytes())
    expected = amendment["prerequisites"]
    actual = {"elixir": "1.20.4", "otp_patch": "29.1.1", "mix": "Mix 1.20.4 (compiled with Erlang/OTP 29)",
              "openssl": "OpenSSL 3.0.22 CONTROL-PLACEHOLDER-DATE\nplatform: debian-amd64\n",
              "crypto": "pure-control-fixture-not-a-runtime-result",
              "crypto_libraries": [{"name": "OpenSSL", "number": 805306720, "version": "OpenSSL 3.0.22 CONTROL-PLACEHOLDER-DATE"}],
              "tools": copy.deepcopy(expected["tools"]), "versions": {"/usr/bin/tar": "tar (GNU tar) 1.34\n"},
              "ca": {key: expected["ca"][key] for key in ("path", "bytes", "sha256")}}
    actual["ca"].update(load="explicit-selected-bundle", loaded_count=150, loaded_der_sha256=copy.deepcopy(expected["ca"]["der_sha256"]))
    return actual, expected


def exact_execution_metadata():
    values = exact_metadata()
    root = COLLECTOR_PATH.resolve().parents[2]
    base = "verification/identity-network-image-amendment-v2/metadata/"
    manifest = json.loads((root / base / "packet-manifest.json").read_bytes())
    for path in ["packet-manifest.json", *manifest["files"]]:
        values[base + path] = (root / base / path).read_bytes()
    return values


def exact_execution_contract():
    root = COLLECTOR_PATH.resolve().parents[2]
    contract = json.loads((root / "verification/identity-network-image-amendment-v2/metadata/execution-amendment.json").read_bytes())
    image = json.loads((root / "verification/identity-network-image-amendment-v1/metadata/image-amendment.json").read_bytes())
    return contract, image


def exact_mounts(role):
    lines = ["101 99 0:7 / /workspace rw,nosuid,nodev,noexec,relatime - tmpfs tmpfs rw,size=983040k,mode=755",
             "102 101 0:8 / /workspace/tooling rw,nosuid,nodev,relatime - tmpfs tmpfs rw,size=65536k,mode=755",
             "103 99 0:9 / /tmp rw,nosuid,nodev,noexec,relatime - tmpfs tmpfs rw,size=65536k"]
    modes = {"/workspace": 0o755, "/workspace/tooling": 0o755, "/tmp": 0o1777}
    if role == "test":
        lines.append("104 99 0:10 / /run rw,nosuid,nodev,noexec,relatime - tmpfs tmpfs rw,size=16384k,mode=755")
        modes["/run"] = 0o755
    return {"role": role, "source": "/proc/self/mountinfo", "read_bytes": 1000 + sum(len(line) + 1 for line in lines),
            "read_sha256": "a" * 64, "selected_lines": lines, "path_modes": modes}


class ImageAmendmentControls(unittest.TestCase):
    def test_selected_metadata_requires_both_independent_immutable_roots(self):
        self.assertEqual("6a2ec88721d89a28e40961f834b856598ba0f6f14d88708906cf3931e0e33afa", collector.AMENDMENT_SHA256)
        self.assertEqual("9ddc12c8277b120dcd8ef7577dd9da03d245b8502802db85399a6f1104bcbdc8", collector.AMENDMENT_PACKET)
        self.assertEqual("261023b77cb55255f666959f367330783a354174252ed23b71145566f87ba597", collector.SOURCE_REVIEW_PACKET)
        amendment = collector.validate_selected_metadata(exact_metadata())
        self.assertEqual(ELIXIR_REF, amendment["test_image"]["ref"])
        self.assertEqual(POSTGRES_REF, amendment["preserved"]["postgres"]["ref"])
        self.assertEqual(177, amendment["preserved"]["product_files"])
        self.assertEqual(PRODUCT_DIGEST, amendment["preserved"]["product_digest"])
        self.assertEqual(LOCK_DIGEST, amendment["preserved"]["lock_sha256"])

    def test_old_image_and_old_config_are_refused_for_prepare_and_test(self):
        for role in ("prepare", "test"):
            for field, old in (("Id", "sha256:6631543fddfe053ddbd30435318916667d5da87b5f5ec0644893d146a539370e"),
                               ("RepoDigests", ["hexpm/elixir@sha256:3571d320ec0656c38c76b4c362a8e0c0fd6f9b58cec6448a08e43a82940d4e43"]),
                               ("RepoDigests", ["hexpm/elixir@sha256:1ae099301985ddf8a723ad50cc25e37dd854497aec12cebf984c195570b0d83e"])):
                value = exact_image(role)
                value[field] = old
                with self.subTest(role=role, field=field, old=old), self.assertRaises(collector.CollectorError):
                    collector.validate_image_inspect(role, value)

    def test_every_missing_selected_metadata_file_is_refused(self):
        base = exact_metadata()
        for path in base:
            value = dict(base)
            value.pop(path)
            with self.subTest(path=path), self.assertRaises(collector.CollectorError):
                collector.validate_selected_metadata(value)

    def test_metadata_bytes_cannot_drift_in_either_namespace(self):
        base = exact_metadata()
        targets = [path for path in base if not path.endswith("packet-manifest.json")]
        for path in targets:
            value = dict(base)
            value[path] += b" "
            with self.subTest(path=path), self.assertRaises(collector.CollectorError):
                collector.validate_selected_metadata(value)

    def test_amendment_seal_is_not_self_asserted_by_a_recomputed_tree(self):
        value = exact_metadata()
        path = "verification/identity-network-image-amendment-v1/metadata/packet-manifest.json"
        packet = json.loads(value[path])
        packet["files"]["image-amendment.json"]["sha256"] = "0" * 64
        packet["tree_digest_sha256"] = canonical_digest(packet["files"])
        value[path] = json.dumps(packet).encode()
        with self.assertRaises(collector.CollectorError):
            collector.validate_selected_metadata(value)

    def test_old_packet_cannot_replace_new_amendment_or_its_seal(self):
        for target, replacement in (("packet-manifest.json", "packet-manifest.json"),
                                    ("image-amendment.json", "contract.json"),
                                    ("inputs/registry/elixir-amd64-manifest.json", "inputs/registry/elixir-amd64-manifest.json"),
                                    ("inputs/registry/elixir-amd64-config.json", "inputs/registry/elixir-amd64-config.json")):
            value = exact_metadata()
            value["verification/identity-network-image-amendment-v1/metadata/" + target] = value["verification/identity-production-network-contract/" + replacement]
            with self.subTest(target=target), self.assertRaises(collector.CollectorError):
                collector.validate_selected_metadata(value)

    def test_extra_overlay_metadata_is_refused(self):
        value = exact_metadata()
        value["verification/identity-network-image-amendment-v1/metadata/override.json"] = b'{"image":"unreviewed"}'
        with self.assertRaises(collector.CollectorError):
            collector.validate_selected_metadata(value)

    def test_selected_metadata_archive_retains_both_namespaces_and_review(self):
        values = exact_metadata()
        with tarfile.open(fileobj=io.BytesIO(collector.source_tar(values)), mode="r:") as archive_value:
            rows = {member.name: archive_value.extractfile(member).read() for member in collector.safe_members(archive_value)}
        self.assertEqual(values, rows)
        self.assertIn("verification/identity-production-network-contract/inputs/registry/postgres-amd64-config.json", rows)
        self.assertIn("verification/identity-network-image-amendment-v1/metadata/source-review/packet-manifest.json", rows)


class ExecutionAmendmentControls(unittest.TestCase):
    def test_closed_execution_contract_binds_prior_actual_prerequisites_and_same_image(self):
        self.assertEqual("b447fe5919c4e73d86aee4da707570127de2c35ecdae5a7b90b0163eb9bc436c", collector.EXECUTION_SHA256)
        self.assertEqual("0e35cd6dcc1685b16745def4fe0217fc60e5d703c95a5cddbfd2409381c63b6d", collector.EXECUTION_PACKET)
        result = collector.validate_execution_metadata(exact_execution_metadata())
        self.assertEqual(ELIXIR_REF, result["preserved"]["test_image"]["ref"])
        self.assertEqual(177, result["preserved"]["product_pg_bootstrap_contract"]["product_files"])
        self.assertIs(False, result["runtime_basis"]["actual_prior_mountinfo"])
        partition = result["workspace_partition"]
        self.assertEqual(1073741824, partition["workspace_bytes"] + partition["tooling_bytes"])
        self.assertEqual(67108864, partition["tooling_bytes"])

    def test_execution_tables_reject_broad_exec_wrong_paths_sizes_and_extra_mounts(self):
        base, image = exact_execution_contract()
        for role in ("prepare", "test"):
            for path, replacement in (("/workspace", "rw,nosuid,nodev,exec,size=1006632960,mode=0755"),
                                      ("/tmp", "rw,nosuid,nodev,exec,size=67108864,mode=1777"),
                                      ("/workspace/tooling", "rw,nosuid,nodev,exec,size=134217728,mode=0755"),
                                      ("/workspace/unreviewed", "rw,nosuid,nodev,exec,size=67108864,mode=0755")):
                value = copy.deepcopy(base)
                value["new_tmpfs"][role][path] = replacement
                with self.subTest(role=role, path=path), self.assertRaises(collector.CollectorError):
                    collector.validate_execution_contract(value, image)
            value = copy.deepcopy(base)
            value["new_tmpfs"][role].pop("/workspace/tooling")
            with self.subTest(role=role, missing="tooling"), self.assertRaises(collector.CollectorError):
                collector.validate_execution_contract(value, image)

    def test_workspace_carve_cannot_raise_total_or_move_its_role_or_path(self):
        base, image = exact_execution_contract()
        for field, replacement in (("total_bytes", 1140850688), ("workspace_bytes", 1073741824),
                                   ("tooling_bytes", 134217728), ("tooling_bytes", True),
                                   ("tooling_path", "/workspace"), ("roles", ["prepare", "test", "pg"])):
            value = copy.deepcopy(base)
            value["workspace_partition"][field] = replacement
            with self.subTest(field=field), self.assertRaises(collector.CollectorError):
                collector.validate_execution_contract(value, image)

    def test_execution_amendment_preserves_caps_resources_CA_tools_and_pg(self):
        base, image = exact_execution_contract()
        mutations = [lambda v: v["preserved"]["capabilities"]["prepare"].append("SYS_ADMIN"),
                     lambda v: v["preserved"]["resources"]["test"].__setitem__(0, 4294967296),
                     lambda v: v["preserved"]["prerequisites"]["ca"].__setitem__("sha256", "0" * 64),
                     lambda v: v["preserved"]["prerequisites"]["tools"].pop("/usr/bin/openssl"),
                     lambda v: v["preserved"]["product_pg_bootstrap_contract"]["postgres"].__setitem__("config", "sha256:" + "0" * 64)]
        for index, mutate in enumerate(mutations):
            value = copy.deepcopy(base)
            mutate(value)
            with self.subTest(index=index), self.assertRaises(collector.CollectorError):
                collector.validate_execution_contract(value, image)

    def test_each_missing_or_changed_v2_metadata_file_is_refused(self):
        base = exact_execution_metadata()
        for path in [name for name in base if name.startswith("verification/identity-network-image-amendment-v2/")]:
            for operation in ("missing", "changed"):
                value = dict(base)
                if operation == "missing":
                    value.pop(path)
                else:
                    value[path] += b" "
                with self.subTest(path=path, operation=operation), self.assertRaises((collector.CollectorError, json.JSONDecodeError)):
                    collector.validate_execution_metadata(value)

    def test_stale_self_recomputed_or_v1_execution_seals_have_no_authority(self):
        base = exact_execution_metadata()
        path = "verification/identity-network-image-amendment-v2/metadata/packet-manifest.json"
        changed = json.loads(base[path])
        changed["files"]["execution-amendment.json"]["sha256"] = "0" * 64
        changed["tree_digest_sha256"] = canonical_digest(changed["files"])
        for replacement in (json.dumps(changed).encode(), base["verification/identity-network-image-amendment-v1/metadata/packet-manifest.json"]):
            value = dict(base)
            value[path] = replacement
            with self.assertRaises(collector.CollectorError):
                collector.validate_execution_metadata(value)

    def test_inspection_requires_only_exact_carved_tmpfs_with_original_resources(self):
        for role in ("prepare", "test"):
            value = exact_container(role)
            collector.validate_container_inspect(role, value, owned(role))
            for path, replacement in (("/workspace", "rw,nosuid,nodev,exec,size=1006632960,mode=0755"),
                                      ("/workspace/tooling", "rw,nosuid,nodev,exec,size=134217728,mode=0755"),
                                      ("/unexpected", "rw,nosuid,nodev,exec,size=67108864,mode=0755")):
                changed = copy.deepcopy(value)
                changed["HostConfig"]["Tmpfs"][path] = replacement
                with self.subTest(role=role, path=path), self.assertRaises(collector.CollectorError):
                    collector.validate_container_inspect(role, changed, owned(role))


class RebarTransferControls(unittest.TestCase):
    def fixture(self):
        sha = "b51946058fbe4aa823185bfe27204be59be439982ac3a3e1dbd9f8260b9af046fcfdfbd9066283c3fbba5a2a45dc3570550c12a9a548daf223b80cac222a6d0f"
        transfer = {"source": "/workspace/downloads/rebar3", "destination": "/workspace/tooling/rebar3", "download_bytes": 4096, "copied_bytes": 4096, "target_bytes": 4096, "sha512": sha, "exclusive_create": True, "closed_before_hash": True, "owned_download_removed": True}
        download = {"url": "https://builds.hex.pm/installs/1.18.4/rebar3-3.28.0-otp-29", "bytes": 4096, "sha512": sha}
        return transfer, download

    def test_transfer_contract_is_fixed_to_exclusive_bounded_copy_at_unchanged_paths(self):
        contract, image = exact_execution_contract()
        collector.validate_execution_contract(contract, image)
        self.assertEqual("/workspace/downloads/rebar3", contract["bootstrap_transfer"]["source"])
        self.assertEqual("/workspace/tooling/rebar3", contract["bootstrap_transfer"]["destination"])
        self.assertEqual(16777216, contract["bootstrap_transfer"]["max_bytes"])
        for key, replacement in (("source", "/tmp/rebar3"), ("destination", "/workspace/rebar3"),
                                 ("max_bytes", 33554432), ("sha512", "0" * 128), ("copy", "rename-fallback")):
            value = copy.deepcopy(contract)
            value["bootstrap_transfer"][key] = replacement
            with self.subTest(key=key), self.assertRaises(collector.CollectorError):
                collector.validate_execution_contract(value, image)

    def test_exact_closed_and_complete_transfer_receipt_joins_verified_download(self):
        value, download = self.fixture()
        self.assertEqual(value, collector.validate_rebar_transfer(value, download))

    def test_missing_short_overbound_unclosed_hash_mismatch_or_nonexclusive_copy_fails(self):
        base, download = self.fixture()
        for key, replacement in (("source", "/unowned/rebar3"), ("destination", "/workspace/rebar3"),
                                 ("download_bytes", 0), ("download_bytes", True), ("copied_bytes", 4095),
                                 ("target_bytes", 4095), ("target_bytes", 16777217), ("sha512", "0" * 128),
                                 ("exclusive_create", False), ("closed_before_hash", False), ("owned_download_removed", False)):
            value = copy.deepcopy(base)
            value[key] = replacement
            with self.subTest(key=key), self.assertRaises(collector.CollectorError):
                collector.validate_rebar_transfer(value, download)
        for key in base:
            value = copy.deepcopy(base)
            value.pop(key)
            with self.subTest(missing=key), self.assertRaises(collector.CollectorError):
                collector.validate_rebar_transfer(value, download)
        for value in (None, {}, []):
            with self.subTest(value=value), self.assertRaises(collector.CollectorError):
                collector.validate_rebar_transfer(value, download)

    def test_transfer_cannot_join_other_download_size_hash_or_url(self):
        value, download = self.fixture()
        for key, replacement in (("bytes", 4095), ("bytes", True), ("sha512", "0" * 128), ("url", "https://other.invalid/rebar3")):
            observed = copy.deepcopy(download)
            observed[key] = replacement
            with self.subTest(key=key), self.assertRaises(collector.CollectorError):
                collector.validate_rebar_transfer(value, observed)


class ActualMountControls(unittest.TestCase):
    def test_only_selected_tooling_is_executable_with_exact_carved_sizes(self):
        for role in ("prepare", "test"):
            value = exact_mounts(role)
            collector.validate_mount_observation(role, value)
            value["selected_lines"].reverse()
            collector.validate_mount_observation(role, value)

    def test_absent_overbound_wrong_role_or_other_mount_source_is_refused(self):
        for role in ("prepare", "test"):
            for value in (None, {}, [], "declaration-only"):
                with self.subTest(role=role, value=value), self.assertRaises(collector.CollectorError):
                    collector.validate_mount_observation(role, value)
            for field, replacement in (("role", "pg"), ("source", "/proc/1/mountinfo"),
                                       ("read_bytes", 65537), ("read_bytes", True), ("read_bytes", 1),
                                       ("read_sha256", "")):
                value = exact_mounts(role)
                value[field] = replacement
                with self.subTest(role=role, field=field), self.assertRaises(collector.CollectorError):
                    collector.validate_mount_observation(role, value)

    def test_every_missing_mount_line_or_mode_is_refused(self):
        for role in ("prepare", "test"):
            base = exact_mounts(role)
            for index in range(len(base["selected_lines"])):
                value = copy.deepcopy(base)
                value["selected_lines"].pop(index)
                with self.subTest(role=role, missing_line=index), self.assertRaises(collector.CollectorError):
                    collector.validate_mount_observation(role, value)
            for path in base["path_modes"]:
                value = copy.deepcopy(base)
                value["path_modes"].pop(path)
                with self.subTest(role=role, missing_mode=path), self.assertRaises(collector.CollectorError):
                    collector.validate_mount_observation(role, value)

    def test_broad_exec_and_noexec_tooling_missing_security_flags_are_refused(self):
        replacements = [(0, "noexec,", ""), (2, "noexec,", ""),
                        (1, "nodev,", "nodev,noexec,"), (0, "nosuid,", ""),
                        (1, "nodev,", ""), (2, "rw,nosuid", "ro,nosuid"),
                        (0, "rw,nosuid", "rw,exec,nosuid")]
        for index, old, new in replacements:
            value = exact_mounts("prepare")
            value["selected_lines"][index] = value["selected_lines"][index].replace(old, new, 1)
            with self.subTest(index=index, old=old, new=new), self.assertRaises(collector.CollectorError):
                collector.validate_mount_observation("prepare", value)
        value = exact_mounts("test")
        value["selected_lines"][-1] = value["selected_lines"][-1].replace("noexec,", "")
        with self.assertRaises(collector.CollectorError):
            collector.validate_mount_observation("test", value)

    def test_wrong_size_units_filesystem_root_or_tooling_parent_are_refused(self):
        replacements = [(0, "size=983040k", "size=1048576k"), (1, "size=65536k", "size=128m"),
                        (1, "size=65536k", "size=64%"), (0, "size=983040k", "size=983040k,size=983040k"),
                        (0, " - tmpfs tmpfs ", " - ext4 /dev/root "), (1, "102 101 ", "102 99 "),
                        (1, "0:8 / /workspace", "0:8 /subdir /workspace")]
        for index, old, new in replacements:
            value = exact_mounts("prepare")
            value["selected_lines"][index] = value["selected_lines"][index].replace(old, new, 1)
            with self.subTest(old=old, new=new), self.assertRaises(collector.CollectorError):
                collector.validate_mount_observation("prepare", value)

    def test_duplicate_selected_mount_and_additional_descendant_or_mode_drift_is_refused(self):
        base = exact_mounts("prepare")
        for replacement in (base["selected_lines"][0],
                            "105 102 0:11 / /workspace/tooling/escape rw,nosuid,nodev,relatime - tmpfs tmpfs rw,size=65536k"):
            value = copy.deepcopy(base)
            value["selected_lines"].append(replacement)
            with self.assertRaises(collector.CollectorError):
                collector.validate_mount_observation("prepare", value)
        value = copy.deepcopy(base)
        value["path_modes"]["/workspace/tooling"] = 0o777
        with self.assertRaises(collector.CollectorError):
            collector.validate_mount_observation("prepare", value)


class PrerequisiteControls(unittest.TestCase):
    def test_complete_actual_tool_ca_and_crypto_result_passes_pure_validation(self):
        value, expected = exact_prerequisites()
        self.assertEqual("/etc/ssl/certs/ca-certificates.crt", expected["ca"]["path"])
        self.assertEqual(224449, expected["ca"]["bytes"])
        self.assertEqual("714d457d580922dbf1d0be8bd35ba236a842b50b0072ae791582a19adef772a5", expected["ca"]["sha256"])
        self.assertEqual(150, len(expected["ca"]["der_sha256"]))
        self.assertEqual(value, collector.validate_prerequisites(value, expected))

    def test_missing_actual_result_and_each_observation_are_refused(self):
        base, expected = exact_prerequisites()
        for value in (None, {}, [], "source-present-only"):
            with self.subTest(value=value), self.assertRaises(collector.CollectorError):
                collector.validate_prerequisites(value, expected)
        for key in base:
            value = copy.deepcopy(base)
            value.pop(key)
            with self.subTest(missing=key), self.assertRaises(collector.CollectorError):
                collector.validate_prerequisites(value, expected)

    def test_wrong_missing_or_stale_ca_bundle_and_loaded_roots_are_refused(self):
        base, expected = exact_prerequisites()
        mutations = [("path", "/unreviewed/roots.pem"), ("bytes", 0), ("bytes", True),
                     ("sha256", "0" * 64), ("load", "default-fallback"),
                     ("loaded_count", 0), ("loaded_count", True), ("loaded_count", 149),
                     ("loaded_der_sha256", []), ("loaded_der_sha256", ["0" * 64] * 150)]
        for field, replacement in mutations:
            value = copy.deepcopy(base)
            value["ca"][field] = replacement
            with self.subTest(field=field, replacement=replacement), self.assertRaises(collector.CollectorError):
                collector.validate_prerequisites(value, expected)
        for field in base["ca"]:
            value = copy.deepcopy(base)
            value["ca"].pop(field)
            with self.subTest(missing_ca_field=field), self.assertRaises(collector.CollectorError):
                collector.validate_prerequisites(value, expected)

    def test_actual_crypto_library_name_numeric_and_full_version_are_required(self):
        base, expected = exact_prerequisites()
        for field, replacement in (("name", "LibreSSL"), ("number", 0), ("number", True),
                                   ("version", "OpenSSL 3.0.21 old"), ("version", "")):
            value = copy.deepcopy(base)
            value["crypto_libraries"][0][field] = replacement
            with self.subTest(field=field, replacement=replacement), self.assertRaises(collector.CollectorError):
                collector.validate_prerequisites(value, expected)
        for replacement in ([], {}, None, [{"name": "OpenSSL"}]):
            value = copy.deepcopy(base)
            value["crypto_libraries"] = replacement
            with self.subTest(replacement=replacement), self.assertRaises(collector.CollectorError):
                collector.validate_prerequisites(value, expected)

    def test_each_actual_executable_must_match_source_bytes_and_hash(self):
        base, expected = exact_prerequisites()
        for path in base["tools"]:
            for field, replacement in (("bytes", 0), ("bytes", True), ("sha256", "0" * 64)):
                value = copy.deepcopy(base)
                value["tools"][path][field] = replacement
                with self.subTest(path=path, field=field), self.assertRaises(collector.CollectorError):
                    collector.validate_prerequisites(value, expected)
            value = copy.deepcopy(base)
            value["tools"].pop(path)
            with self.subTest(missing=path), self.assertRaises(collector.CollectorError):
                collector.validate_prerequisites(value, expected)

    def test_actual_vm_and_version_results_cannot_be_missing_or_stale(self):
        base, expected = exact_prerequisites()
        for key, replacement in (("elixir", "1.20.3"), ("otp_patch", "29.1"), ("mix", ""),
                                 ("openssl", "OpenSSL 3.0.21 old"), ("crypto", ""),
                                 ("versions", {}), ("versions", {"/usr/bin/tar": "tar unavailable"})):
            value = copy.deepcopy(base)
            value[key] = replacement
            with self.subTest(key=key), self.assertRaises(collector.CollectorError):
                collector.validate_prerequisites(value, expected)


class ArchiveControls(unittest.TestCase):
    def test_regular_files_in_safe_directories_pass_without_extraction(self):
        with archive([("hosted/lib/a.ex", tarfile.REGTYPE, b"a", ""),
                      ("tooling/rebar3", tarfile.REGTYPE, b"b", "")]) as value:
            self.assertEqual(2, len(collector.safe_members(value, max_bytes=2)))

    def test_absolute_parent_backslash_and_normalized_alias_members_refused(self):
        for name in ("/outside", "../outside", "hosted/../../outside", "hosted/../a.ex",
                     "hosted\\a.ex", "hosted//a.ex", "./hosted/a.ex"):
            with self.subTest(name=name), archive([(name, tarfile.REGTYPE, b"x", "")]) as value, \
                    self.assertRaises(collector.CollectorError):
                collector.safe_members(value)

    def test_links_devices_and_fifo_refused_even_with_in_root_targets(self):
        for kind in (tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.CHRTYPE, tarfile.BLKTYPE, tarfile.FIFOTYPE):
            with self.subTest(kind=kind), archive([("hosted/a", kind, b"", "hosted/b")]) as value, \
                    self.assertRaises(collector.CollectorError):
                collector.safe_members(value)

    def test_duplicate_paths_refused_even_when_bytes_agree(self):
        with archive([("hosted/a.ex", tarfile.REGTYPE, b"x", ""),
                      ("hosted/a.ex", tarfile.REGTYPE, b"x", "")]) as value, \
                self.assertRaises(collector.CollectorError):
            collector.safe_members(value)

    def test_aggregate_expanded_size_cap_is_enforced(self):
        for entries in ([('hosted/a', tarfile.REGTYPE, b'abc', '')],
                        [('hosted/a', tarfile.REGTYPE, b'ab', ''), ('hosted/b', tarfile.REGTYPE, b'c', '')]):
            with self.subTest(entries=len(entries)), archive(entries) as value, self.assertRaises(collector.CollectorError):
                collector.safe_members(value, max_bytes=2)


class PreparedArchiveControls(unittest.TestCase):
    """Composition tests; immutable source admission is covered separately above.

    A tiny in-memory source gate substitutes only the 177-file hash preimage. It
    verifies delegation to that gate while exercising real archive membership,
    hash, section and contamination decisions without reading product code.
    """
    def fixture(self):
        bodies = {
            "hosted/lib/fixture.ex": b"frozen source fixture",
            "hosted/deps/dependency/lib/fixture.ex": b"dependency fixture",
            "tooling/rebar3": b"checked bootstrap fixture",
            "collector-prerequisites.exs": b"prerequisites fixture",
            "collector-bootstrap.exs": b"bootstrap fixture",
            "collector-manifest.exs": b"manifest fixture",
            "collector-netns.exs": b"netns fixture",
            "collector-observer.exs": b"observer fixture",
            "collector-mounts.exs": b"mounts fixture",
        }
        source = {"hosted/lib/fixture.ex": {"bytes": len(bodies["hosted/lib/fixture.ex"]),
                  "sha256": hashlib.sha256(bodies["hosted/lib/fixture.ex"]).hexdigest()}}
        bodies["frozen-manifest.json"] = json.dumps(source, sort_keys=True, separators=(",", ":")).encode()
        manifest = {"source": {}, "deps": {}, "tools": {}, "helpers": {}}
        for path, body in bodies.items():
            section = "deps" if path.startswith("hosted/deps/") else "source" if path.startswith("hosted/") else "tools" if path.startswith("tooling/") else "helpers"
            manifest[section][path] = {"bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()}
        return bodies, manifest

    def run_fixture(self, bodies, manifest):
        with archive([(name, tarfile.REGTYPE, body, "") for name, body in bodies.items()]) as value:
            data = value.fileobj.getvalue()
        bootstrap = copy.deepcopy(collector.BOOTSTRAP)
        bootstrap["rebar"]["sha512"] = hashlib.sha512(b"checked bootstrap fixture").hexdigest()
        with mock.patch.object(collector, "validate_source_manifest") as source_gate, \
                mock.patch.multiple(collector, FROZEN_MANIFEST=manifest["source"], BOOTSTRAP=bootstrap,
                                    PREREQUISITES_EXS="prerequisites fixture", BOOTSTRAP_EXS="bootstrap fixture",
                                    MANIFEST_EXS="manifest fixture",
                                    NETNS_EXS="netns fixture", OBSERVER_EXS="observer fixture", MOUNTS_EXS="mounts fixture"):
            result = collector.validate_prepared_archive(data, manifest)
            source_gate.assert_called_once_with(manifest["source"])
            return result

    def test_exact_section_membership_and_hashes_pass_after_source_admission(self):
        bodies, manifest = self.fixture()
        self.assertEqual(set(bodies), set(self.run_fixture(bodies, manifest)))

    def test_unlisted_added_missing_and_mutated_payloads_refused(self):
        for operation in ("extra", "missing", "changed"):
            bodies, manifest = self.fixture()
            if operation == "extra":
                bodies["hosted/deps/injected.ex"] = b"injected"
            elif operation == "missing":
                del bodies["collector-observer.exs"]
            else:
                bodies["collector-observer.exs"] = b"different"
            with self.subTest(operation=operation), self.assertRaises(collector.CollectorError):
                self.run_fixture(bodies, manifest)

    def test_changed_helper_or_rebar_refused_even_with_recomputed_archive_manifest(self):
        for path in ("collector-observer.exs", "tooling/rebar3"):
            bodies, manifest = self.fixture()
            bodies[path] = b"attacker replacement"
            section = "helpers" if path.endswith(".exs") else "tools"
            manifest[section][path] = {"bytes": len(bodies[path]), "sha256": hashlib.sha256(bodies[path]).hexdigest()}
            with self.subTest(path=path), self.assertRaises(collector.CollectorError):
                self.run_fixture(bodies, manifest)

    def test_fresh_evidence_build_keys_and_section_injection_refused(self):
        for section, path in (("deps", "hosted/evidence/identity/old.json"),
                              ("deps", "hosted/_build/test/a.beam"),
                              ("deps", "hosted/deps/x/mixer-key-owner-tls-123/key.pem"),
                              ("deps", "hosted/lib/injected.ex"),
                              ("tools", "tooling/mix/archives/hex-999/hex.beam"),
                              ("helpers", "attacker-observer.exs")):
            bodies, manifest = self.fixture()
            bodies[path] = b"injected"
            manifest[section][path] = {"bytes": 8, "sha256": hashlib.sha256(b"injected").hexdigest()}
            with self.subTest(section=section, path=path), self.assertRaises(collector.CollectorError):
                self.run_fixture(bodies, manifest)


class NamespaceControls(unittest.TestCase):
    def test_only_owned_lo_namespace_with_closed_setup_socket_passes(self):
        collector.validate_namespace(exact_namespace(), "net:[100]")

    def test_external_interface_host_namespace_route_alias_and_setup_failures_refused(self):
        for key, value in (("interfaces", ["lo", "eth0"]), ("interfaces", []),
                           ("default_routes", ["default via 172.17.0.1 dev eth0"]),
                           ("default_routes", ["::/0 dev lo"]), ("netns", "net:[100]"),
                           ("public_address", "127.0.0.1"), ("setup_socket_closed", False),
                           ("setup_socket_closed", 1), ("open_setup_sockets", 1),
                           ("cap_eff", "0000000000003400"), ("cap_prm", "0000000000000000"),
                           ("cap_bnd", "0000003fffffffff")):
            evidence = exact_namespace()
            evidence[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(collector.CollectorError):
                collector.validate_namespace(evidence, "net:[100]")

    def test_missing_namespace_observations_refused(self):
        for key in exact_namespace():
            evidence = exact_namespace()
            del evidence[key]
            with self.subTest(key=key), self.assertRaises(collector.CollectorError):
                collector.validate_namespace(evidence, "net:[100]")

    def test_each_role_has_an_independently_valid_resource_fixture(self):
        for role in ("prepare", "test", "pg"):
            collector.validate_container_inspect(role, exact_container(role), owned(role), test_cid=CID_TEST)

    def test_postgres_exposed_metadata_passes_but_host_publication_refused(self):
        document = exact_container("pg")
        document["NetworkSettings"] = {"Ports": {"5432/tcp": None}}
        collector.validate_container_inspect("pg", document, owned("pg"), test_cid=CID_TEST)
        document["NetworkSettings"]["Ports"]["5432/tcp"] = [{"HostIp": "0.0.0.0", "HostPort": "5432"}]
        with self.assertRaises(collector.CollectorError):
            collector.validate_container_inspect("pg", document, owned("pg"), test_cid=CID_TEST)

    def test_wrong_identity_and_network_sharing_refused(self):
        for role in ("test", "pg"):
            for field, value in (("Id", "4" * 64), ("Image", "sha256:" + "0" * 64)):
                document = exact_container(role)
                document[field] = value
                with self.subTest(role=role, field=field), self.assertRaises(collector.CollectorError):
                    collector.validate_container_inspect(role, document, owned(role), test_cid=CID_TEST)
            for mode in ("host", "bridge", f"container:{'4' * 64}"):
                document = exact_container(role)
                document["HostConfig"]["NetworkMode"] = mode
                with self.subTest(role=role, network=mode), self.assertRaises(collector.CollectorError):
                    collector.validate_container_inspect(role, document, owned(role), test_cid=CID_TEST)
        for label in ("mixer.identity.run", "mixer.identity.role"):
            document = exact_container("test")
            document["Config"]["Labels"][label] = "other"
            with self.subTest(label=label), self.assertRaises(collector.CollectorError):
                collector.validate_container_inspect("test", document, owned("test"), test_cid=CID_TEST)

    def test_extra_privilege_mount_publication_and_unbounded_resources_refused(self):
        attacks = (("Privileged", True), ("ReadonlyRootfs", False),
                   ("CapAdd", ["NET_ADMIN", "NET_BIND_SERVICE", "SYS_ADMIN"]),
                   ("CapDrop", []), ("Binds", ["/var/run/docker.sock:/var/run/docker.sock"]),
                   ("Devices", [{"PathOnHost": "/dev/net/tun"}]),
                   ("PortBindings", {"443/tcp": [{"HostPort": "443"}]}),
                   ("Memory", 0), ("MemorySwap", -1), ("NanoCpus", 0),
                   ("PidsLimit", -1), ("SecurityOpt", []), ("Ulimits", []),
                   ("Tmpfs", {}))
        for field, value in attacks:
            document = exact_container("test")
            document["HostConfig"][field] = value
            with self.subTest(field=field), self.assertRaises(collector.CollectorError):
                collector.validate_container_inspect("test", document, owned("test"), test_cid=CID_TEST)
        document = exact_container("test")
        document["Mounts"] = [{"Type": "bind", "Source": "/tmp", "Destination": "/host"}]
        with self.assertRaises(collector.CollectorError):
            collector.validate_container_inspect("test", document, owned("test"), test_cid=CID_TEST)


class EventAndSemanticControls(unittest.TestCase):
    def test_exact_two_completed_methods_and_semantics_pass(self):
        collector.validate_events(exact_events(), 0, exact_semantics())

    def test_nonzero_exit_refused_even_with_complete_success_events(self):
        for exit_code in (1, 124, -15):
            with self.subTest(exit_code=exit_code), self.assertRaises(collector.CollectorError):
                collector.validate_events(exact_events(), exit_code, exact_semantics())

    def test_missing_duplicate_and_extra_methods_refused(self):
        cases = []
        events = exact_events()
        del events[3:5]
        cases.append(events)
        events = exact_events()
        events[3:3] = copy.deepcopy(events[1:3])
        cases.append(events)
        events = exact_events()
        events[3]["name"] = "test additional method"
        events[4]["name"] = "test additional method"
        cases.append(events)
        events = exact_events()
        events[3]["module"] = "Elixir.Attacker"
        events[4]["module"] = "Elixir.Attacker"
        cases.append(events)
        for events in cases:
            with self.subTest(events=events), self.assertRaises(collector.CollectorError):
                collector.validate_events(events, 0, exact_semantics())

    def test_non_nil_method_state_refused_without_truthiness_coercion(self):
        for state in ("skipped", "excluded", "invalid", "failed", False, 0, "nil", [], {}):
            events = exact_events()
            events[2]["state"] = state
            with self.subTest(state=state), self.assertRaises(collector.CollectorError):
                collector.validate_events(events, 0, exact_semantics())

    def test_suite_integrity_and_event_order_refused_when_incomplete(self):
        cases = [exact_events()[1:], exact_events()[:-1], exact_events() + [exact_events()[-1]],
                 [exact_events()[0], exact_events()[2], exact_events()[1], *exact_events()[3:]],
                 exact_events() + [{"event": "unrecognized_observation"}]]
        for events in cases:
            with self.subTest(events=events), self.assertRaises(collector.CollectorError):
                collector.validate_events(events, 0, exact_semantics())

    def test_suite_statistics_must_report_exact_two_and_no_other_states(self):
        for field, value in (("total", 1), ("total", 3), ("failures", 1), ("skipped", 1),
                             ("excluded", 1), ("invalid", 1), ("total", "2"), ("failures", False)):
            events = exact_events()
            events[-1][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(collector.CollectorError):
                collector.validate_events(events, 0, exact_semantics())

    def test_missing_method_state_or_suite_statistics_refused(self):
        for target, field in ((2, "state"), (-1, "total"), (-1, "failures"),
                              (-1, "skipped"), (-1, "excluded"), (-1, "invalid")):
            events = exact_events()
            del events[target][field]
            with self.subTest(target=target, field=field), self.assertRaises(collector.CollectorError):
                collector.validate_events(events, 0, exact_semantics())

    def test_each_semantic_fact_is_an_independent_obligation(self):
        for receipt_name, fields in exact_semantics().items():
            for field, original in fields.items():
                wrong = not original if isinstance(original, bool) else original + 1 if isinstance(original, int) else "attacker"
                semantics = exact_semantics()
                semantics[receipt_name][field] = wrong
                with self.subTest(receipt=receipt_name, field=field), self.assertRaises(collector.CollectorError):
                    collector.validate_events(exact_events(), 0, semantics)

    def test_type_coercion_cannot_forge_semantic_facts(self):
        for receipt_name, field, value in (
                ("production-DNS-rebinding.json", "publicConnections", True),
                ("production-DNS-rebinding.json", "forbiddenSinkConnections", False),
                ("startup-production-network.json", "coldTokenAdmitted", 1),
                ("startup-production-network.json", "fixtureKeyDirectoryRemoved", 1),
                ("startup-production-network.json", "productionPolicyBypasses", False)):
            semantics = exact_semantics()
            semantics[receipt_name][field] = value
            with self.subTest(receipt=receipt_name, field=field), self.assertRaises(collector.CollectorError):
                collector.validate_events(exact_events(), 0, semantics)

    def test_absent_receipts_and_facts_refused(self):
        for receipt_name, fields in exact_semantics().items():
            semantics = exact_semantics()
            del semantics[receipt_name]
            with self.subTest(receipt=receipt_name), self.assertRaises(collector.CollectorError):
                collector.validate_events(exact_events(), 0, semantics)
            for field in fields:
                semantics = exact_semantics()
                del semantics[receipt_name][field]
                with self.subTest(receipt=receipt_name, field=field), self.assertRaises(collector.CollectorError):
                    collector.validate_events(exact_events(), 0, semantics)


class OwnedCleanupControls(unittest.TestCase):
    def test_cleanup_plan_targets_exact_known_cids_in_dependency_order(self):
        records = [owned("prepare"), owned("test"), owned("pg")]
        plan = collector.cleanup_plan(records)
        expected = []
        for cid in (CID_PG, CID_TEST, CID_PREPARE):
            expected.extend([["docker", "stop", "--time", "2", cid],
                             ["docker", "rm", "--volumes", cid]])
        self.assertEqual(expected, plan)
        self.assertEqual([], collector.cleanup_plan([]))

    def test_cleanup_plan_rejects_duplicate_or_foreign_role_records(self):
        foreign = owned("test")
        foreign.role = "unrelated"
        for records in ([owned("test"), owned("test")], [foreign]):
            with self.subTest(records=records), self.assertRaises(collector.CollectorError):
                collector.cleanup_plan(records)

    def test_registry_requires_matching_reserved_role_image_and_label(self):
        record = owned("test")
        changes = (("name", record.name + "-other"), ("role", "pg"),
                   ("image_id", POSTGRES_CONFIG), ("label", "another-run"))
        for field, value in changes:
            registry = collector.OwnedRegistry()
            registry.reserve(record.name, record.role, record.image_id, record.label)
            arguments = dict(cid=record.cid, name=record.name, role=record.role,
                             image_id=record.image_id, label=record.label)
            arguments[field] = value
            with self.subTest(field=field), self.assertRaises(collector.CollectorError):
                registry.add(**arguments)
            self.assertEqual([], registry.records)
            self.assertEqual(1, len(registry.unresolved))

    def test_registry_retains_exact_identity_after_reservation_and_create(self):
        registry = collector.OwnedRegistry()
        record = owned("test")
        registry.reserve(record.name, record.role, record.image_id, record.label)
        added = registry.add(record.cid, record.name, record.role, record.image_id, record.label)
        self.assertEqual(record.cid, added.cid)
        self.assertEqual(record.image_id, added.image_id)
        self.assertEqual(record.label, added.label)
        self.assertEqual([], registry.unresolved)
        self.assertEqual([record.cid], [item.cid for item in registry.records])

    def test_permission_refusal_is_sticky_and_never_generates_cleanup_commands(self):
        registry = collector.OwnedRegistry()
        record = owned("test")
        registry.reserve(record.name, record.role, record.image_id, record.label)
        registry.add(record.cid, record.name, record.role, record.image_id, record.label)
        registry.refuse(record.cid, "permission denied")
        self.assertEqual("identity_lost", registry.records[0].state)
        with self.assertRaises(collector.CollectorError):
            collector.cleanup_plan(registry.records)
        # Re-admission cannot turn refusal into a new owned record.
        with self.assertRaises(collector.CollectorError):
            registry.add(record.cid, record.name, record.role, record.image_id, record.label)
        self.assertEqual("identity_lost", registry.records[0].state)

    def test_create_response_loss_retains_reserved_name_as_unresolved(self):
        registry = collector.OwnedRegistry()
        record = owned("test")
        registry.reserve(record.name, record.role, record.image_id, record.label)
        registry.creation_unknown(record.name, "create response timed out")
        self.assertEqual([], registry.records)
        self.assertEqual(1, len(registry.unresolved))
        self.assertIn(record.name, repr(registry.unresolved))
        self.assertIn("create response timed out", repr(registry.unresolved))
        # No CID means no name-based stop/rm, enumeration, or PID fallback.
        self.assertEqual([], collector.cleanup_plan(registry.records))
        with self.assertRaises(collector.CollectorError):
            registry.add(record.cid, record.name, record.role, record.image_id, record.label)

    def test_malformed_or_duplicate_cid_never_enters_cleanup_ownership(self):
        for cid in ("", "1" * 12, "a" * 63, "g" * 64, "--all", CID_TEST + "\n"):
            registry = collector.OwnedRegistry()
            record = owned("test")
            registry.reserve(record.name, record.role, record.image_id, record.label)
            with self.subTest(cid=cid), self.assertRaises(collector.CollectorError):
                registry.add(cid, record.name, record.role, record.image_id, record.label)
        registry = collector.OwnedRegistry()
        record = owned("test")
        registry.reserve(record.name, record.role, record.image_id, record.label)
        registry.add(record.cid, record.name, record.role, record.image_id, record.label)
        other = owned("pg")
        registry.reserve(other.name, other.role, other.image_id, other.label)
        with self.assertRaises(collector.CollectorError):
            registry.add(record.cid, other.name, other.role, other.image_id, other.label)

    def test_identity_loss_cannot_be_bypassed_by_cleanup_of_other_owned_records(self):
        lost = owned("test")
        lost.state = "identity_lost"
        for records in ([lost], [owned("pg"), lost], [owned("prepare"), lost]):
            with self.subTest(count=len(records)), self.assertRaises(collector.CollectorError):
                collector.cleanup_plan(records)


class FakeDocker:
    """A strict transcript fake. Every unknown command is an assertion failure."""
    def __init__(self):
        self.calls = []
        self.transcripts = []
        self.documents = {}
        self.fail_create = False
        self.deny_exec = False
        self.exec_response = None
        self.exec_error = None
        self.absence_error = None

    def __call__(self, argv, timeout, input_bytes):
        self.calls.append(list(argv))
        self.transcripts.append((list(argv), timeout, input_bytes))
        if argv[:2] == ["docker", "create"]:
            if self.fail_create:
                raise collector.CollectorError("lost create response")
            role = next(value.split("=", 1)[1] for value in argv if value.startswith("mixer.identity.role="))
            label = next(value.split("=", 1)[1] for value in argv if value.startswith("mixer.identity.run="))
            document = exact_container(role)
            document["Name"] = "/" + argv[argv.index("--name") + 1]
            document["Config"]["Labels"]["mixer.identity.run"] = label
            document["State"] = {"Running": False, "OOMKilled": False}
            self.documents[document["Id"]] = document
            return 0, (document["Id"] + "\n").encode(), b""
        if argv[:3] == ["docker", "container", "inspect"] and len(argv) == 4:
            cid = argv[3]
            if cid not in self.documents:
                return 1, b"[]", self.absence_error or ("Error: No such container: " + cid).encode()
            return 0, json.dumps([self.documents[cid]]).encode(), b""
        if argv[:2] == ["docker", "exec"]:
            cid = next((value for value in argv if value in self.documents), None)
            if cid is None:
                raise AssertionError("exec did not use a known exact CID")
            if self.exec_error is not None:
                raise self.exec_error
            return self.exec_response or ((1, b"", b"permission denied") if self.deny_exec else (0, b"fixture output", b""))
        if argv[:4] == ["docker", "stop", "--time", "2"] and len(argv) == 5:
            self.documents[argv[4]]["State"]["Running"] = False
            return 0, argv[4].encode(), b""
        if argv[:2] == ["docker", "logs"] and len(argv) == 3 and argv[2] in self.documents:
            return 0, b"synthetic retained logs", b""
        if argv[:3] == ["docker", "rm", "--volumes"] and len(argv) == 4:
            del self.documents[argv[3]]
            return 0, argv[3].encode(), b""
        raise AssertionError("unexpected command (no execution performed): " + repr(argv))


class CollectorMethodWiringControls(unittest.TestCase):
    """Exercise method wiring with a transcript fake; outer run/finally separate."""
    def make_collector(self, directory, runner, subject_class=None):
        root = Path(directory) / "repository"
        root.mkdir()
        with mock.patch.dict("os.environ", {"GITHUB_RUN_ID": "100", "GITHUB_RUN_ATTEMPT": "1"}):
            return (subject_class or collector.Collector)(root, Path(directory) / "evidence", "a" * 40, runner=runner)

    def test_prepare_create_and_inspection_use_explicit_bridge(self):
        # Docker's retained CI response resolves its default network to bridge.
        fake = FakeDocker()
        with tempfile.TemporaryDirectory(prefix="identity-controls-") as directory:
            subject = self.make_collector(directory, fake)
            record = subject.create("prepare")
            create = next(argv for argv in fake.calls if argv[:2] == ["docker", "create"])
            self.assertEqual("bridge", create[create.index("--network") + 1])
            self.assertEqual("bridge", fake.documents[record.cid]["HostConfig"]["NetworkMode"])
            document = copy.deepcopy(fake.documents[record.cid])
            document["HostConfig"]["NetworkMode"] = "default"
            with self.assertRaises(collector.CollectorError):
                collector.validate_container_inspect("prepare", document, record)
            self.assertTrue(subject.cleanup())
            self.assertEqual({}, fake.documents)

    def test_copy_in_uses_exact_tar_stdin_cid_workdir_and_cleared_environment(self):
        expected_env = {
            "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            "LANG": "C.UTF-8", "HOME": "/workspace/home", "MIX_ENV": "test",
            "MIX_HOME": "/workspace/tooling/mix", "MIX_REBAR3": "/workspace/tooling/rebar3",
            "HEX_HOME": "/workspace/tooling/hex", "XDG_CACHE_HOME": "/workspace/cache",
            "ERL_CRASH_DUMP": "/workspace/evidence/erl_crash.dump", "ERL_CRASH_DUMP_SECONDS": "0",
        }
        data = collector.source_tar({"hosted/lib/a.ex": b"frozen transfer fixture"})
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:") as value:
            member = value.getmembers()[0]
            self.assertEqual((0, 0, 0o644, 0), (member.uid, member.gid, member.mode, member.mtime))
        for role in ("prepare", "test"):
            fake = FakeDocker()
            with self.subTest(role=role), tempfile.TemporaryDirectory(prefix="identity-controls-") as directory:
                subject = self.make_collector(directory, fake)
                record = subject.create(role)
                before = copy.deepcopy(fake.documents[record.cid])
                first = len(fake.calls)
                subject.copy_in(record, data)
                expected = ["docker", "exec", "-i", "--workdir", "/workspace"]
                expected += [part for key, value in sorted(expected_env.items()) for part in ("--env", key + "=" + value)]
                expected += [record.cid, "/usr/bin/env", "-i", *[key + "=" + value for key, value in sorted(expected_env.items())],
                             "/usr/bin/tar", "--extract", "--file", "-", "--directory", "/workspace",
                             "--no-same-owner", "--no-same-permissions"]
                self.assertEqual([["docker", "container", "inspect", record.cid], expected], fake.calls[first:])
                self.assertEqual(data, fake.transcripts[-1][2])
                self.assertLessEqual(fake.transcripts[-1][1], 30)
                self.assertEqual(before, fake.documents[record.cid])
                self.assertFalse(any(argv[:2] == ["docker", "cp"] for argv in fake.calls))
                log = json.loads((subject.output / "logs" / f"{subject.command_number:04d}.json").read_text())
                self.assertEqual(str(subject.root), log["cwd"])
                self.assertEqual((len(data), hashlib.sha256(data).hexdigest()), (log["stdin_bytes"], log["stdin_sha256"]))
                self.assertTrue(subject.cleanup())

    def test_copy_in_preserves_executable_bytes_without_owner_or_permission_restore(self):
        memory = io.BytesIO()
        with tarfile.open(fileobj=memory, mode="w", format=tarfile.USTAR_FORMAT) as value:
            member = tarfile.TarInfo("tooling/rebar3")
            member.size, member.mode, member.uid, member.gid = 7, 0o755, 0, 0
            value.addfile(member, io.BytesIO(b"fixture"))
        data = memory.getvalue()
        fake = FakeDocker()
        with tempfile.TemporaryDirectory(prefix="identity-controls-") as directory:
            subject = self.make_collector(directory, fake)
            record = subject.create("test")
            subject.copy_in(record, data)
            self.assertEqual(data, fake.transcripts[-1][2])
            self.assertIn("--no-same-owner", fake.calls[-1])
            self.assertIn("--no-same-permissions", fake.calls[-1])
            self.assertTrue(subject.cleanup())

    def test_exec_defaults_keep_original_workdirs_and_closed_override_refuses_before_inspect(self):
        fake = FakeDocker()
        with tempfile.TemporaryDirectory(prefix="identity-controls-") as directory:
            subject = self.make_collector(directory, fake)
            test = subject.create("test")
            pg = subject.create("pg", test_cid=test.cid)
            for record, directory_name in ((test, "/workspace/hosted"), (pg, "/")):
                subject.execute(record, ["fixture-command"])
                self.assertEqual(["docker", "exec", "--workdir", directory_name], fake.calls[-1][:4])
                self.assertIsNone(fake.transcripts[-1][2])
            for record, directory_name in ((test, "/tmp"), (test, "/workspace/../tmp"), (test, "/workspace/hosted"), (pg, "/workspace")):
                first = len(fake.calls)
                with self.subTest(role=record.role, directory=directory_name), self.assertRaises(collector.CollectorError):
                    subject.execute(record, ["fixture-command"], workdir=directory_name)
                self.assertEqual(first, len(fake.calls))
                self.assertEqual("owned", record.state)
            self.assertTrue(subject.cleanup())

    def test_invalid_copy_in_archive_is_refused_before_any_container_command(self):
        entries = [
            [(name, tarfile.REGTYPE, b"x", "")] for name in
            ("/outside", "../outside", "hosted/../outside", "hosted\\outside", "hosted//a", "./hosted/a")
        ]
        entries += [[("hosted/a", kind, b"", "hosted/b")] for kind in
                    (tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.CHRTYPE, tarfile.BLKTYPE, tarfile.FIFOTYPE, tarfile.DIRTYPE)]
        entries += [[("hosted/a", tarfile.REGTYPE, b"x", ""), ("hosted/a", tarfile.REGTYPE, b"x", "")]]
        data = collector.source_tar({"hosted/a": b"body"})
        invalid = [b"", b"not a tar", data[:515], data + b"trailing data", data[:1024]]
        for rows in entries:
            with archive(rows) as value:
                invalid.append(value.fileobj.getvalue())
        fake = FakeDocker()
        with tempfile.TemporaryDirectory(prefix="identity-controls-") as directory:
            subject = self.make_collector(directory, fake)
            record = subject.create("prepare")
            for index, value in enumerate(invalid):
                first = len(fake.calls)
                with self.subTest(index=index), self.assertRaises(collector.CollectorError):
                    subject.copy_in(record, value)
                self.assertEqual(first, len(fake.calls))
                self.assertEqual("owned", record.state)
            first = len(fake.calls)
            with mock.patch.object(collector, "MAX_ARCHIVE_BYTES", len(data) - 1), self.assertRaises(collector.CollectorError):
                subject.copy_in(record, data)
            self.assertEqual(first, len(fake.calls))
            self.assertTrue(subject.cleanup())

    def test_copy_in_refuses_extended_metadata_special_modes_and_stdin_types(self):
        invalid = [None, "not bytes", bytearray(b"not immutable")]
        for mode, tar_format, headers, name in ((0o4755, tarfile.USTAR_FORMAT, {}, "hosted/a"),
                                                (0o644, tarfile.PAX_FORMAT, {"comment": "unreviewed"}, "hosted/a"),
                                                (0o644, tarfile.GNU_FORMAT, {}, "hosted/" + "a" * 150)):
            memory = io.BytesIO()
            with tarfile.open(fileobj=memory, mode="w", format=tar_format) as value:
                member = tarfile.TarInfo(name)
                member.size, member.mode, member.pax_headers = 1, mode, headers
                value.addfile(member, io.BytesIO(b"x"))
            invalid.append(memory.getvalue())
        fake = FakeDocker()
        with tempfile.TemporaryDirectory(prefix="identity-controls-") as directory:
            subject = self.make_collector(directory, fake)
            record = subject.create("prepare")
            for index, value in enumerate(invalid):
                first = len(fake.calls)
                with self.subTest(index=index), self.assertRaises(collector.CollectorError):
                    subject.copy_in(record, value)
                self.assertEqual(first, len(fake.calls))
            self.assertTrue(subject.cleanup())

    def test_copy_in_permission_refusal_preserves_sticky_custody_and_no_cleanup_retry(self):
        for stderr in (b"permission denied", b"operation not permitted", b"access denied"):
            fake = FakeDocker()
            fake.exec_response = (1, b"", stderr)
            with self.subTest(stderr=stderr), tempfile.TemporaryDirectory(prefix="identity-controls-") as directory:
                subject = self.make_collector(directory, fake)
                record = subject.create("prepare")
                with self.assertRaises(collector.CollectorError):
                    subject.copy_in(record, collector.source_tar({"hosted/a": b"x"}))
                self.assertEqual("identity_lost", record.state)
                first = len(fake.calls)
                self.assertFalse(subject.cleanup())
                self.assertEqual(first, len(fake.calls))
                self.assertEqual("FAILED-unknown-or-incomplete", subject.state["cleanup"]["status"])

    def test_copy_in_identity_loss_refuses_exec_and_never_retries_cleanup(self):
        fake = FakeDocker()
        with tempfile.TemporaryDirectory(prefix="identity-controls-") as directory:
            subject = self.make_collector(directory, fake)
            record = subject.create("prepare")
            fake.documents[record.cid]["Name"] = "/foreign-container"
            first = len(fake.calls)
            with self.assertRaises(collector.CollectorError):
                subject.copy_in(record, collector.source_tar({"hosted/a": b"x"}))
            self.assertEqual([["docker", "container", "inspect", record.cid]], fake.calls[first:])
            self.assertEqual("identity_lost", record.state)
            first = len(fake.calls)
            self.assertFalse(subject.cleanup())
            with self.assertRaises(collector.CollectorError):
                subject.copy_in(record, collector.source_tar({"hosted/a": b"x"}))
            self.assertEqual(first, len(fake.calls))

    def test_run_finally_freezes_tar_failure_before_exact_owned_cleanup(self):
        fake = FakeDocker()
        fake.exec_response = (2, b"", b"tar: fixture extraction failure")
        testcase = self
        class FaultingCollector(collector.Collector):
            def collect(self):
                record = self.create("prepare")
                self.copy_in(record, collector.source_tar({"hosted/a": b"x"}))

            def cleanup(self):
                testcase.assertTrue(self.state["primary_outcome_frozen"])
                testcase.assertEqual("FAILED-or-partial", self.state["status"])
                return super().cleanup()
        with tempfile.TemporaryDirectory(prefix="identity-controls-") as directory:
            subject = self.make_collector(directory, fake, FaultingCollector)
            self.assertEqual(1, subject.run())
            self.assertEqual("FAILED-or-partial", subject.state["status"])
            self.assertEqual("verified-exact-created-IDs-absent", subject.state["cleanup"]["status"])
            self.assertEqual({}, fake.documents)
            self.assertEqual(1, sum(argv[:2] == ["docker", "exec"] for argv in fake.calls))
            self.assertTrue((subject.output / "artifact-manifest.json").is_file())
            self.assertFalse((subject.output / ".scratch").exists())

    def test_copy_in_timeout_and_output_overflow_fail_without_transfer_retry(self):
        for failure in ("injected-timeout", "stdout-overflow"):
            fake = FakeDocker()
            if failure == "injected-timeout":
                fake.exec_error = collector.CollectorError("command timeout/output incomplete")
            else:
                fake.exec_response = (0, b"x" * (collector.MAX_COMMAND_BYTES + 1), b"")
            class FaultingCollector(collector.Collector):
                def collect(self):
                    record = self.create("prepare")
                    self.copy_in(record, collector.source_tar({"hosted/a": b"x"}))
            with self.subTest(failure=failure), tempfile.TemporaryDirectory(prefix="identity-controls-") as directory:
                subject = self.make_collector(directory, fake, FaultingCollector)
                self.assertEqual(1, subject.run())
                self.assertEqual("FAILED-or-partial", subject.state["status"])
                self.assertTrue(subject.state["primary_outcome_frozen"])
                self.assertEqual("verified-exact-created-IDs-absent", subject.state["cleanup"]["status"])
                self.assertEqual({}, fake.documents)
                self.assertEqual(1, sum(argv[:2] == ["docker", "exec"] for argv in fake.calls))
                command_logs = [json.loads(path.read_text()) for path in (subject.output / "logs").glob("*.json")]
                transfer = next(row for row in command_logs if row["argv"][:2] == ["docker", "exec"])
                self.assertFalse(transfer["stdout_complete"])
                self.assertFalse(transfer["stderr_complete"])
                if failure == "stdout-overflow":
                    self.assertTrue(transfer["overflow"])
                self.assertFalse((subject.output / ".scratch").exists())

    def test_bounded_command_stdin_closes_at_exact_input_eof_without_a_process(self):
        class Pipe:
            def __init__(self, number):
                self.number, self.closed = number, False

            def fileno(self):
                return self.number

            def close(self):
                self.closed = True

        process = SimpleNamespace(stdin=Pipe(101), stdout=Pipe(102), stderr=Pipe(103), returncode=0)
        waited_after_eof = []
        process.wait = lambda **options: waited_after_eof.append(process.stdin.closed)
        process.poll = lambda: 0

        class Selector:
            def __init__(self):
                self.registered = {}

            def __enter__(self):
                return self

            def __exit__(self, *error):
                return False

            def register(self, pipe, events, kind):
                self.registered[pipe] = SimpleNamespace(fileobj=pipe, data=kind)

            def unregister(self, pipe):
                del self.registered[pipe]

            def get_map(self):
                return self.registered

            def select(self, timeout):
                return [(key, 0) for key in list(self.registered.values())]

        data = collector.source_tar({"hosted/a": b"x" * 131073})
        sent = bytearray()
        def send(number, chunk):
            self.assertEqual(101, number)
            count = min(32768, len(chunk))
            sent.extend(chunk[:count])
            return count
        fake = FakeDocker()
        with tempfile.TemporaryDirectory(prefix="identity-controls-") as directory:
            subject = self.make_collector(directory, fake)
            subject.runner = None
            with mock.patch.object(collector.subprocess, "Popen", return_value=process) as spawn, \
                    mock.patch.object(collector.selectors, "DefaultSelector", Selector), \
                    mock.patch.object(collector.os, "set_blocking"), \
                    mock.patch.object(collector.os, "read", return_value=b""), \
                    mock.patch.object(collector.os, "write", side_effect=send):
                self.assertEqual((b"", b"", 0), subject.command(["fake-bounded-stdin"], 30, input_bytes=data))
            self.assertEqual(data, bytes(sent))
            self.assertEqual([True], waited_after_eof)
            self.assertTrue(all(pipe.closed for pipe in (process.stdin, process.stdout, process.stderr)))
            self.assertEqual(str(subject.root), str(spawn.call_args.kwargs["cwd"]))
            self.assertEqual(collector.subprocess.PIPE, spawn.call_args.kwargs["stdin"])

    def test_lost_create_response_stays_unresolved_and_never_uses_name_cleanup(self):
        fake = FakeDocker()
        fake.fail_create = True
        with tempfile.TemporaryDirectory(prefix="identity-controls-") as directory:
            subject = self.make_collector(directory, fake)
            with self.assertRaises(collector.CollectorError):
                subject.create("test")
            before_cleanup = len(fake.calls)
            self.assertFalse(subject.cleanup())
            self.assertEqual(before_cleanup, len(fake.calls))
            self.assertEqual(1, len(subject.registry.unresolved))
            self.assertEqual("unknown", subject.registry.unresolved[0]["state"])
            self.assertEqual("FAILED-unknown-or-incomplete", subject.state["cleanup"]["status"])

    def test_exec_permission_refusal_is_sticky_and_cleanup_never_retries_it(self):
        fake = FakeDocker()
        with tempfile.TemporaryDirectory(prefix="identity-controls-") as directory:
            subject = self.make_collector(directory, fake)
            record = subject.create("test")
            fake.deny_exec = True
            with self.assertRaises(collector.CollectorError):
                subject.execute(record, ["fixture-command"])
            self.assertEqual("identity_lost", record.state)
            before_cleanup = len(fake.calls)
            self.assertFalse(subject.cleanup())
            self.assertEqual(before_cleanup, len(fake.calls))
            self.assertEqual("FAILED-unknown-or-incomplete", subject.state["cleanup"]["status"])

    def test_post_remove_ambiguous_absence_is_sticky_without_retry(self):
        fake = FakeDocker()
        with tempfile.TemporaryDirectory(prefix="identity-controls-") as directory:
            subject = self.make_collector(directory, fake)
            record = subject.create("test")
            fake.absence_error = b"Error: No such container; permission denied"
            self.assertFalse(subject.cleanup())
            self.assertEqual("identity_lost", record.state)
            before_second_cleanup = len(fake.calls)
            self.assertFalse(subject.cleanup())
            self.assertEqual(before_second_cleanup, len(fake.calls))
            self.assertEqual("FAILED-unknown-or-incomplete", subject.state["cleanup"]["status"])

    def test_cleanup_uses_only_retained_cids_and_observes_exact_absence(self):
        fake = FakeDocker()
        with tempfile.TemporaryDirectory(prefix="identity-controls-") as directory:
            subject = self.make_collector(directory, fake)
            test = subject.create("test")
            pg = subject.create("pg", test_cid=test.cid)
            before_cleanup = len(fake.calls)
            self.assertTrue(subject.cleanup())
            actions = [argv for argv in fake.calls[before_cleanup:] if argv[1] in ("stop", "rm")]
            self.assertEqual([["docker", "stop", "--time", "2", pg.cid],
                              ["docker", "rm", "--volumes", pg.cid],
                              ["docker", "stop", "--time", "2", test.cid],
                              ["docker", "rm", "--volumes", test.cid]], actions)
            self.assertEqual({}, fake.documents)
            self.assertEqual(["removed", "removed"], [row.state for row in subject.registry.records])
            self.assertEqual("verified-exact-created-IDs-absent", subject.state["cleanup"]["status"])
            self.assertFalse(subject.state["cleanup"]["container_teardown_is_product_lifecycle_proof"])

    def test_cancellation_stops_new_work_but_permits_known_cid_cleanup(self):
        fake = FakeDocker()
        with tempfile.TemporaryDirectory(prefix="identity-controls-") as directory:
            subject = self.make_collector(directory, fake)
            subject.create("test")
            subject.cancelled = True
            before_refusal = len(fake.calls)
            with self.assertRaises(collector.CollectorError):
                subject.command(["would-initiate-work"])
            self.assertEqual(before_refusal, len(fake.calls))
            self.assertTrue(subject.cleanup())

    def test_run_finally_freezes_each_phase_fault_before_exact_cid_cleanup(self):
        phases = (("static", ()), ("bootstrap", ("prepare",)),
                  ("dependencies", ("prepare",)), ("restore", ("test",)),
                  ("database", ("test", "pg")), ("compile", ("test", "pg")),
                  ("two-tests", ("test", "pg")), ("evidence", ("test", "pg")))
        for phase, roles in phases:
            fake = FakeDocker()
            testcase = self
            class FaultingCollector(collector.Collector):
                def collect(self):
                    for role in roles:
                        self.create(role, test_cid=CID_TEST if role == "pg" else None)
                    raise collector.CollectorError("injected " + phase)

                def cleanup(self):
                    testcase.assertTrue(self.state["primary_outcome_frozen"])
                    testcase.assertEqual("injected " + phase, self.state["primary_failure"]["message"])
                    return super().cleanup()

            with self.subTest(phase=phase), tempfile.TemporaryDirectory(prefix="identity-controls-") as directory:
                subject = self.make_collector(directory, fake, FaultingCollector)
                self.assertEqual(1, subject.run())
                self.assertEqual("FAILED-or-partial", subject.state["status"])
                self.assertEqual("injected " + phase, subject.state["primary_failure"]["message"])
                self.assertEqual({}, fake.documents)
                self.assertTrue(all(row.state == "removed" for row in subject.registry.records))
                self.assertTrue((subject.output / "artifact-manifest.json").is_file())
                self.assertFalse((subject.output / ".scratch").exists())

    def test_run_finally_preserves_create_uncertainty_and_permission_refusal_as_failure(self):
        for failure in ("create-unknown", "exec-denied"):
            fake = FakeDocker()
            fake.fail_create = failure == "create-unknown"
            fake.deny_exec = failure == "exec-denied"
            class FaultingCollector(collector.Collector):
                def collect(self):
                    record = self.create("test")
                    self.execute(record, ["fixture-command"])
            with self.subTest(failure=failure), tempfile.TemporaryDirectory(prefix="identity-controls-") as directory:
                subject = self.make_collector(directory, fake, FaultingCollector)
                self.assertEqual(1, subject.run())
                self.assertEqual("FAILED-cleanup-unknown-or-incomplete", subject.state["status"])
                self.assertIn("primary_failure", subject.state)
                self.assertTrue(subject.state["primary_outcome_frozen"])
                self.assertFalse(any(argv[1] in ("stop", "rm") for argv in fake.calls))
                self.assertTrue((subject.output / "artifact-manifest.json").is_file())

    def test_run_finally_handles_keyboard_cancellation_with_bounded_owned_cleanup(self):
        fake = FakeDocker()
        class CancelledCollector(collector.Collector):
            def collect(self):
                self.create("test")
                self.cancelled = True
                raise KeyboardInterrupt("injected cancellation")
        with tempfile.TemporaryDirectory(prefix="identity-controls-") as directory:
            subject = self.make_collector(directory, fake, CancelledCollector)
            self.assertEqual(1, subject.run())
            self.assertEqual("KeyboardInterrupt", subject.state["primary_failure"]["type"])
            self.assertEqual("FAILED-cancelled", subject.state["status"])
            self.assertEqual({}, fake.documents)
            self.assertTrue((subject.output / "artifact-manifest.json").is_file())

    def test_output_overflow_is_recorded_and_exhausted_aggregate_budget_starts_no_command(self):
        for mode in ("command-overflow", "aggregate-overflow"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory(prefix="identity-controls-") as directory:
                calls = []
                def fake(argv, timeout, input_bytes):
                    calls.append(argv)
                    return (0, b"123456789", b"")
                subject = self.make_collector(directory, fake)
                if mode == "aggregate-overflow":
                    subject.log_bytes = collector.MAX_LOG_BYTES - 1
                with self.assertRaises(collector.CollectorError):
                    subject.command(["fixture-command"], limit=8 if mode == "command-overflow" else 16)
                if mode == "command-overflow":
                    row = json.loads((subject.output / "logs/0001.json").read_text())
                    self.assertIn("failure", row)
                    self.assertTrue(row["overflow"])
                    self.assertFalse(row["stdout_complete"])
                    self.assertFalse(row["stderr_complete"])
                    self.assertEqual([["fixture-command"]], calls)
                else:
                    self.assertEqual([], calls)
                    self.assertFalse((subject.output / "logs/0001.json").exists())
                state = json.loads((subject.output / "state.json").read_text())
                self.assertEqual(1 if mode == "command-overflow" else 0, state["command_number"])


    def _amendment_preflight_subject(self, directory, metadata):
        repository = COLLECTOR_PATH.resolve().parents[2]
        # These boundary controls stub source admission below. The independent
        # SourceControls keep the complete 177-source decision unchanged; a
        # protected dirty store in the development tree is not a Git fixture.
        subject = self.make_collector(directory, lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("real command forbidden")))
        controls = ["hosted/scripts/test-identity-network.py", "hosted/scripts/test_identity_network_collector.py", "docs/hosted-identity-production-network-ci-contract.md", ".github/workflows/identity-network.yml"]
        for path in controls:
            target = subject.root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((repository / path).read_bytes())
        def blobs(paths):
            return {path: metadata[path] if path.startswith("verification/") else (repository / path).read_bytes() for path in paths}
        subject.git_blobs = blobs
        calls = []
        def command(argv, *args, **kwargs):
            calls.append(argv)
            if argv == ["git", "--no-replace-objects", "rev-parse", "HEAD"]:
                return (subject.sha.encode(), b"", 0)
            if argv == ["git", "--version"] or argv[:2] == ["docker", "version"] or argv[:2] == ["docker", "pull"]:
                return (b"{}", b"", 0)
            if argv[:3] == ["docker", "image", "inspect"]:
                return (json.dumps([exact_image("pg" if argv[-1] == POSTGRES_REF else "test")]).encode(), b"", 0)
            raise AssertionError("unexpected command in pure collector preflight: " + repr(argv))
        subject.command = command
        return subject, calls

    def test_collect_refuses_missing_amendment_before_any_image_or_create_operation(self):
        metadata = exact_metadata()
        metadata.pop("verification/identity-network-image-amendment-v1/metadata/packet-manifest.json")
        with tempfile.TemporaryDirectory(prefix="identity-controls-") as directory:
            subject, calls = self._amendment_preflight_subject(directory, metadata)
            with mock.patch.dict("os.environ", {"GITHUB_ACTIONS": "true", "RUNNER_OS": "Linux", "RUNNER_ARCH": "X64"}, clear=True), \
                    mock.patch.object(collector.os, "uname", return_value=collector.os.uname_result(("Linux", "control", "0", "0", "x86_64"))), \
                    mock.patch.object(collector, "validate_source_manifest", return_value=collector.FROZEN_MANIFEST), \
                    mock.patch.object(subject, "create", side_effect=AssertionError("create before metadata admission")) as create:
                with self.assertRaisesRegex(KeyError, "metadata/packet-manifest.json"):
                    subject.collect()
            self.assertFalse(create.called)
            self.assertFalse(any(argv[0] == "docker" for argv in calls))

    def test_collect_requires_actual_prepare_result_before_bootstrap(self):
        with tempfile.TemporaryDirectory(prefix="identity-controls-") as directory:
            subject, calls = self._amendment_preflight_subject(directory, exact_execution_metadata())
            prepared = owned("prepare")
            inspected = {"Config": {"Env": [key + "=" + value for key, value in collector.BASE_ENV.items()]}}
            with mock.patch.dict("os.environ", {"GITHUB_ACTIONS": "true", "RUNNER_OS": "Linux", "RUNNER_ARCH": "X64"}, clear=True), \
                    mock.patch.object(collector.os, "uname", return_value=collector.os.uname_result(("Linux", "control", "0", "0", "x86_64"))), \
                    mock.patch.object(collector.os, "readlink", return_value="net:[100]"), \
                    mock.patch.object(collector, "validate_source_manifest", return_value=collector.FROZEN_MANIFEST), \
                    mock.patch.object(subject, "create", return_value=prepared) as create, \
                    mock.patch.object(subject, "inspect", return_value=inspected), \
                    mock.patch.object(subject, "docker"), mock.patch.object(subject, "copy_in"), \
                    mock.patch.object(subject, "observe_mounts", return_value=exact_mounts("prepare")), \
                    mock.patch.object(subject, "execute", return_value=(b"IDENTITY_JSON={}\n", b"", 0)) as execute:
                with self.assertRaisesRegex(collector.CollectorError, "prerequisite result incomplete"):
                    subject.collect()
            self.assertEqual([mock.call("prepare")], create.call_args_list)
            self.assertEqual([mock.call(prepared, ["/usr/local/bin/elixir", "/workspace/collector-prerequisites.exs"])], execute.call_args_list)
            self.assertFalse((subject.output / "bootstrap-plan.json").exists())


    def test_collect_requires_v2_execution_seal_before_any_image_operation(self):
        metadata = exact_execution_metadata()
        metadata.pop("verification/identity-network-image-amendment-v2/metadata/packet-manifest.json")
        with tempfile.TemporaryDirectory(prefix="identity-controls-") as directory:
            subject, calls = self._amendment_preflight_subject(directory, metadata)
            with mock.patch.dict("os.environ", {"GITHUB_ACTIONS": "true", "RUNNER_OS": "Linux", "RUNNER_ARCH": "X64"}, clear=True), \
                    mock.patch.object(collector.os, "uname", return_value=collector.os.uname_result(("Linux", "control", "0", "0", "x86_64"))), \
                    mock.patch.object(collector, "validate_source_manifest", return_value=collector.FROZEN_MANIFEST), \
                    mock.patch.object(subject, "create", side_effect=AssertionError("create before v2 seal")) as create:
                with self.assertRaisesRegex(KeyError, "v2/metadata/packet-manifest.json"):
                    subject.collect()
            self.assertFalse(create.called)
            self.assertFalse(any(argv[0] == "docker" for argv in calls))

    def test_mount_observation_uses_exact_owned_helper_with_small_timeout_and_output_bound(self):
        for role in ("prepare", "test"):
            with tempfile.TemporaryDirectory(prefix="identity-controls-") as directory:
                subject = self.make_collector(directory, lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("real command forbidden")))
                value = exact_mounts(role)
                output = b"IDENTITY_JSON=" + json.dumps(value).encode() + b"\n"
                with mock.patch.object(subject, "execute", return_value=(output, b"", 0)) as execute:
                    self.assertEqual(value, subject.observe_mounts(owned(role)))
                execute.assert_called_once_with(owned(role), ["/usr/local/bin/elixir", "/workspace/collector-mounts.exs", role], 15, limit=65536)
                self.assertEqual(value, json.loads((subject.output / (role + "-mount-policy.json")).read_bytes()))
                with mock.patch.object(subject, "execute", return_value=(b"IDENTITY_JSON={}\n", b"", 0)):
                    with self.assertRaises(collector.CollectorError):
                        subject.observe_mounts(owned(role))


class BudgetAndCommandControls(unittest.TestCase):
    def test_phase_deadline_leaves_cleanup_reserve_and_never_extends_requested_bound(self):
        now = [620.0]
        value = collector.Budget(start=0.0, clock=lambda: now[0], total=660, reserve=30)
        allowed = value.remaining(15)
        self.assertGreater(allowed, 0)
        self.assertLessEqual(allowed, 10)
        now[0] = 630.0
        with self.assertRaises(collector.CollectorError):
            value.remaining(1)
        self.assertLessEqual(value.remaining(15, cleanup=True), 15)
        now[0] = 660.0
        with self.assertRaises(collector.CollectorError):
            value.remaining(1, cleanup=True)

    def test_invalid_phase_bounds_are_not_valid_timeouts(self):
        for requested in (0, -1, float("inf"), float("nan"), True):
            value = collector.Budget(start=0.0, clock=lambda: 0.0, total=660, reserve=30)
            with self.subTest(requested=requested), self.assertRaises(collector.CollectorError):
                value.remaining(requested)

    def test_complete_zero_exit_output_at_cap_passes(self):
        collector.validate_command_result(0, b"abcd", b"efgh", limit=8)

    def test_output_overflow_nonzero_and_oom_refused(self):
        for returncode, stdout, stderr, oom in ((0, b"123456789", b"", False),
                                               (0, b"12345", b"6789", False),
                                               (1, b"", b"", False),
                                               (124, b"partial", b"", False),
                                               (0, b"", b"", True)):
            with self.subTest(returncode=returncode, oom=oom), self.assertRaises(collector.CollectorError):
                collector.validate_command_result(returncode, stdout, stderr, limit=8, oom=oom)


if __name__ == "__main__":
    signal.alarm(50)
    unittest.main(verbosity=2)
