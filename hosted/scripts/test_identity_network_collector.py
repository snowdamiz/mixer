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
SELECTED_DIGEST = "8d0139c8c64e02f29f42a96384661f60dd7b724fa5fb4d5f54f6e7c1b7b78cd3"
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


def archive(entries, *, mtimes=None):
    """Build headers in memory only; entries are (name,type,payload,linkname)."""
    memory = io.BytesIO()
    with tarfile.open(fileobj=memory, mode="w") as out:
        for name, kind, payload, linkname in entries:
            info = tarfile.TarInfo(name)
            info.type = kind
            info.linkname = linkname
            info.size = len(payload) if kind == tarfile.REGTYPE else 0
            info.mtime = (mtimes or {}).get(name, 0)
            out.addfile(info, io.BytesIO(payload) if kind == tarfile.REGTYPE else None)
    memory.seek(0)
    return tarfile.open(fileobj=memory, mode="r:")


class SourceControls(unittest.TestCase):
    def test_frozen_source_has_independent_contract_root_and_lock(self):
        self.assertEqual(178, len(collector.FROZEN_MANIFEST))
        self.assertEqual(SELECTED_DIGEST, canonical_digest(collector.FROZEN_MANIFEST))
        self.assertEqual(177, len(collector.PREDECESSOR_MANIFEST))
        self.assertEqual(PRODUCT_DIGEST, canonical_digest(collector.PREDECESSOR_MANIFEST))
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
            collector.validate_source_manifest(value, expected_digest=canonical_digest(value), expected_count=178)

    def test_manifest_structure_cannot_be_authorized_by_its_own_digest(self):
        for path in ("/hosted/escape.ex", "hosted/../escape.ex", "hosted\\escape.ex", "hosted//alias.ex", "outside.ex"):
            value = copy.deepcopy(collector.FROZEN_MANIFEST)
            metadata = value.pop("hosted/.formatter.exs")
            value[path] = metadata
            with self.subTest(path=path), self.assertRaises(collector.CollectorError):
                collector.validate_source_manifest(value, expected_digest=canonical_digest(value), expected_count=178)
        for metadata in ({"bytes": -1, "sha256": "a" * 64},
                         {"bytes": True, "sha256": "a" * 64},
                         {"bytes": 1, "sha256": "g" * 64},
                         {"bytes": 1, "sha256": "a" * 63}):
            value = copy.deepcopy(collector.FROZEN_MANIFEST)
            value["hosted/.formatter.exs"] = metadata
            with self.subTest(metadata=metadata), self.assertRaises(collector.CollectorError):
                collector.validate_source_manifest(value, expected_digest=canonical_digest(value), expected_count=178)

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


def exact_fixture_metadata():
    values = exact_execution_metadata()
    root = COLLECTOR_PATH.resolve().parents[2]
    base = "verification/identity-network-fixture-amendment-v1/metadata/"
    packet = json.loads((root / base / "packet-manifest.json").read_bytes())
    for path in ["packet-manifest.json", *packet["files"]]:
        values[base + path] = (root / base / path).read_bytes()
    return values


def exact_format_metadata():
    values = exact_fixture_metadata()
    root = COLLECTOR_PATH.resolve().parents[2]
    base = collector.FORMAT_BASE
    packet = json.loads((root / base / "packet-manifest.json").read_bytes())
    for path in ["packet-manifest.json", *packet["files"]]:
        values[base + path] = (root / base / path).read_bytes()
    return values


class FormatAmendmentControls(unittest.TestCase):
    def test_exact_format_only_source_and_helpers_pass(self):
        values = exact_format_metadata()
        result = collector.validate_format_metadata(values)
        self.assertEqual(SELECTED_DIGEST, result["selected"]["source_digest_sha256"])
        self.assertEqual(collector.FIXTURE_SOURCE_DIGEST, result["predecessor"]["source_digest_sha256"])
        self.assertEqual(collector.literal_helper_rows(), result["literal_helpers"])
        root = COLLECTOR_PATH.resolve().parents[2]
        for path in ["hosted/test/mixer_hosted/identity/tls_fixture_lifecycle_control_test.exs", "hosted/test/support/identity_tls_fixture.ex", "hosted/mix.lock", *["hosted/" + name for name in collector.TEST_ROOTS]]:
            row = collector.FROZEN_MANIFEST[path]
            body = (root / path).read_bytes()
            self.assertEqual(row, {"bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()})
        self.assertEqual(collector.FIXTURE_MANIFEST["hosted/test/support/identity_tls_fixture.ex"], collector.FROZEN_MANIFEST["hosted/test/support/identity_tls_fixture.ex"])

    def test_every_missing_changed_or_extra_format_member_refused(self):
        values = exact_format_metadata()
        for path in [path for path in values if path.startswith(collector.FORMAT_BASE)]:
            for action in ("missing", "changed"):
                altered = dict(values)
                if action == "missing": del altered[path]
                else: altered[path] += b" "
                with self.subTest(path=path, action=action), self.assertRaises(collector.CollectorError):
                    collector.validate_format_metadata(altered)
        altered = dict(values)
        altered[collector.FORMAT_BASE + "override.json"] = b"{}"
        with self.assertRaises(collector.CollectorError): collector.validate_format_metadata(altered)

    def test_old_178_source_and_caller_recomputed_digest_are_refused(self):
        with self.assertRaises(collector.CollectorError): collector.validate_source_manifest(collector.FIXTURE_MANIFEST)
        with self.assertRaises(collector.CollectorError):
            collector.validate_source_manifest(collector.FIXTURE_MANIFEST, expected_digest=collector.FIXTURE_SOURCE_DIGEST)
        values = exact_format_metadata()
        seal = collector.FORMAT_BASE + "packet-manifest.json"
        packet = json.loads(values[seal])
        packet["files"]["after.exs"]["sha256"] = "0" * 64
        packet["tree_digest_sha256"] = canonical_digest(packet["files"])
        values[seal] = json.dumps(packet).encode()
        with self.assertRaises(collector.CollectorError): collector.validate_format_metadata(values)

    def test_exact_format_bytes_and_accepted_review_retained_in_archive(self):
        values = exact_format_metadata()
        collector.validate_format_metadata(values)
        with tarfile.open(fileobj=io.BytesIO(collector.source_tar(values)), mode="r:") as archive_value:
            retained = {member.name: archive_value.extractfile(member).read() for member in collector.safe_members(archive_value)}
        self.assertEqual(values, retained)
        self.assertIn(collector.FIXTURE_BASE + "independent-review/review.json", retained)
        self.assertIn(collector.FORMAT_BASE + "after.exs", retained)
        root = COLLECTOR_PATH.resolve().parents[2]
        self.assertEqual((root / "hosted/test/mixer_hosted/identity/tls_fixture_lifecycle_control_test.exs").read_bytes(), retained[collector.FORMAT_BASE + "after.exs"])


class FixtureAmendmentControls(unittest.TestCase):
    BASE = "verification/identity-network-fixture-amendment-v1/metadata/"

    def test_selected_source_passes_with_historical_contracts_unchanged(self):
        result = collector.validate_fixture_metadata(exact_fixture_metadata())
        self.assertEqual(178, result["selected"]["source_count"])
        self.assertEqual(collector.FIXTURE_SOURCE_DIGEST, result["selected"]["source_digest_sha256"])
        self.assertEqual(PRODUCT_DIGEST, result["predecessor"]["source_digest_sha256"])
        self.assertEqual("510771949fe7e95d81cd64f7a8d65df722fa7aa79293b55c773a61bbce8e351b", collector.FIXTURE_SHA256)
        self.assertEqual("13a0b3d84a5140d8fd73d2d4468a5675f6fcaeb8467788bdbda469c18f3a1f4c", collector.FIXTURE_PACKET)
        self.assertEqual("613876f8c91fb07e08100ba8cf02906cf61b67ae8573703ecced44073c84fa5e", collector.FIXTURE_REVIEW_SHA256)
        self.assertEqual("f8d04d5f4f118f940f7183f16b217ca401b34fcda5558dd7929ce2d5657d446d", collector.FIXTURE_REVIEW_PACKET)
        old = collector.validate_selected_metadata(exact_metadata())
        self.assertEqual(177, old["preserved"]["product_files"])
        self.assertEqual(PRODUCT_DIGEST, old["preserved"]["product_digest"])
        execution = collector.validate_execution_metadata(exact_execution_metadata())
        self.assertEqual(old["preserved"], execution["preserved"]["product_pg_bootstrap_contract"])

    def test_exact_delta_is_one_replacement_and_one_added_canonical_test(self):
        result = collector.validate_fixture_metadata(exact_fixture_metadata())
        fixture = "hosted/test/support/identity_tls_fixture.ex"
        control = "hosted/test/mixer_hosted/identity/tls_fixture_lifecycle_control_test.exs"
        expected = {
            fixture: {"bytes": 9533, "sha256": "d3b55796a8baac4f9ebd37cc9ee5e44bde01ca346ce2dd00a0a5dd884711ba55"},
            control: {'bytes': 4401, 'sha256': 'a76b33c4cefac67797fed2909fe7b0c2eb7f7bb99a40b7924adc68901a514fff'},
        }
        self.assertEqual(set(expected), set(result["exact_delta"]))
        old = collector.PREDECESSOR_MANIFEST
        selected = collector.FROZEN_MANIFEST
        self.assertEqual(set(old) | {control}, set(selected))
        self.assertEqual([fixture], [path for path in old if old[path] != selected[path]])
        root = COLLECTOR_PATH.resolve().parents[2]
        for path, row in expected.items():
            body = (root / path).read_bytes()
            self.assertEqual(row, {"bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()})
            self.assertEqual(row, selected[path])
        self.assertEqual([KEY_METHOD, STARTUP_METHOD], list(collector.EXPECTED_METHODS))
        self.assertEqual(["test/mixer_hosted/identity/key_owner_linux_network_test.exs", "test/mixer_hosted/identity/startup_linux_network_test.exs"], collector.TEST_ROOTS)

    def test_old_fixture_missing_test_changed_tests_lock_extra_and_self_digest_refused(self):
        base = collector.FROZEN_MANIFEST
        paths = ["hosted/test/support/identity_tls_fixture.ex", "hosted/test/mixer_hosted/identity/tls_fixture_lifecycle_control_test.exs",
                 "hosted/test/mixer_hosted/identity/key_owner_linux_network_test.exs", "hosted/test/mixer_hosted/identity/startup_linux_network_test.exs", "hosted/mix.lock"]
        cases = [copy.deepcopy(collector.PREDECESSOR_MANIFEST)]
        changed = copy.deepcopy(base)
        changed[paths[0]] = copy.deepcopy(collector.PREDECESSOR_MANIFEST[paths[0]])
        cases.append(changed)
        for path in paths:
            changed = copy.deepcopy(base)
            del changed[path]
            cases.append(changed)
            changed = copy.deepcopy(base)
            changed[path]["sha256"] = "0" * 64
            cases.append(changed)
        changed = copy.deepcopy(base)
        changed["hosted/test/unselected_test.exs"] = {"bytes": 0, "sha256": "0" * 64}
        cases.append(changed)
        for manifest in cases:
            for override in ({}, {"expected_digest": canonical_digest(manifest), "expected_count": len(manifest)}):
                with self.subTest(paths=len(manifest), override=bool(override)), self.assertRaises(collector.CollectorError):
                    collector.validate_source_manifest(manifest, **override)

    def test_every_missing_or_changed_fixture_or_review_member_refused(self):
        base = exact_fixture_metadata()
        for path in [path for path in base if path.startswith(self.BASE)]:
            for action in ("missing", "changed"):
                value = dict(base)
                if action == "missing": del value[path]
                else: value[path] += b" "
                with self.subTest(path=path, action=action), self.assertRaises(collector.CollectorError):
                    collector.validate_fixture_metadata(value)

    def test_old_self_recomputed_and_extra_amendment_metadata_refused(self):
        base = exact_fixture_metadata()
        seal = self.BASE + "packet-manifest.json"
        packet = json.loads(base[seal])
        packet["files"]["source-amendment.json"]["sha256"] = "0" * 64
        packet["tree_digest_sha256"] = canonical_digest(packet["files"])
        for replacement in (json.dumps(packet).encode(), base["verification/identity-network-image-amendment-v2/metadata/packet-manifest.json"]):
            value = dict(base)
            value[seal] = replacement
            with self.assertRaises(collector.CollectorError): collector.validate_fixture_metadata(value)
        value = dict(base)
        value[self.BASE + "override.json"] = b"{}"
        with self.assertRaises(collector.CollectorError): collector.validate_fixture_metadata(value)

    def test_helper_manifest_and_review_are_retained_in_exact_metadata_archive(self):
        values = exact_fixture_metadata()
        result = collector.validate_fixture_metadata(values)
        helper = json.dumps(collector.FIXTURE_MANIFEST, sort_keys=True, separators=(",", ":")).encode()
        self.assertEqual({"bytes": len(helper), "sha256": hashlib.sha256(helper).hexdigest()}, result["literal_helpers"]["frozen-manifest.json"])
        self.assertEqual(178, len(json.loads(helper)))
        with tarfile.open(fileobj=io.BytesIO(collector.source_tar(values)), mode="r:") as archive_value:
            retained = {member.name: archive_value.extractfile(member).read() for member in collector.safe_members(archive_value)}
        self.assertEqual(values, retained)
        self.assertIn(self.BASE + "independent-review/review.json", retained)
        self.assertIn(self.BASE + "selected-source-manifest.json", retained)
        for name in ("source-amendment.json", "selected-source-manifest.json", "independent-review/review.json", "independent-review/packet-manifest.json"):
            value = dict(values)
            value[self.BASE + name] = b"{}"
            with self.subTest(name=name), self.assertRaises(collector.CollectorError):
                collector.validate_fixture_metadata(value)


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


class BootstrapExportControls(unittest.TestCase):
    def test_high_byte_nul_and_all_256_values_pass_only_exact_size_and_hash(self):
        for body in (b"\x00", b"\x80\xff\x00", bytes(range(256)), bytes(range(256)) * 257):
            pins = copy.deepcopy(collector.BOOTSTRAP)
            pins["hex"]["sha512"] = hashlib.sha512(body).hexdigest()
            with self.subTest(bytes=len(body)), mock.patch.object(collector, "BOOTSTRAP", pins):
                self.assertEqual(body, collector.validate_bootstrap_export("hex", body, len(body)))
                transformed = body.decode("latin1").encode("utf8")
                if transformed != body:
                    with self.assertRaises(collector.CollectorError):
                        collector.validate_bootstrap_export("hex", transformed, len(body))

    def test_wrong_export_size_digest_type_or_download_bound_is_refused(self):
        body = bytes(range(256))
        for tool, value, expected in (("hex", body, len(body) + 1), ("hex", body, len(body)),
                                      ("rebar", body, len(body)), ("other", body, len(body)),
                                      ("hex", bytearray(body), len(body)), ("hex", body, True),
                                      ("hex", body, 0), ("hex", body, 16777217)):
            with self.subTest(tool=tool, expected=expected), self.assertRaises(collector.CollectorError):
                collector.validate_bootstrap_export(tool, value, expected)


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

    A tiny in-memory source gate substitutes only the 178-file hash preimage. It
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

    def run_fixture(self, bodies, manifest, *, mtimes=None):
        timestamps = {name: 1 for name in bodies}
        timestamps.update(mtimes or {})
        with archive([(name, tarfile.REGTYPE, body, "") for name, body in bodies.items()], mtimes=timestamps) as value:
            data = value.fileobj.getvalue()
        bootstrap = copy.deepcopy(collector.BOOTSTRAP)
        bootstrap["rebar"]["sha512"] = hashlib.sha512(b"checked bootstrap fixture").hexdigest()
        with mock.patch.object(collector, "validate_configured_startup_source_manifest") as source_gate, \
                mock.patch.multiple(collector, CONFIGURED_STARTUP_MANIFEST=manifest["source"], BOOTSTRAP=bootstrap,
                                    PREREQUISITES_EXS="prerequisites fixture", BOOTSTRAP_EXS="bootstrap fixture",
                                    MANIFEST_EXS="manifest fixture",
                                    NETNS_EXS="netns fixture", OBSERVER_EXS="observer fixture", MOUNTS_EXS="mounts fixture"):
            result = collector.validate_prepared_archive(data, manifest)
            source_gate.assert_called_once_with(manifest["source"])
            return result

    def test_exact_section_membership_and_hashes_pass_after_source_admission(self):
        bodies, manifest = self.fixture()
        self.assertEqual(set(bodies), set(self.run_fixture(bodies, manifest)))

    def test_epoch_zero_archive_is_refused_even_with_exact_payload_hashes(self):
        bodies, manifest = self.fixture()
        with self.assertRaisesRegex(collector.CollectorError, "prepared archive timestamp mismatch"):
            self.run_fixture(bodies, manifest, mtimes={name: 0 for name in bodies})

    def test_one_wrong_timestamp_in_any_prepared_section_is_refused(self):
        bodies, manifest = self.fixture()
        for name in bodies:
            for timestamp in (0, 2, 4294967295):
                with self.subTest(name=name, timestamp=timestamp), \
                        self.assertRaisesRegex(collector.CollectorError, "prepared archive timestamp mismatch"):
                    self.run_fixture(bodies, manifest, mtimes={name: timestamp})

    def test_negative_and_fractional_prepared_timestamps_are_refused(self):
        bodies, manifest = self.fixture()
        for timestamp in (-1, 1.5):
            with self.subTest(timestamp=timestamp), self.assertRaises(collector.CollectorError):
                self.run_fixture(bodies, manifest, mtimes={"hosted/deps/dependency/lib/fixture.ex": timestamp})

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
        # SourceControls keep the complete selected source decision pinned; a
        # protected dirty store in the development tree is not a Git fixture.
        subject = self.make_collector(directory, lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("real command forbidden")))
        controls = ["hosted/scripts/test-identity-network.py", "hosted/scripts/test_identity_network_collector.py", "docs/hosted-identity-production-network-ci-contract.md", ".github/workflows/identity-network.yml"]
        for path in controls:
            target = subject.root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((repository / path).read_bytes())
        def blobs(paths):
            return {path: (repository / path).read_bytes() if path.startswith((collector.CURRENT_SOURCE_BASE, collector.SUCCESSOR_SOURCE_BASE, collector.PRIVATE_SOURCE_BASE, collector.BROWSER_SOURCE_BASE, collector.OPERATION_SOURCE_BASE, collector.LIFETIME_SOURCE_BASE, collector.COMMIT_SOURCE_BASE, collector.PROXY_SOURCE_BASE, collector.BUILD_READ_SOURCE_BASE, collector.BROWSER_BUILD_SOURCE_BASE, collector.OWNED_EVIDENCE_SOURCE_BASE, collector.HOSTED_COMPILER_SOURCE_BASE, collector.CATALOG_JOIN_SOURCE_BASE, collector.PROVIDER_HTTPS_SOURCE_BASE, collector.ORDINARY_BROWSER_SOURCE_BASE, collector.SUPERVISED_PROVIDER_SOURCE_BASE, collector.PROVIDER_IO_SOURCE_BASE, collector.CONFIGURED_STARTUP_SOURCE_BASE)) or not path.startswith("verification/") else metadata[path] for path in paths}
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
                    mock.patch.object(collector, "validate_configured_startup_source_manifest", return_value=collector.CONFIGURED_STARTUP_MANIFEST), \
                    mock.patch.object(subject, "create", side_effect=AssertionError("create before metadata admission")) as create:
                with self.assertRaisesRegex(KeyError, "metadata/packet-manifest.json"):
                    subject.collect()
            self.assertFalse(create.called)
            self.assertFalse(any(argv[0] == "docker" for argv in calls))

    def test_collect_requires_actual_prepare_result_before_bootstrap(self):
        with tempfile.TemporaryDirectory(prefix="identity-controls-") as directory:
            subject, calls = self._amendment_preflight_subject(directory, exact_format_metadata())
            prepared = owned("prepare")
            inspected = {"Config": {"Env": [key + "=" + value for key, value in collector.BASE_ENV.items()]}}
            with mock.patch.dict("os.environ", {"GITHUB_ACTIONS": "true", "RUNNER_OS": "Linux", "RUNNER_ARCH": "X64"}, clear=True), \
                    mock.patch.object(collector.os, "uname", return_value=collector.os.uname_result(("Linux", "control", "0", "0", "x86_64"))), \
                    mock.patch.object(collector.os, "readlink", return_value="net:[100]"), \
                    mock.patch.object(collector, "validate_configured_startup_source_manifest", return_value=collector.CONFIGURED_STARTUP_MANIFEST), \
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
                    mock.patch.object(collector, "validate_configured_startup_source_manifest", return_value=collector.CONFIGURED_STARTUP_MANIFEST), \
                    mock.patch.object(subject, "create", side_effect=AssertionError("create before v2 seal")) as create:
                with self.assertRaisesRegex(KeyError, "v2/metadata/packet-manifest.json"):
                    subject.collect()
            self.assertFalse(create.called)
            self.assertFalse(any(argv[0] == "docker" for argv in calls))

    def test_collect_requires_fixture_amendment_and_review_before_any_image_operation(self):
        base = "verification/identity-network-fixture-amendment-v1/metadata/"
        for path in ("packet-manifest.json", "source-amendment.json", "independent-review/packet-manifest.json", "independent-review/review.json"):
            for action in ("missing", "changed"):
                metadata = exact_fixture_metadata()
                if action == "missing": del metadata[base + path]
                else: metadata[base + path] += b" "
                with self.subTest(path=path, action=action), tempfile.TemporaryDirectory(prefix="identity-controls-") as directory:
                    subject, calls = self._amendment_preflight_subject(directory, metadata)
                    with mock.patch.dict("os.environ", {"GITHUB_ACTIONS": "true", "RUNNER_OS": "Linux", "RUNNER_ARCH": "X64"}, clear=True), \
                            mock.patch.object(collector.os, "uname", return_value=collector.os.uname_result(("Linux", "control", "0", "0", "x86_64"))), \
                            mock.patch.object(collector, "validate_configured_startup_source_manifest", return_value=collector.CONFIGURED_STARTUP_MANIFEST), \
                            mock.patch.object(subject, "create", side_effect=AssertionError("create before fixture admission")) as create:
                        with self.assertRaises((collector.CollectorError, KeyError)): subject.collect()
                    self.assertFalse(create.called)
                    self.assertFalse(any(argv[0] == "docker" for argv in calls))

    def test_collect_requires_format_amendment_before_any_image_operation(self):
        for path in ("packet-manifest.json", "source-amendment.json", "format-proof.json", "after.exs"):
            for action in ("missing", "changed"):
                metadata = exact_format_metadata()
                if action == "missing": del metadata[collector.FORMAT_BASE + path]
                else: metadata[collector.FORMAT_BASE + path] += b" "
                with self.subTest(path=path, action=action), tempfile.TemporaryDirectory(prefix="identity-controls-") as directory:
                    subject, calls = self._amendment_preflight_subject(directory, metadata)
                    with mock.patch.dict("os.environ", {"GITHUB_ACTIONS": "true", "RUNNER_OS": "Linux", "RUNNER_ARCH": "X64"}, clear=True), \
                            mock.patch.object(collector.os, "uname", return_value=collector.os.uname_result(("Linux", "control", "0", "0", "x86_64"))), \
                            mock.patch.object(collector, "validate_configured_startup_source_manifest", return_value=collector.CONFIGURED_STARTUP_MANIFEST), \
                            mock.patch.object(subject, "create", side_effect=AssertionError("create before format admission")) as create:
                        with self.assertRaises((collector.CollectorError, KeyError)): subject.collect()
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


    def _binary_copy_subject(self, directory, payload, *, code=0, stderr=b""):
        subject = self.make_collector(directory, lambda argv, timeout, stdin: (code, payload, stderr))
        def execute(owned_value, argv, timeout, **options):
            # This inspects delivered Elixir source and exercises the real host
            # byte transport with an inert runner. It executes no Elixir VM.
            expected_prefix = "; :ok = :io.setopts(:standard_io, encoding: :latin1); :ok = IO.binwrite(File.read!(path))"
            self.assertEqual(["/usr/local/bin/elixir", "-e"], argv[:2])
            self.assertTrue(argv[-1].endswith(expected_prefix))
            self.assertEqual(1, argv[-1].count(":io.setopts"))
            self.assertEqual(30, timeout)
            return subject.command(argv, timeout, **options)
        subject.execute = execute
        return subject

    def test_copy_out_binary_literal_and_host_transport_preserve_high_bytes_nul_all256(self):
        for path in ("/workspace/downloads/hex.ez", "/workspace/tooling/rebar3", "/workspace/prepared.tar", "/workspace/evidence/runtime.json"):
            for payload in (b"\x00", b"\x80\xff\x00", bytes(range(256)), bytes(range(256)) * 257):
                with self.subTest(path=path, bytes=len(payload)), tempfile.TemporaryDirectory(prefix="identity-controls-") as directory:
                    subject = self._binary_copy_subject(directory, payload)
                    maximum = len(payload) + 1
                    self.assertEqual(payload, subject.copy_file_out(owned("prepare"), path, maximum))
                    row = json.loads((subject.output / "logs/0001.json").read_bytes())
                    expected = "path = " + json.dumps(path) + "; true = File.stat!(path).size <= " + str(maximum) + "; :ok = :io.setopts(:standard_io, encoding: :latin1); :ok = IO.binwrite(File.read!(path))"
                    self.assertEqual(expected, row["argv"][-1])
                    self.assertEqual(len(payload), row["stdout_bytes"])
                    self.assertEqual(hashlib.sha256(payload).hexdigest(), row["stdout_sha256"])
                    self.assertTrue(row["stdout_complete"])
                    self.assertTrue(row["stderr_complete"])

    def test_failed_host_size_or_hash_retains_only_public_bootstrap_bytes_and_receipt(self):
        for tool, path in (("hex", "/workspace/downloads/hex.ez"), ("rebar", "/workspace/tooling/rebar3")):
            for failure in ("size", "hash"):
                with self.subTest(tool=tool, failure=failure), tempfile.TemporaryDirectory(prefix="identity-controls-") as directory:
                    payload = bytes(range(256))
                    subject = self._binary_copy_subject(directory, payload)
                    artifact = subject.copy_file_out(owned("prepare"), path, 4096)
                    raw = subject.output / "bootstrap-exports" / (tool + "-actual.bin")
                    receipt = json.loads(raw.with_suffix(".json").read_bytes())
                    self.assertEqual(payload, raw.read_bytes())
                    self.assertEqual(len(payload), receipt["bytes"])
                    self.assertEqual(hashlib.sha256(payload).hexdigest(), receipt["sha256"])
                    self.assertEqual(hashlib.sha512(payload).hexdigest(), receipt["sha512"])
                    self.assertEqual(4096, receipt["maximum_bytes"])
                    self.assertEqual(path, receipt["container_path"])
                    self.assertTrue(receipt["stdout_complete"])
                    expected = len(payload) + 1 if failure == "size" else len(payload)
                    with self.assertRaisesRegex(collector.CollectorError, "byte-count mismatch" if failure == "size" else "digest mismatch"):
                        collector.validate_bootstrap_export(tool, artifact, expected)
                    subject.seal()
                    manifest = json.loads((subject.output / "artifact-manifest.json").read_bytes())
                    self.assertEqual({"bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}, manifest["files"]["bootstrap-exports/" + tool + "-actual.bin"])
                    self.assertFalse((subject.output / ".scratch").exists())

    def test_public_export_overflow_retains_bounded_partial_bytes_with_incomplete_flags(self):
        payload = bytes(range(256)) * 33
        with tempfile.TemporaryDirectory(prefix="identity-controls-") as directory:
            subject = self._binary_copy_subject(directory, payload)
            with self.assertRaisesRegex(collector.CollectorError, "output incomplete"):
                subject.copy_file_out(owned("prepare"), "/workspace/downloads/hex.ez", 4096)
            raw = subject.output / "bootstrap-exports/hex-actual.bin"
            self.assertEqual(payload[:4096], raw.read_bytes())
            receipt = json.loads(raw.with_suffix(".json").read_bytes())
            self.assertEqual(4096, receipt["bytes"])
            self.assertIs(False, receipt["stdout_complete"])
            self.assertIs(False, receipt["stderr_complete"])
            self.assertEqual(hashlib.sha256(payload[:4096]).hexdigest(), receipt["sha256"])

    def test_public_nonzero_command_retains_actual_bytes_without_forging_command_success(self):
        payload = b"\x00\x80\xff"
        with tempfile.TemporaryDirectory(prefix="identity-controls-") as directory:
            subject = self._binary_copy_subject(directory, payload, code=1, stderr=b"export failed")
            with self.assertRaises(collector.CollectorError):
                subject.copy_file_out(owned("prepare"), "/workspace/tooling/rebar3", 4096)
            raw = subject.output / "bootstrap-exports/rebar-actual.bin"
            self.assertEqual(payload, raw.read_bytes())
            receipt = json.loads(raw.with_suffix(".json").read_bytes())
            self.assertEqual(1, receipt["command_exit_code"])
            self.assertIs(False, receipt["stdout_complete"])

    def test_nonpublic_exports_remain_scratch_only_and_unreviewed_paths_stay_refused(self):
        for path in ("/workspace/prepared.tar", "/workspace/evidence/fixture-key-private.json"):
            with self.subTest(path=path), tempfile.TemporaryDirectory(prefix="identity-controls-") as directory:
                subject = self._binary_copy_subject(directory, b"private-control-fixture")
                subject.copy_file_out(owned("test"), path, 4096)
                self.assertFalse((subject.output / "bootstrap-exports").exists())
                self.assertFalse((subject.output / ".scratch/copy.bin").exists())
        for path in ("/etc/shadow", "/workspace/downloads/other", "/workspace/tooling/other"):
            with self.subTest(path=path), tempfile.TemporaryDirectory(prefix="identity-controls-") as directory:
                subject = self._binary_copy_subject(directory, b"control")
                with self.assertRaises(collector.CollectorError):
                    subject.copy_file_out(owned("prepare"), path)
                self.assertEqual(0, subject.command_number)

    def test_public_capture_cannot_be_overwritten_or_expand_its16MiB_bound(self):
        with tempfile.TemporaryDirectory(prefix="identity-controls-") as directory:
            subject = self._binary_copy_subject(directory, b"\x00\xff")
            subject.copy_file_out(owned("prepare"), "/workspace/downloads/hex.ez", 4096)
            with self.assertRaisesRegex(collector.CollectorError, "already retained"):
                subject.copy_file_out(owned("prepare"), "/workspace/downloads/hex.ez", 4096)
            self.assertEqual(1, subject.command_number)
            self.assertEqual(b"\x00\xff", (subject.output / "bootstrap-exports/hex-actual.bin").read_bytes())
        with tempfile.TemporaryDirectory(prefix="identity-controls-") as directory:
            subject = self._binary_copy_subject(directory, b"control")
            with self.assertRaisesRegex(collector.CollectorError, "public bootstrap export cap"):
                subject.copy_file_out(owned("prepare"), "/workspace/tooling/rebar3", 16777217)
            self.assertEqual(0, subject.command_number)


class GeneratedCompilerOutputControls(unittest.TestCase):
    PATH = "hosted/deps/telemetry/_build/prod/lib/.rebar3/rebar_compiler_erl/source.dag"
    PARENTS = ["/workspace", "/workspace/hosted", "/workspace/hosted/deps", "/workspace/hosted/deps/telemetry", "/workspace/hosted/deps/telemetry/_build", "/workspace/hosted/deps/telemetry/_build/prod", "/workspace/hosted/deps/telemetry/_build/prod/lib", "/workspace/hosted/deps/telemetry/_build/prod/lib/.rebar3", "/workspace/hosted/deps/telemetry/_build/prod/lib/.rebar3/rebar_compiler_erl"]

    def row(self, body=b"opaque inert DAG fixture\x00\x80\xff"):
        return {"bytes": len(body), "sha256": hashlib.sha256(body).hexdigest(),
                "type": "regular", "links": 1, "uid": 0, "gid": 0, "mode": 0o644,
                "parents": {path: {"type": "directory", "uid": 0, "gid": 0, "mode": 0o755} for path in self.PARENTS}}

    def fixture(self, body=b"opaque inert DAG fixture\x00\x80\xff"):
        # Input anchors are independently written from the locked sealed archive.
        prepared = {"source": copy.deepcopy(collector.CONFIGURED_STARTUP_MANIFEST), "deps": {
            "hosted/deps/telemetry/rebar.config": {"bytes": 943, "sha256": "2ac5ee04618133d912fcafe68859904ee88aa7bfac678c8165ce1dfb32cbc3b0"},
            "hosted/deps/telemetry/src/telemetry.erl": {"bytes": 17044, "sha256": "8bb2a1fa116def38f63a5b36b65fdc9af98022e6e378e047f38d49b584564278"},
            "hosted/deps/telemetry/src/telemetry.app.src": {"bytes": 533, "sha256": "29778243956492d0d255bf2289fe5e4f6b10f22d282ca5679015a478c1eb33d2"},
            "hosted/deps/other/src/input.erl": {"bytes": 12, "sha256": "a" * 64}},
            "tools": {"tooling/rebar3": {"bytes": 823379, "sha256": "b" * 64}},
            "helpers": {"collector-manifest.exs": {"bytes": 100, "sha256": "c" * 64}}}
        compiled = copy.deepcopy(prepared)
        compiled["deps"][self.PATH] = self.row(body)
        return prepared, compiled

    def subject(self, directory, payload, code=0):
        subject = CollectorMethodWiringControls.make_collector(self, directory, lambda argv, timeout, stdin: (code, payload, b""))
        def execute(record, argv, timeout, **options):
            self.assertEqual(owned("test"), record)
            self.assertEqual(["/usr/local/bin/elixir", "/workspace/collector-manifest.exs", "export-generated"], argv)
            self.assertGreater(timeout, 0)
            self.assertLessEqual(timeout, 15)
            self.assertEqual(65536, options["limit"])
            return subject.command(argv, timeout, **options)
        subject.execute = execute
        return subject

    def test_one_exact_fresh_output_passes_without_old_observed_hash_whitelist(self):
        self.assertEqual(self.PATH, collector.GENERATED_DAG_PATH)
        self.assertEqual(65536, collector.MAX_GENERATED_DAG_BYTES)
        self.assertEqual(self.PARENTS, collector.GENERATED_DAG_PARENTS)
        for body in (b"opaque fixture", bytes(range(256)), b"\x00" * 65536):
            prepared, compiled = self.fixture(body)
            unchanged = copy.deepcopy(prepared)
            self.assertEqual(compiled, collector.validate_compiled_source_unchanged(prepared, compiled))
            self.assertEqual(unchanged, prepared)
            with self.assertRaises(collector.CollectorError):
                collector.validate_source_unchanged(prepared, compiled)

    def test_output_absent_or_preexisting_during_prepare_or_restore_is_refused(self):
        prepared, compiled = self.fixture()
        for before, after in ((compiled, compiled), (prepared, prepared)):
            with self.subTest(before_has_dag=self.PATH in before["deps"]), self.assertRaises(collector.CollectorError):
                collector.validate_compiled_source_unchanged(before, after)
        with self.assertRaises(collector.CollectorError):
            collector.validate_source_unchanged(prepared, compiled)

    def test_neighbor_alias_and_other_build_outputs_are_never_ignored(self):
        for path in (self.PATH + ".other", self.PATH.replace("source.dag", "source.erl"),
                     self.PATH.replace("telemetry/", "other/"), self.PATH.replace("/prod/", "/test/"),
                     self.PATH.replace("/source.dag", "//source.dag"), self.PATH.replace("/source.dag", "/../source.dag"),
                     "hosted/deps/telemetry/_build/prod/lib/other.beam", "hosted/_build/test/injected.ex"):
            prepared, compiled = self.fixture()
            compiled["deps"][path] = self.row()
            with self.subTest(path=path), self.assertRaises(collector.CollectorError):
                collector.validate_compiled_source_unchanged(prepared, compiled)

    def test_every_prepared_section_rejects_changed_missing_and_added_inputs(self):
        for section in ("source", "deps", "tools", "helpers"):
            for action in ("changed", "missing", "extra"):
                prepared, compiled = self.fixture()
                target = next(path for path in prepared[section] if path != self.PATH)
                if action == "changed": compiled[section][target]["sha256"] = "0" * 64
                elif action == "missing": del compiled[section][target]
                else: compiled[section][target + ".extra"] = {"bytes": 1, "sha256": "d" * 64}
                with self.subTest(section=section, action=action), self.assertRaises(collector.CollectorError):
                    collector.validate_compiled_source_unchanged(prepared, compiled)

    def test_locked_telemetry_anchors_and_frozen_lock_stay_required(self):
        for target in ("hosted/deps/telemetry/rebar.config", "hosted/deps/telemetry/src/telemetry.erl", "hosted/deps/telemetry/src/telemetry.app.src"):
            for action in ("missing", "changed"):
                prepared, compiled = self.fixture()
                for manifest in (prepared, compiled):
                    if action == "missing": del manifest["deps"][target]
                    else: manifest["deps"][target]["sha256"] = "0" * 64
                with self.subTest(target=target, action=action), self.assertRaises(collector.CollectorError):
                    collector.validate_compiled_source_unchanged(prepared, compiled)
        prepared, compiled = self.fixture()
        for manifest in (prepared, compiled): manifest["source"]["hosted/mix.lock"]["sha256"] = "0" * 64
        with self.assertRaises(collector.CollectorError): collector.validate_compiled_source_unchanged(prepared, compiled)

    def test_generated_file_type_link_owner_mode_size_and_hash_fail_closed(self):
        for field, value in (("type", "symlink"), ("type", "directory"), ("links", 2), ("links", True),
                             ("uid", 1), ("uid", False), ("gid", 1), ("mode", 0o755), ("mode", 0o600),
                             ("mode", 0o4644), ("bytes", 0), ("bytes", -1), ("bytes", True),
                             ("bytes", 65537), ("sha256", "g" * 64), ("sha256", "a" * 63)):
            row = self.row(); row[field] = value
            with self.subTest(field=field, value=value), self.assertRaises(collector.CollectorError): collector.validate_generated_dag_row(row)
        for field in self.row():
            row = self.row(); del row[field]
            with self.subTest(missing=field), self.assertRaises(collector.CollectorError): collector.validate_generated_dag_row(row)
        row = self.row(); row["extra"] = 1
        with self.assertRaises(collector.CollectorError): collector.validate_generated_dag_row(row)

    def test_each_parent_requires_exact_path_directory_owner_and_mode(self):
        for path in self.PARENTS:
            for field, value in (("type", "symlink"), ("type", "regular"), ("uid", 1), ("gid", 1), ("mode", 0o777)):
                row = self.row(); row["parents"][path][field] = value
                with self.subTest(path=path, field=field), self.assertRaises(collector.CollectorError): collector.validate_generated_dag_row(row)
            row = self.row(); del row["parents"][path]
            with self.subTest(missing=path), self.assertRaises(collector.CollectorError): collector.validate_generated_dag_row(row)
        row = self.row(); row["parents"][self.PARENTS[-1] + "/../alias"] = row["parents"].pop(self.PARENTS[-1])
        with self.assertRaises(collector.CollectorError): collector.validate_generated_dag_row(row)

    def test_manifest_section_injection_and_type_substitution_fail_closed(self):
        for section in ("source", "deps", "tools", "helpers"):
            for value in (None, [], "invalid"):
                prepared, compiled = self.fixture(); compiled[section] = value
                with self.subTest(section=section, value=value), self.assertRaises(collector.CollectorError): collector.validate_compiled_source_unchanged(prepared, compiled)
        prepared, compiled = self.fixture(); compiled["generated"] = {self.PATH: self.row()}
        with self.assertRaises(collector.CollectorError): collector.validate_compiled_source_unchanged(prepared, compiled)

    def test_final_comparison_freezes_generated_bytes_and_identity_with_all_inputs(self):
        _, compiled = self.fixture()
        collector.validate_source_unchanged(compiled, copy.deepcopy(compiled))
        for field, value in (("sha256", "0" * 64), ("bytes", 1), ("mode", 0o600), ("uid", 1), ("links", 2)):
            after = copy.deepcopy(compiled); after["deps"][self.PATH][field] = value
            with self.subTest(field=field), self.assertRaises(collector.CollectorError): collector.validate_source_unchanged(compiled, after)
        after = copy.deepcopy(compiled); del after["deps"][self.PATH]
        with self.assertRaises(collector.CollectorError): collector.validate_source_unchanged(compiled, after)

    def test_prepared_archive_build_ban_remains_even_for_the_new_exact_output(self):
        helper = PreparedArchiveControls()
        bodies, manifest = helper.fixture(); bodies[self.PATH] = b"premature output"
        manifest["deps"][self.PATH] = {"bytes": len(bodies[self.PATH]), "sha256": hashlib.sha256(bodies[self.PATH]).hexdigest()}
        with self.assertRaises(collector.CollectorError): helper.run_fixture(bodies, manifest)

    def test_exact_owned_test_export_retains_opaque_bytes_and_hash_join(self):
        body = bytes(range(256)); expected = self.row(body)
        with tempfile.TemporaryDirectory(prefix="identity-controls-") as directory:
            subject = self.subject(directory, body)
            result = subject.capture_generated_dag(owned("test"), expected, .25)
            self.assertEqual({"path": self.PATH, "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest(), "classification": "opaque-postcompile-rebar-telemetry-metadata"}, result)
            raw = subject.output / "compiler-generated/telemetry-source.dag"
            self.assertEqual(body, raw.read_bytes())
            receipt = json.loads(raw.with_suffix(".json").read_bytes())
            self.assertEqual(expected, receipt["expected_manifest_row"])
            self.assertEqual(CID_TEST, receipt["owned_cid"])
            self.assertEqual("/workspace/" + self.PATH, receipt["container_path"])
            self.assertEqual(65536, receipt["maximum_bytes"])
            self.assertIs(True, receipt["stdout_complete"])
            self.assertEqual(0, receipt["command_exit_code"])
            subject.seal()
            manifest = json.loads((subject.output / "artifact-manifest.json").read_bytes())
            self.assertEqual({"bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()}, manifest["files"]["compiler-generated/telemetry-source.dag"])

    def test_capture_refuses_other_roles_states_paths_and_overwrite(self):
        for timeout in (0, -1, 16, True, float("inf"), float("nan")):
            with self.subTest(timeout=timeout), tempfile.TemporaryDirectory(prefix="identity-controls-") as directory:
                subject = self.subject(directory, b"fixture")
                with self.assertRaises(collector.CollectorError): subject.capture_generated_dag(owned("test"), self.row(b"fixture"), timeout)
                self.assertEqual(0, subject.command_number)
        for role in ("prepare", "pg"):
            with tempfile.TemporaryDirectory(prefix="identity-controls-") as directory:
                subject = self.subject(directory, b"fixture")
                with self.assertRaises(collector.CollectorError): subject.capture_generated_dag(owned(role), self.row(b"fixture"))
                self.assertEqual(0, subject.command_number)
        with tempfile.TemporaryDirectory(prefix="identity-controls-") as directory:
            subject = self.subject(directory, b"fixture"); record = owned("test"); record.state = "identity_lost"
            with self.assertRaises(collector.CollectorError): subject.capture_generated_dag(record, self.row(b"fixture"))
            with self.assertRaises(collector.CollectorError): subject.copy_file_out(owned("test"), "/workspace/" + self.PATH, 65536)
            self.assertEqual(0, subject.command_number)
            subject.capture_generated_dag(owned("test"), self.row(b"fixture"))
            with self.assertRaises(collector.CollectorError): subject.capture_generated_dag(owned("test"), self.row(b"fixture"))
            self.assertEqual(1, subject.command_number)

    def test_capture_hash_or_size_mismatch_preserves_actual_failure_bytes(self):
        for field, value in (("sha256", "a" * 64), ("bytes", 255)):
            with self.subTest(field=field), tempfile.TemporaryDirectory(prefix="identity-controls-") as directory:
                body = bytes(range(256)); expected = self.row(body); expected[field] = value
                subject = self.subject(directory, body)
                with self.assertRaises(collector.CollectorError): subject.capture_generated_dag(owned("test"), expected)
                raw = subject.output / "compiler-generated/telemetry-source.dag"
                self.assertEqual(body, raw.read_bytes())
                receipt = json.loads(raw.with_suffix(".json").read_bytes())
                self.assertEqual(hashlib.sha256(body).hexdigest(), receipt["sha256"])
                self.assertEqual(expected, receipt["expected_manifest_row"])
                self.assertIs(True, receipt["stdout_complete"])

    def test_overflow_and_failed_export_preserve_bounded_partial_facts(self):
        for body, code in ((bytes(range(256)) * 257, 0), (b"failed fixture", 1)):
            with self.subTest(code=code), tempfile.TemporaryDirectory(prefix="identity-controls-") as directory:
                subject = self.subject(directory, body, code)
                with self.assertRaises(collector.CollectorError): subject.capture_generated_dag(owned("test"), self.row(b"expected fixture"))
                raw = subject.output / "compiler-generated/telemetry-source.dag"
                self.assertEqual(body[:65536], raw.read_bytes())
                receipt = json.loads(raw.with_suffix(".json").read_bytes())
                self.assertEqual(code, receipt["command_exit_code"])
                self.assertIs(False, receipt["stdout_complete"])
                self.assertLessEqual(receipt["bytes"], 65536)

    def test_literal_helper_and_authorization_wiring_are_source_bound_only(self):
        # This is static wiring evidence, deliberately not an Elixir syntax/runtime pass.
        helper = collector.MANIFEST_EXS
        self.assertIn('@generated "/workspace/' + self.PATH + '"', helper)
        self.assertIn('File.lstat!(@generated)', helper)
        self.assertIn('type: :regular, links: 1, uid: 0, gid: 0', helper)
        self.assertIn('0o644 = Bitwise.band(mode, 0o7777)', helper)
        self.assertIn('0o755 = Bitwise.band(mode, 0o7777)', helper)
        self.assertIn('size > 0 and size <= 65536', helper)
        self.assertIn('["export-generated"] -> MixerIdentityNetworkCollector.Manifest.export_generated()', helper)
        export = helper.split('  def export_generated do\n', 1)[1].split('\n  end', 1)[0]
        self.assertLess(export.index('generated_identity()'), export.index('File.read!(@generated)'))
        self.assertLess(export.index(':io.setopts(:standard_io, encoding: :latin1)'), export.index('IO.binwrite(bytes)'))
        source = COLLECTOR_PATH.read_text()
        compile_call = source.index('self.execute(test, ["/usr/local/bin/mix", "compile", "--warnings-as-errors"]')
        capture_call = source.index('generated = self.capture_generated_dag(test,', compile_call)
        validate_call = source.index('validate_compiled_source_unchanged(prepared_manifest, before_tests)', capture_call)
        authorize = source.index('flag_env = {**TEST_ENV, "MIXER_ISOLATED_NETNS": "1"}', validate_call)
        self.assertLess(compile_call, capture_call)
        self.assertLess(capture_call, validate_call)
        self.assertLess(validate_call, authorize)
        self.assertIn('validate_source_unchanged(prepared_manifest, restored)', source[:compile_call])
        self.assertIn('validate_source_unchanged(before_tests, after_tests)', source[authorize:])


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




class CurrentSourceSelectionControls(unittest.TestCase):
    DIGEST = "07bb7b5d7b518f487e4981dc4aa0e911f16c99a5bbbf96ea0bdc204d9455ccd9"
    SELECTION = "14868be39631a86c79f4ba7b6bfb9386c6d80062ef4d0ddebbf55aea833afc96"

    def metadata(self):
        root = COLLECTOR_PATH.resolve().parents[2]
        return {collector.CURRENT_SOURCE_BASE + name: (root / collector.CURRENT_SOURCE_BASE / name).read_bytes()
                for name in ("selection.json", "selected-source-manifest.json")}

    def test_current_actual_source_has_independent_closed_root(self):
        value = collector.validate_current_source_metadata(self.metadata())
        result = {"source_count": value["selected"]["source_count"], "source_digest_sha256": value["selected"]["source_digest_sha256"], "selection_sha256": self.SELECTION, "runtime_or_GA_accepted": value["runtime_or_GA_accepted"]}
        with self.assertRaises(collector.CollectorError):
            collector.check_current_source(COLLECTOR_PATH.resolve().parents[2])
        self.assertEqual((185, self.DIGEST, self.SELECTION),
                         (result["source_count"], result["source_digest_sha256"], result["selection_sha256"]))
        self.assertFalse(result["runtime_or_GA_accepted"])

    def test_historical_and_current_source_authority_are_distinct(self):
        collector.validate_source_manifest(copy.deepcopy(collector.FROZEN_MANIFEST))
        collector.validate_current_source_manifest(copy.deepcopy(collector.CURRENT_MANIFEST))
        with self.assertRaises(collector.CollectorError): collector.validate_current_source_manifest(collector.FROZEN_MANIFEST)
        with self.assertRaises(collector.CollectorError): collector.validate_source_manifest(collector.CURRENT_MANIFEST)

    def test_current_source_changed_missing_and_foreign_members_refuse(self):
        for path in ("hosted/mix.lock", "hosted/lib/mixer_hosted/billing/webhook_inbox.ex",
                     "hosted/test/mixer_hosted/builds/coordinator_test.exs", "hosted/test/test_helper.exs"):
            value = copy.deepcopy(collector.CURRENT_MANIFEST)
            value[path]["sha256"] = "0" * 64
            with self.subTest(path=path), self.assertRaises(collector.CollectorError): collector.validate_current_source_manifest(value)
        value = copy.deepcopy(collector.CURRENT_MANIFEST)
        value.pop("hosted/lib/mixer_hosted/billing/webhook_inbox.ex")
        with self.assertRaises(collector.CollectorError): collector.validate_current_source_manifest(value)
        value["hosted/priv/repo/migrations/20261110000001_foreign.exs"] = {"bytes": 0, "sha256": "0" * 64}
        with self.assertRaises(collector.CollectorError): collector.validate_current_source_manifest(value)

    def test_untrusted_source_digest_cannot_replace_current_authority(self):
        value = copy.deepcopy(collector.CURRENT_MANIFEST)
        value["hosted/mix.lock"]["sha256"] = "0" * 64
        with self.assertRaises(collector.CollectorError):
            collector.validate_current_source_manifest(value, expected_digest=canonical_digest(value), expected_count=185)

    def test_current_metadata_exact_pin_and_membership(self):
        metadata = self.metadata()
        result = collector.validate_current_source_metadata(metadata)
        self.assertEqual(185, result["selected"]["source_count"])
        for path in metadata:
            changed = dict(metadata)
            changed[path] += b" "
            with self.subTest(path=path), self.assertRaises(collector.CollectorError): collector.validate_current_source_metadata(changed)
        changed = dict(metadata)
        changed[collector.CURRENT_SOURCE_BASE + "foreign.json"] = b"{}"
        with self.assertRaises(collector.CollectorError): collector.validate_current_source_metadata(changed)

    def test_current_metadata_refusal_precedes_any_docker_operation(self):
        helper = CollectorMethodWiringControls()
        with tempfile.TemporaryDirectory(prefix="identity-controls-") as directory:
            subject, calls = helper._amendment_preflight_subject(directory, exact_format_metadata())
            original = subject.git_blobs
            def blobs(paths):
                result = original(paths)
                if collector.SUCCESSOR_SOURCE_BASE + "selection.json" in result:
                    result[collector.SUCCESSOR_SOURCE_BASE + "selection.json"] += b" "
                return result
            subject.git_blobs = blobs
            with mock.patch.dict("os.environ", {"GITHUB_ACTIONS": "true", "RUNNER_OS": "Linux", "RUNNER_ARCH": "X64"}, clear=True), \
                    mock.patch.object(collector.os, "uname", return_value=collector.os.uname_result(("Linux", "control", "0", "0", "x86_64"))):
                with self.assertRaisesRegex(collector.CollectorError, "selection pin mismatch"): subject.collect()
            self.assertFalse(any(argv[0] == "docker" for argv in calls))


class SuccessorSourceSelectionControls(unittest.TestCase):
    DIGEST = "4d2eefb1fe856f83507fc643c46ba9f2171b5f11810ffad3942c345b209e9eab"
    SELECTION = "bfeca22fb174a283206c8b9db0ffd858ba52849444384eeea62b728717b24272"

    def metadata(self):
        root = COLLECTOR_PATH.resolve().parents[2]
        return {collector.SUCCESSOR_SOURCE_BASE + name: (root / collector.SUCCESSOR_SOURCE_BASE / name).read_bytes()
                for name in ("selection.json", "selected-source-manifest.json")}

    def test_current_actual_source_has_independent_closed_root(self):
        result = collector.validate_successor_source_metadata(self.metadata())
        self.assertEqual((190, self.DIGEST), (result["selected"]["source_count"], result["selected"]["source_digest_sha256"]))
        with self.assertRaises(collector.CollectorError):
            collector.check_successor_source(COLLECTOR_PATH.resolve().parents[2])

    def test_historical_and_successor_source_authority_are_distinct(self):
        collector.validate_source_manifest(copy.deepcopy(collector.FROZEN_MANIFEST))
        collector.validate_successor_source_manifest(copy.deepcopy(collector.SUCCESSOR_MANIFEST))
        with self.assertRaises(collector.CollectorError): collector.validate_successor_source_manifest(collector.FROZEN_MANIFEST)
        with self.assertRaises(collector.CollectorError): collector.validate_source_manifest(collector.SUCCESSOR_MANIFEST)

    def test_successor_source_changed_missing_and_foreign_members_refuse(self):
        for path in ("hosted/lib/mixer_hosted/billing/usage_ledger.ex", "hosted/test/support/reviewed_migrations.json", "hosted/priv/repo/migrations/20261110000001_add_billing_usage_ledger.exs", "hosted/mix.lock", "hosted/lib/mixer_hosted/billing/webhook_inbox.ex",
                     "hosted/test/mixer_hosted/builds/coordinator_test.exs", "hosted/test/test_helper.exs"):
            value = copy.deepcopy(collector.SUCCESSOR_MANIFEST)
            value[path]["sha256"] = "0" * 64
            with self.subTest(path=path), self.assertRaises(collector.CollectorError): collector.validate_successor_source_manifest(value)
        value = copy.deepcopy(collector.SUCCESSOR_MANIFEST)
        value.pop("hosted/lib/mixer_hosted/billing/webhook_inbox.ex")
        with self.assertRaises(collector.CollectorError): collector.validate_successor_source_manifest(value)
        value["hosted/priv/repo/migrations/20261110000001_foreign.exs"] = {"bytes": 0, "sha256": "0" * 64}
        with self.assertRaises(collector.CollectorError): collector.validate_successor_source_manifest(value)

    def test_untrusted_source_digest_cannot_replace_current_authority(self):
        value = copy.deepcopy(collector.SUCCESSOR_MANIFEST)
        value["hosted/mix.lock"]["sha256"] = "0" * 64
        with self.assertRaises(collector.CollectorError):
            collector.validate_successor_source_manifest(value, expected_digest=canonical_digest(value), expected_count=190)

    def test_current_metadata_exact_pin_and_membership(self):
        metadata = self.metadata()
        result = collector.validate_successor_source_metadata(metadata)
        self.assertEqual(190, result["selected"]["source_count"])
        for path in metadata:
            changed = dict(metadata)
            changed[path] += b" "
            with self.subTest(path=path), self.assertRaises(collector.CollectorError): collector.validate_successor_source_metadata(changed)
        changed = dict(metadata)
        changed[collector.SUCCESSOR_SOURCE_BASE + "foreign.json"] = b"{}"
        with self.assertRaises(collector.CollectorError): collector.validate_successor_source_metadata(changed)

    def test_current_metadata_refusal_precedes_any_docker_operation(self):
        helper = CollectorMethodWiringControls()
        with tempfile.TemporaryDirectory(prefix="identity-controls-") as directory:
            subject, calls = helper._amendment_preflight_subject(directory, exact_format_metadata())
            original = subject.git_blobs
            def blobs(paths):
                result = original(paths)
                if collector.SUCCESSOR_SOURCE_BASE + "selection.json" in result:
                    result[collector.SUCCESSOR_SOURCE_BASE + "selection.json"] += b" "
                return result
            subject.git_blobs = blobs
            with mock.patch.dict("os.environ", {"GITHUB_ACTIONS": "true", "RUNNER_OS": "Linux", "RUNNER_ARCH": "X64"}, clear=True), \
                    mock.patch.object(collector.os, "uname", return_value=collector.os.uname_result(("Linux", "control", "0", "0", "x86_64"))):
                with self.assertRaisesRegex(collector.CollectorError, "selection pin mismatch"): subject.collect()
            self.assertFalse(any(argv[0] == "docker" for argv in calls))


class PrivateSourceSelectionControls(unittest.TestCase):
    DIGEST = "458b1eefe69c390a10676690434ee05fdfecda11a430347844f855bfc2be3b3c"
    SELECTION = "37ce1ac2ce60e65fa51bc3c99417cc2ee666edaa114e7e9c3cdafe17fd468a02"

    def metadata(self):
        root = COLLECTOR_PATH.resolve().parents[2]
        return {collector.PRIVATE_SOURCE_BASE + name: (root / collector.PRIVATE_SOURCE_BASE / name).read_bytes()
                for name in ("selection.json", "selected-source-manifest.json")}

    def test_private_actual_source_has_independent_closed_root(self):
        value = collector.validate_private_source_metadata(self.metadata())
        result = {"source_count": value["selected"]["source_count"], "source_digest_sha256": value["selected"]["source_digest_sha256"], "selection_sha256": self.SELECTION, "runtime_or_GA_accepted": value["runtime_or_GA_accepted"]}
        with self.assertRaises(collector.CollectorError):
            collector.check_private_source(COLLECTOR_PATH.resolve().parents[2])
        self.assertEqual((201, self.DIGEST, self.SELECTION), (result["source_count"], result["source_digest_sha256"], result["selection_sha256"]))
        self.assertFalse(result["runtime_or_GA_accepted"])

    def test_historical_and_private_source_authority_are_distinct(self):
        collector.validate_source_manifest(copy.deepcopy(collector.FROZEN_MANIFEST))
        collector.validate_private_source_manifest(copy.deepcopy(collector.PRIVATE_MANIFEST))
        with self.assertRaises(collector.CollectorError): collector.validate_private_source_manifest(collector.FROZEN_MANIFEST)
        with self.assertRaises(collector.CollectorError): collector.validate_source_manifest(collector.PRIVATE_MANIFEST)

    def test_private_source_changed_missing_and_foreign_members_refuse(self):
        for path in ("hosted/lib/mixer_hosted/builds/operation_admission.ex", "hosted/priv/unselected_operation_admission/04_admission_function.sql", "hosted/test/mixer_hosted/builds/operation_admission_test.exs", "hosted/lib/mixer_hosted/billing/subscription_read_transport.ex", "hosted/test/mixer_hosted/billing/subscription_read_transport_test.exs", "hosted/lib/mixer_hosted/billing/usage_ledger.ex", "hosted/test/support/reviewed_migrations.json", "hosted/priv/repo/migrations/20261110000001_add_billing_usage_ledger.exs", "hosted/mix.lock", "hosted/lib/mixer_hosted/billing/webhook_inbox.ex",
                     "hosted/test/mixer_hosted/builds/coordinator_test.exs", "hosted/test/test_helper.exs"):
            value = copy.deepcopy(collector.PRIVATE_MANIFEST)
            value[path]["sha256"] = "0" * 64
            with self.subTest(path=path), self.assertRaises(collector.CollectorError): collector.validate_private_source_manifest(value)
        value = copy.deepcopy(collector.PRIVATE_MANIFEST)
        value.pop("hosted/lib/mixer_hosted/billing/webhook_inbox.ex")
        with self.assertRaises(collector.CollectorError): collector.validate_private_source_manifest(value)
        value["hosted/priv/repo/migrations/20261110000001_foreign.exs"] = {"bytes": 0, "sha256": "0" * 64}
        with self.assertRaises(collector.CollectorError): collector.validate_private_source_manifest(value)

    def test_untrusted_source_digest_cannot_replace_private_authority(self):
        value = copy.deepcopy(collector.PRIVATE_MANIFEST)
        value["hosted/mix.lock"]["sha256"] = "0" * 64
        with self.assertRaises(collector.CollectorError):
            collector.validate_private_source_manifest(value, expected_digest=canonical_digest(value), expected_count=201)

    def test_private_metadata_exact_pin_and_membership(self):
        metadata = self.metadata()
        result = collector.validate_private_source_metadata(metadata)
        self.assertEqual(201, result["selected"]["source_count"])
        for path in metadata:
            changed = dict(metadata)
            changed[path] += b" "
            with self.subTest(path=path), self.assertRaises(collector.CollectorError): collector.validate_private_source_metadata(changed)
        changed = dict(metadata)
        changed[collector.PRIVATE_SOURCE_BASE + "foreign.json"] = b"{}"
        with self.assertRaises(collector.CollectorError): collector.validate_private_source_metadata(changed)

    def test_private_metadata_refusal_precedes_any_docker_operation(self):
        helper = CollectorMethodWiringControls()
        with tempfile.TemporaryDirectory(prefix="identity-controls-") as directory:
            subject, calls = helper._amendment_preflight_subject(directory, exact_format_metadata())
            original = subject.git_blobs
            def blobs(paths):
                result = original(paths)
                if collector.PRIVATE_SOURCE_BASE + "selection.json" in result:
                    result[collector.PRIVATE_SOURCE_BASE + "selection.json"] += b" "
                return result
            subject.git_blobs = blobs
            with mock.patch.dict("os.environ", {"GITHUB_ACTIONS": "true", "RUNNER_OS": "Linux", "RUNNER_ARCH": "X64"}, clear=True), \
                    mock.patch.object(collector.os, "uname", return_value=collector.os.uname_result(("Linux", "control", "0", "0", "x86_64"))):
                with self.assertRaisesRegex(collector.CollectorError, "selection pin mismatch"): subject.collect()
            self.assertFalse(any(argv[0] == "docker" for argv in calls))



class BrowserSourceSelectionControls(unittest.TestCase):
    def metadata(self):
        root = COLLECTOR_PATH.resolve().parents[2]
        return {collector.BROWSER_SOURCE_BASE + name: (root / collector.BROWSER_SOURCE_BASE / name).read_bytes()
                for name in ("selection.json", "selected-source-manifest.json")}

    def test_actual_source_count_and_digest_match_independently_pinned_metadata(self):
        metadata = self.metadata()
        body = metadata[collector.BROWSER_SOURCE_BASE + "selection.json"]
        self.assertEqual('7ebc5dd2f3eaf093442ecee1bf26078023d934cc62c216b90aa417cee86331cf', hashlib.sha256(body).hexdigest())
        selected = json.loads(body)["selected"]
        with self.assertRaises(collector.CollectorError):
            collector.check_browser_source(COLLECTOR_PATH.resolve().parents[2])
        result = {"source_count": collector.BROWSER_SOURCE_COUNT, "source_digest_sha256": collector.BROWSER_SOURCE_DIGEST, "selection_sha256": collector.BROWSER_SELECTION_SHA256, "runtime_or_GA_accepted": False}
        self.assertEqual(selected["source_count"], result["source_count"])
        self.assertEqual('e35af32a6ebaafec4d9154ca2d04bdb0655cdd57ad5c7e06988db8e1aa65477d', result["source_digest_sha256"])
        self.assertEqual('7ebc5dd2f3eaf093442ecee1bf26078023d934cc62c216b90aa417cee86331cf', result["selection_sha256"])
        self.assertFalse(result["runtime_or_GA_accepted"])

    def test_every_changed_missing_extra_and_self_recomputed_source_refuses(self):
        for path in collector.BROWSER_MANIFEST:
            value = copy.deepcopy(collector.BROWSER_MANIFEST)
            value[path]["sha256"] = "0" * 64
            with self.subTest(path=path), self.assertRaises(collector.CollectorError):
                collector.validate_browser_source_manifest(value)
        for value in ({}, {**collector.BROWSER_MANIFEST, "hosted/foreign": {"bytes":0,"sha256":"0"*64}}):
            with self.assertRaises(collector.CollectorError): collector.validate_browser_source_manifest(value)
            with self.assertRaises(collector.CollectorError): collector.validate_browser_source_manifest(value, expected_digest=canonical_digest(value), expected_count=len(value))
        value = dict(collector.BROWSER_MANIFEST); value.pop(next(iter(value)))
        with self.assertRaises(collector.CollectorError): collector.validate_browser_source_manifest(value)
        for old in (collector.FROZEN_MANIFEST, collector.CURRENT_MANIFEST, collector.SUCCESSOR_MANIFEST, collector.PRIVATE_MANIFEST):
            with self.assertRaises(collector.CollectorError): collector.validate_browser_source_manifest(old)

    def test_missing_changed_extra_metadata_refuses(self):
        metadata = self.metadata()
        collector.validate_browser_source_metadata(metadata)
        for path in metadata:
            for mode in ("change", "missing"):
                value = dict(metadata)
                if mode == "change": value[path] += b" "
                else: value.pop(path)
                with self.subTest(path=path, mode=mode), self.assertRaises(collector.CollectorError): collector.validate_browser_source_metadata(value)
        with self.assertRaises(collector.CollectorError): collector.validate_browser_source_metadata({**metadata,"foreign": b"{}"})

    def test_browser_metadata_refusal_precedes_any_docker_operation(self):
        helper = CollectorMethodWiringControls()
        with tempfile.TemporaryDirectory(prefix="identity-controls-") as directory:
            subject, calls = helper._amendment_preflight_subject(directory, exact_format_metadata())
            original = subject.git_blobs
            def blobs(paths):
                result = original(paths)
                if collector.BROWSER_SOURCE_BASE + "selection.json" in result:
                    result[collector.BROWSER_SOURCE_BASE + "selection.json"] += b" "
                return result
            subject.git_blobs = blobs
            with mock.patch.dict("os.environ", {"GITHUB_ACTIONS": "true", "RUNNER_OS": "Linux", "RUNNER_ARCH": "X64"}, clear=True), \
                    mock.patch.object(collector.os, "uname", return_value=collector.os.uname_result(("Linux", "control", "0", "0", "x86_64"))):
                with self.assertRaisesRegex(collector.CollectorError, "selection pin mismatch"): subject.collect()
            self.assertFalse(any(argv[0] == "docker" for argv in calls))


class OperationSourceSelectionControls(unittest.TestCase):
    def metadata(self):
        root = COLLECTOR_PATH.resolve().parents[2]
        return {collector.OPERATION_SOURCE_BASE + name: (root / collector.OPERATION_SOURCE_BASE / name).read_bytes()
                for name in ("selection.json", "selected-source-manifest.json")}

    def test_actual_source_count_and_digest_match_independently_pinned_metadata(self):
        metadata = self.metadata()
        body = metadata[collector.OPERATION_SOURCE_BASE + "selection.json"]
        self.assertEqual('b204f4cda567bceedf47f4f23d2466c77a9a99bb071cd1cde1d22723c6825969', hashlib.sha256(body).hexdigest())
        selected = json.loads(body)["selected"]
        with self.assertRaises(collector.CollectorError):
            collector.check_operation_source(COLLECTOR_PATH.resolve().parents[2])
        result = {**collector.validate_operation_source_metadata(metadata)["selected"], "selection_sha256": hashlib.sha256(body).hexdigest(), "runtime_or_GA_accepted": collector.validate_operation_source_metadata(metadata)["runtime_or_GA_accepted"]}
        self.assertEqual(selected["source_count"], result["source_count"])
        self.assertEqual('9514758b76335408231b72c1a9da06b55cce77b75c47bb79d153afb5e3ca7552', result["source_digest_sha256"])
        self.assertEqual('b204f4cda567bceedf47f4f23d2466c77a9a99bb071cd1cde1d22723c6825969', result["selection_sha256"])
        self.assertFalse(result["runtime_or_GA_accepted"])

    def test_every_changed_missing_extra_and_self_recomputed_source_refuses(self):
        for path in collector.OPERATION_MANIFEST:
            value = copy.deepcopy(collector.OPERATION_MANIFEST)
            value[path]["sha256"] = "0" * 64
            with self.subTest(path=path), self.assertRaises(collector.CollectorError):
                collector.validate_operation_source_manifest(value)
        for value in ({}, {**collector.OPERATION_MANIFEST, "hosted/foreign": {"bytes":0,"sha256":"0"*64}}):
            with self.assertRaises(collector.CollectorError): collector.validate_operation_source_manifest(value)
            with self.assertRaises(collector.CollectorError): collector.validate_operation_source_manifest(value, expected_digest=canonical_digest(value), expected_count=len(value))
        value = dict(collector.OPERATION_MANIFEST); value.pop(next(iter(value)))
        with self.assertRaises(collector.CollectorError): collector.validate_operation_source_manifest(value)
        for old in (collector.FROZEN_MANIFEST, collector.CURRENT_MANIFEST, collector.SUCCESSOR_MANIFEST, collector.PRIVATE_MANIFEST, collector.BROWSER_MANIFEST):
            with self.assertRaises(collector.CollectorError): collector.validate_operation_source_manifest(old)

    def test_missing_changed_extra_metadata_refuses(self):
        metadata = self.metadata()
        collector.validate_operation_source_metadata(metadata)
        for path in metadata:
            for mode in ("change", "missing"):
                value = dict(metadata)
                if mode == "change": value[path] += b" "
                else: value.pop(path)
                with self.subTest(path=path, mode=mode), self.assertRaises(collector.CollectorError): collector.validate_operation_source_metadata(value)
        with self.assertRaises(collector.CollectorError): collector.validate_operation_source_metadata({**metadata,"foreign": b"{}"})

    def test_operation_metadata_refusal_precedes_any_docker_operation(self):
        helper = CollectorMethodWiringControls()
        with tempfile.TemporaryDirectory(prefix="identity-controls-") as directory:
            subject, calls = helper._amendment_preflight_subject(directory, exact_format_metadata())
            original = subject.git_blobs
            def blobs(paths):
                result = original(paths)
                if collector.OPERATION_SOURCE_BASE + "selection.json" in result:
                    result[collector.OPERATION_SOURCE_BASE + "selection.json"] += b" "
                return result
            subject.git_blobs = blobs
            with mock.patch.dict("os.environ", {"GITHUB_ACTIONS": "true", "RUNNER_OS": "Linux", "RUNNER_ARCH": "X64"}, clear=True), \
                    mock.patch.object(collector.os, "uname", return_value=collector.os.uname_result(("Linux", "control", "0", "0", "x86_64"))):
                with self.assertRaisesRegex(collector.CollectorError, "selection pin mismatch"): subject.collect()
            self.assertFalse(any(argv[0] == "docker" for argv in calls))


class LifetimeSourceSelectionControls(unittest.TestCase):
    def metadata(self):
        root = COLLECTOR_PATH.resolve().parents[2]
        return {collector.LIFETIME_SOURCE_BASE + name: (root / collector.LIFETIME_SOURCE_BASE / name).read_bytes()
                for name in ("selection.json", "selected-source-manifest.json")}

    def test_actual_source_count_and_digest_match_independently_pinned_metadata(self):
        metadata = self.metadata()
        body = metadata[collector.LIFETIME_SOURCE_BASE + "selection.json"]
        self.assertEqual('243a0cbb98f15f048d0d12dbf5d6fb5ff89e616d0f21dd0dba786fe8fac1e211', hashlib.sha256(body).hexdigest())
        selected = json.loads(body)["selected"]
        with self.assertRaises(collector.CollectorError):
            collector.check_lifetime_source(COLLECTOR_PATH.resolve().parents[2])
        result = {**collector.validate_lifetime_source_metadata(metadata)["selected"], "selection_sha256": hashlib.sha256(body).hexdigest(), "runtime_or_GA_accepted": collector.validate_lifetime_source_metadata(metadata)["runtime_or_GA_accepted"]}
        self.assertEqual(selected["source_count"], result["source_count"])
        self.assertEqual('2cdc4df04d645fee0ca7d6e33aa02d96d02b8bc7cd3fb6848476d0a2bc7a7c11', result["source_digest_sha256"])
        self.assertEqual('243a0cbb98f15f048d0d12dbf5d6fb5ff89e616d0f21dd0dba786fe8fac1e211', result["selection_sha256"])
        self.assertFalse(result["runtime_or_GA_accepted"])

    def test_every_changed_missing_extra_and_self_recomputed_source_refuses(self):
        for path in collector.LIFETIME_MANIFEST:
            value = copy.deepcopy(collector.LIFETIME_MANIFEST)
            value[path]["sha256"] = "0" * 64
            with self.subTest(path=path), self.assertRaises(collector.CollectorError):
                collector.validate_lifetime_source_manifest(value)
        for value in ({}, {**collector.LIFETIME_MANIFEST, "hosted/foreign": {"bytes":0,"sha256":"0"*64}}):
            with self.assertRaises(collector.CollectorError): collector.validate_lifetime_source_manifest(value)
            with self.assertRaises(collector.CollectorError): collector.validate_lifetime_source_manifest(value, expected_digest=canonical_digest(value), expected_count=len(value))
        value = dict(collector.LIFETIME_MANIFEST); value.pop(next(iter(value)))
        with self.assertRaises(collector.CollectorError): collector.validate_lifetime_source_manifest(value)
        for old in (collector.FROZEN_MANIFEST, collector.CURRENT_MANIFEST, collector.SUCCESSOR_MANIFEST, collector.PRIVATE_MANIFEST, collector.BROWSER_MANIFEST, collector.OPERATION_MANIFEST):
            with self.assertRaises(collector.CollectorError): collector.validate_lifetime_source_manifest(old)

    def test_missing_changed_extra_metadata_refuses(self):
        metadata = self.metadata()
        collector.validate_lifetime_source_metadata(metadata)
        for path in metadata:
            for mode in ("change", "missing"):
                value = dict(metadata)
                if mode == "change": value[path] += b" "
                else: value.pop(path)
                with self.subTest(path=path, mode=mode), self.assertRaises(collector.CollectorError): collector.validate_lifetime_source_metadata(value)
        with self.assertRaises(collector.CollectorError): collector.validate_lifetime_source_metadata({**metadata,"foreign": b"{}"})

    def test_lifetime_metadata_refusal_precedes_any_docker_operation(self):
        helper = CollectorMethodWiringControls()
        with tempfile.TemporaryDirectory(prefix="identity-controls-") as directory:
            subject, calls = helper._amendment_preflight_subject(directory, exact_format_metadata())
            original = subject.git_blobs
            def blobs(paths):
                result = original(paths)
                if collector.LIFETIME_SOURCE_BASE + "selection.json" in result:
                    result[collector.LIFETIME_SOURCE_BASE + "selection.json"] += b" "
                return result
            subject.git_blobs = blobs
            with mock.patch.dict("os.environ", {"GITHUB_ACTIONS": "true", "RUNNER_OS": "Linux", "RUNNER_ARCH": "X64"}, clear=True), \
                    mock.patch.object(collector.os, "uname", return_value=collector.os.uname_result(("Linux", "control", "0", "0", "x86_64"))):
                with self.assertRaisesRegex(collector.CollectorError, "selection pin mismatch"): subject.collect()
            self.assertFalse(any(argv[0] == "docker" for argv in calls))


class CommitSourceSelectionControls(unittest.TestCase):
    def metadata(self):
        root = COLLECTOR_PATH.resolve().parents[2]
        return {collector.COMMIT_SOURCE_BASE + name: (root / collector.COMMIT_SOURCE_BASE / name).read_bytes()
                for name in ("selection.json", "selected-source-manifest.json")}

    def test_actual_source_count_and_digest_match_independently_pinned_metadata(self):
        metadata = self.metadata()
        body = metadata[collector.COMMIT_SOURCE_BASE + "selection.json"]
        self.assertEqual('77406d745d798c83be28f1b26be08c3b396cee1093e4726b147ddc0a5e6b36ed', hashlib.sha256(body).hexdigest())
        selected = json.loads(body)["selected"]
        collector.validate_commit_source_metadata(metadata)
        with self.assertRaises(collector.CollectorError):
            collector.check_commit_source(COLLECTOR_PATH.resolve().parents[2])
        result = {**selected, "selection_sha256": collector.COMMIT_SELECTION_SHA256, "runtime_or_GA_accepted": False}
        self.assertEqual(selected["source_count"], result["source_count"])
        self.assertEqual('619e21ed7669a1b5782c6c4ccc4e0647aaba20433002ab8b4045e0d57df9891c', result["source_digest_sha256"])
        self.assertEqual('77406d745d798c83be28f1b26be08c3b396cee1093e4726b147ddc0a5e6b36ed', result["selection_sha256"])
        self.assertFalse(result["runtime_or_GA_accepted"])

    def test_every_changed_missing_extra_and_self_recomputed_source_refuses(self):
        for path in collector.COMMIT_MANIFEST:
            value = copy.deepcopy(collector.COMMIT_MANIFEST)
            value[path]["sha256"] = "0" * 64
            with self.subTest(path=path), self.assertRaises(collector.CollectorError):
                collector.validate_commit_source_manifest(value)
        for value in ({}, {**collector.COMMIT_MANIFEST, "hosted/foreign": {"bytes":0,"sha256":"0"*64}}):
            with self.assertRaises(collector.CollectorError): collector.validate_commit_source_manifest(value)
            with self.assertRaises(collector.CollectorError): collector.validate_commit_source_manifest(value, expected_digest=canonical_digest(value), expected_count=len(value))
        value = dict(collector.COMMIT_MANIFEST); value.pop(next(iter(value)))
        with self.assertRaises(collector.CollectorError): collector.validate_commit_source_manifest(value)
        for old in (collector.FROZEN_MANIFEST, collector.CURRENT_MANIFEST, collector.SUCCESSOR_MANIFEST, collector.PRIVATE_MANIFEST, collector.BROWSER_MANIFEST, collector.OPERATION_MANIFEST, collector.LIFETIME_MANIFEST):
            with self.assertRaises(collector.CollectorError): collector.validate_commit_source_manifest(old)

    def test_missing_changed_extra_metadata_refuses(self):
        metadata = self.metadata()
        collector.validate_commit_source_metadata(metadata)
        for path in metadata:
            for mode in ("change", "missing"):
                value = dict(metadata)
                if mode == "change": value[path] += b" "
                else: value.pop(path)
                with self.subTest(path=path, mode=mode), self.assertRaises(collector.CollectorError): collector.validate_commit_source_metadata(value)
        with self.assertRaises(collector.CollectorError): collector.validate_commit_source_metadata({**metadata,"foreign": b"{}"})

    def test_commit_metadata_refusal_precedes_any_docker_operation(self):
        helper = CollectorMethodWiringControls()
        with tempfile.TemporaryDirectory(prefix="identity-controls-") as directory:
            subject, calls = helper._amendment_preflight_subject(directory, exact_format_metadata())
            original = subject.git_blobs
            def blobs(paths):
                result = original(paths)
                if collector.COMMIT_SOURCE_BASE + "selection.json" in result:
                    result[collector.COMMIT_SOURCE_BASE + "selection.json"] += b" "
                return result
            subject.git_blobs = blobs
            with mock.patch.dict("os.environ", {"GITHUB_ACTIONS": "true", "RUNNER_OS": "Linux", "RUNNER_ARCH": "X64"}, clear=True), \
                    mock.patch.object(collector.os, "uname", return_value=collector.os.uname_result(("Linux", "control", "0", "0", "x86_64"))):
                with self.assertRaisesRegex(collector.CollectorError, "selection pin mismatch"): subject.collect()
            self.assertFalse(any(argv[0] == "docker" for argv in calls))


class ProxySourceSelectionControls(unittest.TestCase):
    def metadata(self):
        root = COLLECTOR_PATH.resolve().parents[2]
        return {collector.PROXY_SOURCE_BASE + name: (root / collector.PROXY_SOURCE_BASE / name).read_bytes()
                for name in ("selection.json", "selected-source-manifest.json")}

    def test_actual_source_count_and_digest_match_independently_pinned_metadata(self):
        metadata = self.metadata()
        body = metadata[collector.PROXY_SOURCE_BASE + "selection.json"]
        self.assertEqual('a5ade3b244f15d610b141eee05dc0c754adbb7e9fcaf71dca52b0100939124fb', hashlib.sha256(body).hexdigest())
        selected = json.loads(body)["selected"]
        collector.validate_proxy_source_metadata(metadata)
        with self.assertRaises(collector.CollectorError):
            collector.check_proxy_source(COLLECTOR_PATH.resolve().parents[2])
        result = {**selected, "selection_sha256": collector.PROXY_SELECTION_SHA256, "runtime_or_GA_accepted": False}
        self.assertEqual(selected["source_count"], result["source_count"])
        self.assertEqual('cd8dfff529b3e461adbea1fec2b21dbbb0ece6ba323a26f63d5b3676cbd41c6f', result["source_digest_sha256"])
        self.assertEqual('a5ade3b244f15d610b141eee05dc0c754adbb7e9fcaf71dca52b0100939124fb', result["selection_sha256"])
        self.assertFalse(result["runtime_or_GA_accepted"])

    def test_every_changed_missing_extra_and_self_recomputed_source_refuses(self):
        for path in collector.PROXY_MANIFEST:
            value = copy.deepcopy(collector.PROXY_MANIFEST)
            value[path]["sha256"] = "0" * 64
            with self.subTest(path=path), self.assertRaises(collector.CollectorError):
                collector.validate_proxy_source_manifest(value)
        for value in ({}, {**collector.PROXY_MANIFEST, "hosted/foreign": {"bytes":0,"sha256":"0"*64}}):
            with self.assertRaises(collector.CollectorError): collector.validate_proxy_source_manifest(value)
            with self.assertRaises(collector.CollectorError): collector.validate_proxy_source_manifest(value, expected_digest=canonical_digest(value), expected_count=len(value))
        value = dict(collector.PROXY_MANIFEST); value.pop(next(iter(value)))
        with self.assertRaises(collector.CollectorError): collector.validate_proxy_source_manifest(value)
        for old in (collector.FROZEN_MANIFEST, collector.CURRENT_MANIFEST, collector.SUCCESSOR_MANIFEST, collector.PRIVATE_MANIFEST, collector.BROWSER_MANIFEST, collector.OPERATION_MANIFEST, collector.LIFETIME_MANIFEST, collector.COMMIT_MANIFEST):
            with self.assertRaises(collector.CollectorError): collector.validate_proxy_source_manifest(old)

    def test_missing_changed_extra_metadata_refuses(self):
        metadata = self.metadata()
        collector.validate_proxy_source_metadata(metadata)
        for path in metadata:
            for mode in ("change", "missing"):
                value = dict(metadata)
                if mode == "change": value[path] += b" "
                else: value.pop(path)
                with self.subTest(path=path, mode=mode), self.assertRaises(collector.CollectorError): collector.validate_proxy_source_metadata(value)
        with self.assertRaises(collector.CollectorError): collector.validate_proxy_source_metadata({**metadata,"foreign": b"{}"})

    def test_proxy_metadata_refusal_precedes_any_docker_operation(self):
        helper = CollectorMethodWiringControls()
        with tempfile.TemporaryDirectory(prefix="identity-controls-") as directory:
            subject, calls = helper._amendment_preflight_subject(directory, exact_format_metadata())
            original = subject.git_blobs
            def blobs(paths):
                result = original(paths)
                if collector.PROXY_SOURCE_BASE + "selection.json" in result:
                    result[collector.PROXY_SOURCE_BASE + "selection.json"] += b" "
                return result
            subject.git_blobs = blobs
            with mock.patch.dict("os.environ", {"GITHUB_ACTIONS": "true", "RUNNER_OS": "Linux", "RUNNER_ARCH": "X64"}, clear=True), \
                    mock.patch.object(collector.os, "uname", return_value=collector.os.uname_result(("Linux", "control", "0", "0", "x86_64"))):
                with self.assertRaisesRegex(collector.CollectorError, "selection pin mismatch"): subject.collect()
            self.assertFalse(any(argv[0] == "docker" for argv in calls))


class CustomerBuildSourceSelectionControls(unittest.TestCase):
    def metadata(self):
        root = COLLECTOR_PATH.resolve().parents[2]
        return {collector.BUILD_READ_SOURCE_BASE + name: (root / collector.BUILD_READ_SOURCE_BASE / name).read_bytes()
                for name in ("selection.json", "selected-source-manifest.json")}

    def test_actual_source_count_and_digest_match_independently_pinned_metadata(self):
        metadata = self.metadata()
        body = metadata[collector.BUILD_READ_SOURCE_BASE + "selection.json"]
        self.assertEqual('d0c51485ce5fa56a94cfea1ffaf59b0afb383356c39619058c387f56ac58328e', hashlib.sha256(body).hexdigest())
        selected = json.loads(body)["selected"]
        with self.assertRaises(collector.CollectorError):
            collector.check_customer_build_source(COLLECTOR_PATH.resolve().parents[2])
        result = {**selected, "selection_sha256": collector.BUILD_READ_SELECTION_SHA256, "runtime_or_GA_accepted": False}
        self.assertEqual(selected["source_count"], result["source_count"])
        self.assertEqual('db080c4ff0b1bde4b0a03e1dccccb8a829c9feb84206f90dcf25620bc990c168', result["source_digest_sha256"])
        self.assertEqual('d0c51485ce5fa56a94cfea1ffaf59b0afb383356c39619058c387f56ac58328e', result["selection_sha256"])
        self.assertFalse(result["runtime_or_GA_accepted"])

    def test_every_changed_missing_extra_and_self_recomputed_source_refuses(self):
        for path in collector.BUILD_READ_MANIFEST:
            value = copy.deepcopy(collector.BUILD_READ_MANIFEST)
            value[path]["sha256"] = "0" * 64
            with self.subTest(path=path), self.assertRaises(collector.CollectorError):
                collector.validate_customer_build_source_manifest(value)
        for value in ({}, {**collector.BUILD_READ_MANIFEST, "hosted/foreign": {"bytes":0,"sha256":"0"*64}}):
            with self.assertRaises(collector.CollectorError): collector.validate_customer_build_source_manifest(value)
            with self.assertRaises(collector.CollectorError): collector.validate_customer_build_source_manifest(value, expected_digest=canonical_digest(value), expected_count=len(value))
        value = dict(collector.BUILD_READ_MANIFEST); value.pop(next(iter(value)))
        with self.assertRaises(collector.CollectorError): collector.validate_customer_build_source_manifest(value)
        for old in (collector.FROZEN_MANIFEST, collector.CURRENT_MANIFEST, collector.SUCCESSOR_MANIFEST, collector.PRIVATE_MANIFEST, collector.BROWSER_MANIFEST, collector.OPERATION_MANIFEST, collector.LIFETIME_MANIFEST, collector.COMMIT_MANIFEST, collector.PROXY_MANIFEST):
            with self.assertRaises(collector.CollectorError): collector.validate_customer_build_source_manifest(old)

    def test_missing_changed_extra_metadata_refuses(self):
        metadata = self.metadata()
        collector.validate_customer_build_source_metadata(metadata)
        for path in metadata:
            for mode in ("change", "missing"):
                value = dict(metadata)
                if mode == "change": value[path] += b" "
                else: value.pop(path)
                with self.subTest(path=path, mode=mode), self.assertRaises(collector.CollectorError): collector.validate_customer_build_source_metadata(value)
        with self.assertRaises(collector.CollectorError): collector.validate_customer_build_source_metadata({**metadata,"foreign": b"{}"})

    def test_customer_build_metadata_refusal_precedes_any_docker_operation(self):
        helper = CollectorMethodWiringControls()
        with tempfile.TemporaryDirectory(prefix="identity-controls-") as directory:
            subject, calls = helper._amendment_preflight_subject(directory, exact_format_metadata())
            original = subject.git_blobs
            def blobs(paths):
                result = original(paths)
                if collector.BUILD_READ_SOURCE_BASE + "selection.json" in result:
                    result[collector.BUILD_READ_SOURCE_BASE + "selection.json"] += b" "
                return result
            subject.git_blobs = blobs
            with mock.patch.dict("os.environ", {"GITHUB_ACTIONS": "true", "RUNNER_OS": "Linux", "RUNNER_ARCH": "X64"}, clear=True), \
                    mock.patch.object(collector.os, "uname", return_value=collector.os.uname_result(("Linux", "control", "0", "0", "x86_64"))):
                with self.assertRaisesRegex(collector.CollectorError, "selection pin mismatch"): subject.collect()
            self.assertFalse(any(argv[0] == "docker" for argv in calls))


    def test_wrong_customer_build_fixture_authority_refuses(self):
        value = copy.deepcopy(collector.BUILD_READ_MANIFEST)
        fixture = "hosted/test/support/customer_build_oban_fixture.ex"
        value[fixture] = collector.BUILD_READ_MANIFEST["hosted/test/customer_build_read_test.exs"]
        with self.assertRaises(collector.CollectorError): collector.validate_customer_build_source_manifest(value)
        with self.assertRaises(collector.CollectorError): collector.validate_customer_build_source_manifest(value, expected_digest=canonical_digest(value), expected_count=len(value))

    def test_exact_predecessor_inverse_preserves_every_v8_row(self):
        value = collector.validate_customer_build_source_metadata(self.metadata())
        inverse = dict(collector.BUILD_READ_MANIFEST)
        for path, change in value["exact_delta"].items():
            if change["before"] is None: inverse.pop(path)
            else: inverse[path] = change["before"]
        self.assertEqual(collector.PROXY_MANIFEST, inverse)
        self.assertEqual(collector.PROXY_SOURCE_DIGEST, canonical_digest(inverse))

class BrowserBuildSourceSelectionControls(unittest.TestCase):
    def metadata(self):
        root = COLLECTOR_PATH.resolve().parents[2]
        return {collector.BROWSER_BUILD_SOURCE_BASE + name: (root / collector.BROWSER_BUILD_SOURCE_BASE / name).read_bytes()
                for name in ("selection.json", "selected-source-manifest.json")}

    def test_actual_source_count_and_digest_match_independently_pinned_metadata(self):
        metadata = self.metadata()
        body = metadata[collector.BROWSER_BUILD_SOURCE_BASE + "selection.json"]
        self.assertEqual('542ceeff624ef3befd51e089cbab646cbb93242a4f48a0fae7033a8df0180f1d', hashlib.sha256(body).hexdigest())
        selected = json.loads(body)["selected"]
        root = COLLECTOR_PATH.resolve().parents[2]
        with tempfile.TemporaryDirectory(prefix="identity-controls-v10-") as directory:
            historical = Path(directory)
            import base64, zlib
            predecessor = json.loads(zlib.decompress(base64.b64decode('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')))
            source = _catalog_join_source_bytes(root)
            observed = {p: {"bytes": len(b), "sha256": hashlib.sha256(b).hexdigest()} for p, b in source.items()}
            self.assertEqual(collector.CATALOG_JOIN_MANIFEST, observed)
            for version, expected in ((13, collector.HOSTED_COMPILER_MANIFEST), (12, collector.OWNED_EVIDENCE_MANIFEST), (11, collector.BROWSER_BUILD_MANIFEST)):
                selection = json.loads((root / f"verification/identity-network-current-source-v{version}/selection.json").read_bytes())
                for relative, change in selection["exact_delta"].items():
                    body = source[relative]
                    self.assertEqual(change["after"], {"bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()})
                    if change["before"] is None:
                        source.pop(relative)
                    elif version == 13:
                        source[relative] = predecessor[relative].encode()
                    else:
                        self.assertEqual(11, version)
                        self.assertEqual("hosted/scripts/test-local.py", relative)
                        old = b'    env["R1104_POSITIVE"] = str(output / "browser-build-positive.json")\n    env["R1104_CONTROLS"] = str(output / "browser-build-controls.json")\n'
                        self.assertEqual(1, body.count(old))
                        source[relative] = body.replace(old, b"")
                observed = {p: {"bytes": len(b), "sha256": hashlib.sha256(b).hexdigest()} for p, b in source.items()}
                self.assertEqual(expected, observed)
            for relative, body in source.items():
                destination = historical / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(body)
            for relative, body in metadata.items():
                destination = historical / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(body)
            result = collector.check_browser_build_source(historical)
        self.assertEqual(selected["source_count"], result["source_count"])
        self.assertEqual('b45def2cb208ba76c5472ac49bd379278d744fc7831b2e8da59e1baf7169c505', result["source_digest_sha256"])
        self.assertEqual('542ceeff624ef3befd51e089cbab646cbb93242a4f48a0fae7033a8df0180f1d', result["selection_sha256"])
        self.assertFalse(result["runtime_or_GA_accepted"])

    def test_every_changed_missing_extra_and_self_recomputed_source_refuses(self):
        for path in collector.BROWSER_BUILD_MANIFEST:
            value = copy.deepcopy(collector.BROWSER_BUILD_MANIFEST)
            value[path]["sha256"] = "0" * 64
            with self.subTest(path=path), self.assertRaises(collector.CollectorError):
                collector.validate_browser_build_source_manifest(value)
        for value in ({}, {**collector.BROWSER_BUILD_MANIFEST, "hosted/foreign": {"bytes":0,"sha256":"0"*64}}):
            with self.assertRaises(collector.CollectorError): collector.validate_browser_build_source_manifest(value)
            with self.assertRaises(collector.CollectorError): collector.validate_browser_build_source_manifest(value, expected_digest=canonical_digest(value), expected_count=len(value))
        value = dict(collector.BROWSER_BUILD_MANIFEST); value.pop(next(iter(value)))
        with self.assertRaises(collector.CollectorError): collector.validate_browser_build_source_manifest(value)
        for old in (collector.FROZEN_MANIFEST, collector.CURRENT_MANIFEST, collector.SUCCESSOR_MANIFEST, collector.PRIVATE_MANIFEST, collector.BROWSER_MANIFEST, collector.OPERATION_MANIFEST, collector.LIFETIME_MANIFEST, collector.COMMIT_MANIFEST, collector.BUILD_READ_MANIFEST):
            with self.assertRaises(collector.CollectorError): collector.validate_browser_build_source_manifest(old)

    def test_missing_changed_extra_metadata_refuses(self):
        metadata = self.metadata()
        collector.validate_browser_build_source_metadata(metadata)
        for path in metadata:
            for mode in ("change", "missing"):
                value = dict(metadata)
                if mode == "change": value[path] += b" "
                else: value.pop(path)
                with self.subTest(path=path, mode=mode), self.assertRaises(collector.CollectorError): collector.validate_browser_build_source_metadata(value)
        with self.assertRaises(collector.CollectorError): collector.validate_browser_build_source_metadata({**metadata,"foreign": b"{}"})

    def test_customer_build_metadata_refusal_precedes_any_docker_operation(self):
        helper = CollectorMethodWiringControls()
        with tempfile.TemporaryDirectory(prefix="identity-controls-") as directory:
            subject, calls = helper._amendment_preflight_subject(directory, exact_format_metadata())
            original = subject.git_blobs
            def blobs(paths):
                result = original(paths)
                if collector.BROWSER_BUILD_SOURCE_BASE + "selection.json" in result:
                    result[collector.BROWSER_BUILD_SOURCE_BASE + "selection.json"] += b" "
                return result
            subject.git_blobs = blobs
            with mock.patch.dict("os.environ", {"GITHUB_ACTIONS": "true", "RUNNER_OS": "Linux", "RUNNER_ARCH": "X64"}, clear=True), \
                    mock.patch.object(collector.os, "uname", return_value=collector.os.uname_result(("Linux", "control", "0", "0", "x86_64"))):
                with self.assertRaisesRegex(collector.CollectorError, "selection pin mismatch"): subject.collect()
            self.assertFalse(any(argv[0] == "docker" for argv in calls))


    def test_wrong_customer_build_fixture_authority_refuses(self):
        value = copy.deepcopy(collector.BROWSER_BUILD_MANIFEST)
        fixture = "hosted/test/support/customer_build_oban_fixture.ex"
        value[fixture] = collector.BROWSER_BUILD_MANIFEST["hosted/test/customer_build_read_test.exs"]
        with self.assertRaises(collector.CollectorError): collector.validate_browser_build_source_manifest(value)
        with self.assertRaises(collector.CollectorError): collector.validate_browser_build_source_manifest(value, expected_digest=canonical_digest(value), expected_count=len(value))

    def test_exact_predecessor_inverse_preserves_every_v9_row(self):
        value = collector.validate_browser_build_source_metadata(self.metadata())
        inverse = dict(collector.BROWSER_BUILD_MANIFEST)
        for path, change in value["exact_delta"].items():
            if change["before"] is None: inverse.pop(path)
            else: inverse[path] = change["before"]
        self.assertEqual(collector.BUILD_READ_MANIFEST, inverse)
        self.assertEqual(collector.BUILD_READ_SOURCE_DIGEST, canonical_digest(inverse))



def _catalog_join_source_bytes(root):
    import base64
    source={p:(root/p).read_bytes() for p in collector.CATALOG_JOIN_MANIFEST}
    historical={"hosted/config/runtime.exs":"aW1wb3J0IENvbmZpZwoKIyBUZXN0cyBzdGFydCB0aGVpciBvd24gaXNvbGF0ZWQgc2VydmljZXMgZXhwbGljaXRseSB3aXRoIC0tbm8tc3RhcnQuIE5vcm1hbAojIHN0YXJ0dXAgYW5kIHJlbGVhc2VzIGhhdmUgbm8gZmFsbGJhY2sgY3JlZGVudGlhbHMsIGRhdGFiYXNlLCBvciBjb21iaW5lZCByb2xlLgppZiBjb25maWdfZW52KCkgIT0gOnRlc3QgZG8KICBzZXR0aW5ncyA9IE1peGVySG9zdGVkLlJ1bnRpbWVDb25maWcubG9hZCEoU3lzdGVtLmdldF9lbnYoKSkKICBjb25maWcgOm1peGVyX2hvc3RlZCwgOnJvbGUsIHNldHRpbmdzLnJvbGUKICBjb25maWcgOm1peGVyX2hvc3RlZCwgOmlkZW50aXR5X3N0YXJ0dXAsIHNldHRpbmdzLmlkZW50aXR5X3N0YXJ0dXAKICBjb25maWcgOm1peGVyX2hvc3RlZCwgTWl4ZXJIb3N0ZWQuUmVwbywgc2V0dGluZ3MucmVwbwogIGNvbmZpZyA6bWl4ZXJfaG9zdGVkLCBPYmFuLCBzZXR0aW5ncy5vYmFuCiAgY29uZmlnIDptaXhlcl9ob3N0ZWQsIE1peGVySG9zdGVkV2ViLkVuZHBvaW50LCBzZXR0aW5ncy5lbmRwb2ludAplbmQK","hosted/lib/mixer_hosted_web/browser_http.ex":"ZGVmbW9kdWxlIE1peGVySG9zdGVkV2ViLkJyb3dzZXJIVFRQIGRvCiAgQG1vZHVsZWRvYyAiUHJpdmF0ZSBmaXhlZCBicm93c2VyIHJlYWRzLiBFeHBsaWNpdCBsaXN0ZW5lciBvbmx5OyBubyBkZWZhdWx0IGFwcGxpY2F0aW9uIG1vdW50LiIKICBAYmVoYXZpb3VyIFBsdWcKICBhbGlhcyBNaXhlckhvc3RlZC5Ccm93c2VyQXV0aC57UHJvdG9jb2wsIFJ1bnRpbWVPd25lcn0KICBhbGlhcyBNaXhlckhvc3RlZFdlYi5Ccm93c2VyV29ya3NwYWNlRGlzcGF0Y2hlci5SZXF1ZXN0CiAgaW1wb3J0IFBsdWcuQ29ubgoKICBkZWYgaW5pdChbXSksIGRvOiBbXQoKICBkZWYgY2FsbChjb25uLCBbXSkgZG8KICAgIHdpdGggdHJ1ZSA8LSBjb25uLm1ldGhvZCA9PSAiR0VUIiwKICAgICAgICAgdHJ1ZSA8LQogICAgICAgICAgIGNvbm4ucmVxdWVzdF9wYXRoIGluIFsKICAgICAgICAgICAgICIvYXV0aC9zZXNzaW9uIiwKICAgICAgICAgICAgICIvY29uc29sZS1hcGkvdjEvb3JncyIsCiAgICAgICAgICAgICAiL2NvbnNvbGUtYXBpL3YxL3Byb2plY3RzIiwKICAgICAgICAgICAgICIvY29uc29sZS1hcGkvdjEvYnVpbGRzIiwKICAgICAgICAgICAgICIvY29uc29sZS1hcGkvdjEvYXBwbGljYXRpb25zIiwKICAgICAgICAgICAgICIvY29uc29sZS1hcGkvdjEvYnVpbGQtY2F0YWxvZyIKICAgICAgICAgICBdLAogICAgICAgICB7Om9rLCBffSA8LSBQcm90b2NvbC5wYXJzZV9zZXNzaW9uX2Nvb2tpZShjb25uLnJlcV9oZWFkZXJzKSwKICAgICAgICAgZmFsc2UgPC0KICAgICAgICAgICBFbnVtLmFueT8oY29ubi5yZXFfaGVhZGVycywgZm4ge2ssIHZ9IC0+CiAgICAgICAgICAgICBrID09ICJ0cmFuc2Zlci1lbmNvZGluZyIgb3IgKGsgPT0gImNvbnRlbnQtbGVuZ3RoIiBhbmQgdiAhPSAiMCIpCiAgICAgICAgICAgZW5kKSwKICAgICAgICAgezpvaywgIiIsIGNvbm59IDwtIHJlYWRfYm9keShjb25uLCBsZW5ndGg6IDAsIHJlYWRfbGVuZ3RoOiAxLCByZWFkX3RpbWVvdXQ6IDFfMDAwKSBkbwogICAgICBkaXNwYXRjaChjb25uKQogICAgZWxzZQogICAgICBfIC0+CiAgICAgICAgZXJyb3IoCiAgICAgICAgICBjb25uLAogICAgICAgICAgaWYoCiAgICAgICAgICAgIGNvbm4ubWV0aG9kID09ICJHRVQiIGFuZAogICAgICAgICAgICAgIGNvbm4ucmVxdWVzdF9wYXRoIGluIFsKICAgICAgICAgICAgICAgICIvYXV0aC9zZXNzaW9uIiwKICAgICAgICAgICAgICAgICIvY29uc29sZS1hcGkvdjEvb3JncyIsCiAgICAgICAgICAgICAgICAiL2NvbnNvbGUtYXBpL3YxL3Byb2plY3RzIiwKICAgICAgICAgICAgICAgICIvY29uc29sZS1hcGkvdjEvYnVpbGRzIiwKICAgICAgICAgICAgICAgICIvY29uc29sZS1hcGkvdjEvYXBwbGljYXRpb25zIiwKICAgICAgICAgICAgICAgICIvY29uc29sZS1hcGkvdjEvYnVpbGQtY2F0YWxvZyIKICAgICAgICAgICAgICBdLAogICAgICAgICAgICBkbzogNDAwLAogICAgICAgICAgICBlbHNlOiA0MDQKICAgICAgICAgICkKICAgICAgICApCiAgICBlbmQKICByZXNjdWUKICAgIF8gLT4gZXJyb3IoY29ubiwgNTAzKQogIGNhdGNoCiAgICBfLCBfIC0+IGVycm9yKGNvbm4sIDUwMykKICBlbmQKCiAgZGVmcCBkaXNwYXRjaCgle3JlcXVlc3RfcGF0aDogIi9hdXRoL3Nlc3Npb24iLCBxdWVyeV9zdHJpbmc6ICIifSA9IGNvbm4pIGRvCiAgICBjYXNlIFJ1bnRpbWVPd25lci5yZWFkX3Nlc3Npb24oY29ubi5yZXFfaGVhZGVycykgZG8KICAgICAgezpvaywgezp1bmF1dGhlbnRpY2F0ZWQsIGNzcmZ9LCA6dW5jaGFuZ2VkfSAtPgogICAgICAgIGlmIFByb3RvY29sLnRva2VuPyhjc3JmKSwKICAgICAgICAgIGRvOiBqc29uKGNvbm4sIDIwMCwgJXtzdGF0ZTogInVuYXV0aGVudGljYXRlZCIsIGNzcmZfdG9rZW46IGNzcmZ9KSwKICAgICAgICAgIGVsc2U6IGVycm9yKGNvbm4sIDUwMykKCiAgICAgIHs6b2ssIHs6YXV0aGVudGljYXRlZCwgY3NyZiwgcmV2aXNpb24sIGdlbmVyYXRpb24sIGV4cGlyZXN9LCA6dW5jaGFuZ2VkfQogICAgICB3aGVuIGlzX2ludGVnZXIocmV2aXNpb24pIGFuZCByZXZpc2lvbiA+PSAwIGFuZCBpc19pbnRlZ2VyKGV4cGlyZXMpIC0+CiAgICAgICAgaWYgUHJvdG9jb2wudG9rZW4/KGNzcmYpIGFuZCBQcm90b2NvbC50b2tlbj8oZ2VuZXJhdGlvbikgYW5kCiAgICAgICAgICAgICBleHBpcmVzID4gU3lzdGVtLnN5c3RlbV90aW1lKDpzZWNvbmQpLAogICAgICAgICAgIGRvOgogICAgICAgICAgICAganNvbihjb25uLCAyMDAsICV7CiAgICAgICAgICAgICAgIHN0YXRlOiAiYXV0aGVudGljYXRlZCIsCiAgICAgICAgICAgICAgIGNzcmZfdG9rZW46IGNzcmYsCiAgICAgICAgICAgICAgIGdlbmVyYXRpb246IGdlbmVyYXRpb24sCiAgICAgICAgICAgICAgIGV4cGlyZXNfYXQ6IGV4cGlyZXMKICAgICAgICAgICAgIH0pLAogICAgICAgICAgIGVsc2U6IGVycm9yKGNvbm4sIDUwMykKCiAgICAgIHs6ZXJyb3IsIDppbnZhbGlkX3JlcXVlc3R9IC0+CiAgICAgICAgZXJyb3IoY29ubiwgNDAwKQoKICAgICAgXyAtPgogICAgICAgIGVycm9yKGNvbm4sIDUwMykKICAgIGVuZAogIGVuZAoKICBkZWZwIGRpc3BhdGNoKCV7cmVxdWVzdF9wYXRoOiAiL2F1dGgvc2Vzc2lvbiJ9ID0gY29ubiksIGRvOiBlcnJvcihjb25uLCA0MDApCgogIGRlZnAgZGlzcGF0Y2goJXtyZXF1ZXN0X3BhdGg6IHBhdGh9ID0gY29ubikKICAgICAgIHdoZW4gcGF0aCBpbiBbIi9jb25zb2xlLWFwaS92MS9hcHBsaWNhdGlvbnMiLCAiL2NvbnNvbGUtYXBpL3YxL2J1aWxkLWNhdGFsb2ciXSBkbwogICAgd2l0aCB7Om9rLCByZXF1ZXN0fSA8LQogICAgICAgICAgIE1peGVySG9zdGVkV2ViLkJyb3dzZXJCdWlsZENhdGFsb2dSZXF1ZXN0LnBhcnNlKHBhdGgsIGNvbm4ucXVlcnlfc3RyaW5nKSBkbwogICAgICBjYXNlIFJ1bnRpbWVPd25lci5yZWFkX2J1aWxkX2NhdGFsb2coY29ubi5yZXFfaGVhZGVycywgcmVxdWVzdCkgZG8KICAgICAgICB7Om9rLCAle3N0YXR1czogc3RhdHVzLCBoZWFkZXJzOiBoZWFkZXJzLCBib2R5OiBib2R5fX0gLT4KICAgICAgICAgIGNvbm4gfD4gbWVyZ2VfcmVzcF9oZWFkZXJzKGhlYWRlcnMpIHw+IHNlbmRfcmVzcChzdGF0dXMsIGJvZHkpCgogICAgICAgIHs6ZXJyb3IsIDppbnZhbGlkX3JlcXVlc3R9IC0+CiAgICAgICAgICBlcnJvcihjb25uLCA0MDApCgogICAgICAgIHs6ZXJyb3IsIDp1bmF1dGhlbnRpY2F0ZWR9IC0+CiAgICAgICAgICBlcnJvcihjb25uLCA0MDEpCgogICAgICAgIF8gLT4KICAgICAgICAgIGVycm9yKGNvbm4sIDUwMykKICAgICAgZW5kCiAgICBlbHNlCiAgICAgIF8gLT4gZXJyb3IoY29ubiwgNDAwKQogICAgZW5kCiAgZW5kCgogIGRlZnAgZGlzcGF0Y2goJXtyZXF1ZXN0X3BhdGg6ICIvY29uc29sZS1hcGkvdjEvYnVpbGRzIn0gPSBjb25uKSBkbwogICAgd2l0aCB7Om9rLCBzZWxlY3Rpb259IDwtIE1peGVySG9zdGVkV2ViLkJyb3dzZXJCdWlsZFJlcXVlc3QucGFyc2UoY29ubi5xdWVyeV9zdHJpbmcpIGRvCiAgICAgIGNhc2UgUnVudGltZU93bmVyLnJlYWRfYnVpbGQoY29ubi5yZXFfaGVhZGVycywgc2VsZWN0aW9uKSBkbwogICAgICAgIHs6b2ssICV7c3RhdHVzOiBzdGF0dXMsIGhlYWRlcnM6IGhlYWRlcnMsIGJvZHk6IGJvZHl9fSAtPgogICAgICAgICAgY29ubiB8PiBtZXJnZV9yZXNwX2hlYWRlcnMoaGVhZGVycykgfD4gc2VuZF9yZXNwKHN0YXR1cywgYm9keSkKCiAgICAgICAgezplcnJvciwgOmludmFsaWRfcmVxdWVzdH0gLT4KICAgICAgICAgIGVycm9yKGNvbm4sIDQwMCkKCiAgICAgICAgezplcnJvciwgOnVuYXV0aGVudGljYXRlZH0gLT4KICAgICAgICAgIGVycm9yKGNvbm4sIDQwMSkKCiAgICAgICAgXyAtPgogICAgICAgICAgZXJyb3IoY29ubiwgNTAzKQogICAgICBlbmQKICAgIGVsc2UKICAgICAgXyAtPiBlcnJvcihjb25uLCA0MDApCiAgICBlbmQKICBlbmQKCiAgZGVmcCBkaXNwYXRjaChjb25uKSBkbwogICAgd2l0aCB7Om9rLCByZXF1ZXN0fSA8LSBxdWVyeShjb25uLnJlcXVlc3RfcGF0aCwgY29ubi5xdWVyeV9zdHJpbmcpLAogICAgICAgICB7Om9rLCBffSA8LSBSZXF1ZXN0Lm5ldyhyZXF1ZXN0KSBkbwogICAgICBjYXNlIFJ1bnRpbWVPd25lci5yZWFkX3dvcmtzcGFjZShjb25uLnJlcV9oZWFkZXJzLCByZXF1ZXN0KSBkbwogICAgICAgIHs6b2ssICV7c3RhdHVzOiBzdGF0dXMsIGhlYWRlcnM6IGhlYWRlcnMsIGJvZHk6IGJvZHl9fSAtPgogICAgICAgICAgY29ubiB8PiBtZXJnZV9yZXNwX2hlYWRlcnMoaGVhZGVycykgfD4gc2VuZF9yZXNwKHN0YXR1cywgYm9keSkKCiAgICAgICAgezplcnJvciwgOmludmFsaWRfcmVxdWVzdH0gLT4KICAgICAgICAgIGVycm9yKGNvbm4sIDQwMCkKCiAgICAgICAgezplcnJvciwgOnVuYXV0aGVudGljYXRlZH0gLT4KICAgICAgICAgIGVycm9yKGNvbm4sIDQwMSkKCiAgICAgICAgXyAtPgogICAgICAgICAgZXJyb3IoY29ubiwgNTAzKQogICAgICBlbmQKICAgIGVsc2UKICAgICAgXyAtPiBlcnJvcihjb25uLCA0MDApCiAgICBlbmQKICBlbmQKCiAgZGVmcCBxdWVyeShwYXRoLCByYXcpIHdoZW4gYnl0ZV9zaXplKHJhdykgPD0gOF8xOTIgZG8KICAgIGFsbG93ZWQgPQogICAgICBpZiBwYXRoID09ICIvY29uc29sZS1hcGkvdjEvcHJvamVjdHMiLAogICAgICAgIGRvOiB+dyhvcmdhbml6YXRpb25faWQgbGltaXQgY3Vyc29yKSwKICAgICAgICBlbHNlOiB+dyhsaW1pdCBjdXJzb3IpCgogICAgcGFpcnMgPSBpZiByYXcgPT0gIiIsIGRvOiBbXSwgZWxzZTogU3RyaW5nLnNwbGl0KHJhdywgIiYiKQoKICAgIHdpdGggdHJ1ZSA8LSBsZW5ndGgocGFpcnMpIDw9IGxlbmd0aChhbGxvd2VkKSwKICAgICAgICAgezpvaywgZmllbGRzfSA8LQogICAgICAgICAgIEVudW0ucmVkdWNlX3doaWxlKHBhaXJzLCB7Om9rLCAle319LCBmbiBwYWlyLCB7Om9rLCBhY2N9IC0+CiAgICAgICAgICAgICBjYXNlIFN0cmluZy5zcGxpdChwYWlyLCAiPSIsIHBhcnRzOiAyKSBkbwogICAgICAgICAgICAgICBbaywgdl0gLT4KICAgICAgICAgICAgICAgICBpZiBrIGluIGFsbG93ZWQgYW5kIG5vdCBNYXAuaGFzX2tleT8oYWNjLCBrKSBhbmQgdiAhPSAiIiBhbmQKICAgICAgICAgICAgICAgICAgICAgIG5vdCBSZWdleC5tYXRjaD8ofnIvJSg/IVswLTlhLWZBLUZdezJ9KS8sIHYpIGRvCiAgICAgICAgICAgICAgICAgICB7OmNvbnQsIHs6b2ssIE1hcC5wdXQoYWNjLCBrLCBVUkkuZGVjb2RlX3d3d19mb3JtKHYpKX19CiAgICAgICAgICAgICAgICAgZWxzZQogICAgICAgICAgICAgICAgICAgezpoYWx0LCA6ZXJyb3J9CiAgICAgICAgICAgICAgICAgZW5kCgogICAgICAgICAgICAgICBfIC0+CiAgICAgICAgICAgICAgICAgezpoYWx0LCA6ZXJyb3J9CiAgICAgICAgICAgICBlbmQKICAgICAgICAgICBlbmQpLAogICAgICAgICBsaW1pdCA9IE1hcC5nZXQoZmllbGRzLCAibGltaXQiLCAiNTAiKSwKICAgICAgICAgdHJ1ZSA8LQogICAgICAgICAgIGJ5dGVfc2l6ZShsaW1pdCkgaW4gMS4uMyBhbmQgRW51bS5hbGw/KDpiaW5hcnkuYmluX3RvX2xpc3QobGltaXQpLCAmKCYxIGluID8wLi4/OSkpLAogICAgICAgICB7bGltaXQsICIifSA8LSBJbnRlZ2VyLnBhcnNlKGxpbWl0KSwKICAgICAgICAgcGFnZSA9ICV7bGltaXQ6IGxpbWl0LCBjdXJzb3I6IGZpZWxkc1siY3Vyc29yIl19IGRvCiAgICAgIHs6b2ssCiAgICAgICBpZihwYXRoID09ICIvY29uc29sZS1hcGkvdjEvb3JncyIsCiAgICAgICAgIGRvOiB7Om9yZ2FuaXphdGlvbnMsIHBhZ2V9LAogICAgICAgICBlbHNlOiB7OnByb2plY3RzLCBmaWVsZHNbIm9yZ2FuaXphdGlvbl9pZCJdLCBwYWdlfQogICAgICAgKX0KICAgIGVsc2UKICAgICAgXyAtPiB7OmVycm9yLCA6aW52YWxpZF9yZXF1ZXN0fQogICAgZW5kCiAgZW5kCgogIGRlZnAgcXVlcnkoXywgXyksIGRvOiB7OmVycm9yLCA6aW52YWxpZF9yZXF1ZXN0fQoKICBkZWZwIGVycm9yKGNvbm4sIHN0YXR1cykgZG8KICAgIGNvZGUgPQogICAgICBjYXNlIHN0YXR1cyBkbwogICAgICAgIDQwMCAtPiAiaW52YWxpZF9yZXF1ZXN0IgogICAgICAgIDQwMSAtPiAidW5hdXRoZW50aWNhdGVkIgogICAgICAgIDQwNCAtPiAibm90X2ZvdW5kIgogICAgICAgIF8gLT4gImF1dGhvcml6YXRpb25fdW5hdmFpbGFibGUiCiAgICAgIGVuZAoKICAgIGNvbm4gPSBpZiBzdGF0dXMgPT0gNTAzLCBkbzogcHV0X3Jlc3BfaGVhZGVyKGNvbm4sICJyZXRyeS1hZnRlciIsICIxIiksIGVsc2U6IGNvbm4KICAgIGpzb24oY29ubiwgc3RhdHVzLCAle2Vycm9yOiAle2NvZGU6IGNvZGUsIG1lc3NhZ2U6ICJCcm93c2VyIHJlcXVlc3QgcmVmdXNlZC4ifX0pCiAgZW5kCgogIGRlZnAganNvbihjb25uLCBzdGF0dXMsIHZhbHVlKSBkbwogICAgY29ubgogICAgfD4gcHV0X3Jlc3BfaGVhZGVyKCJjYWNoZS1jb250cm9sIiwgIm5vLXN0b3JlIikKICAgIHw+IHB1dF9yZXNwX2hlYWRlcigiY29udGVudC10eXBlIiwgImFwcGxpY2F0aW9uL2pzb247IGNoYXJzZXQ9dXRmLTgiKQogICAgfD4gc2VuZF9yZXNwKHN0YXR1cywgSmFzb24uZW5jb2RlISh2YWx1ZSkpCiAgZW5kCmVuZAoKZGVmbW9kdWxlIE1peGVySG9zdGVkV2ViLkJyb3dzZXJIVFRQLlNlcnZlciBkbwogIEBtb2R1bGVkb2MgIkV4cGxpY2l0IHByaXZhdGUgbG9vcGJhY2sgSFRUUC8xIGxpc3RlbmVyOyBubyBhcmJpdHJhcnkgcGx1ZywgaG9zdCBvciByb3V0ZSBjb25maWd1cmF0aW9uLiIKICBkZWYgc3RhcnRfbGluayhbXSkgZG8KICAgIEJhbmRpdC5zdGFydF9saW5rKAogICAgICBwbHVnOiBNaXhlckhvc3RlZFdlYi5Ccm93c2VySFRUUCwKICAgICAgaXA6IHsxMjcsIDAsIDAsIDF9LAogICAgICBwb3J0OiAwLAogICAgICBzdGFydHVwX2xvZzogZmFsc2UsCiAgICAgIGh0dHBfMl9vcHRpb25zOiBbZW5hYmxlZDogZmFsc2VdLAogICAgICB3ZWJzb2NrZXRfb3B0aW9uczogW2VuYWJsZWQ6IGZhbHNlXSwKICAgICAgaHR0cF8xX29wdGlvbnM6IFsKICAgICAgICBtYXhfaGVhZGVyX2NvdW50OiA2NCwKICAgICAgICBtYXhfaGVhZGVyX2xlbmd0aDogOF8zMjAsCiAgICAgICAgbWF4X3JlcXVlc3RfbGluZV9sZW5ndGg6IDhfMzg0CiAgICAgIF0KICAgICkKICBlbmQKZW5kCg==","hosted/lib/mixer_hosted_web/browser_login_http.ex":"ZGVmbW9kdWxlIE1peGVySG9zdGVkV2ViLkJyb3dzZXJMb2dpbkhUVFAgZG8KICBAbW9kdWxlZG9jICJQcml2YXRlIG9wdC1pbiBicm93c2VyIGxvZ2luIGFkYXB0ZXIuIE5ldmVyIG1vdW50ZWQgYnkgdGhlIGFwcGxpY2F0aW9uLiIKICBAYmVoYXZpb3VyIFBsdWcKICBpbXBvcnQgUGx1Zy5Db25uCiAgYWxpYXMgTWl4ZXJIb3N0ZWQuQnJvd3NlckF1dGgue0NhbGxiYWNrTGlmZWN5Y2xlLCBQcmVhdXRoRHJhZnQsIFByb3RvY29sLCBSdW50aW1lT3duZXJ9CgogIGRlZiBpbml0KFtdKSwgZG86IFtdCgogIGRlZiBjYWxsKGNvbm4sIFtdKSBkbwogICAgY2FzZSB7Y29ubi5tZXRob2QsIGNvbm4ucmVxdWVzdF9wYXRofSBkbwogICAgICB7IkdFVCIsICIvYXV0aC9zZXNzaW9uIn0gLT4KICAgICAgICB3aXRoIHs6b2ssIG5pbH0gPC0gUHJvdG9jb2wucGFyc2Vfc2Vzc2lvbl9jb29raWUoY29ubi5yZXFfaGVhZGVycyksCiAgICAgICAgICAgICB0cnVlIDwtIGNvbm4ucXVlcnlfc3RyaW5nID09ICIiLAogICAgICAgICAgICAgezpvaywgY29ubn0gPC0gZW1wdHlfYm9keShjb25uKSBkbwogICAgICAgICAgYm9vdHN0cmFwKGNvbm4pCiAgICAgICAgZWxzZQogICAgICAgICAgezpvaywgY29va2llfSB3aGVuIGlzX2JpbmFyeShjb29raWUpIC0+IE1peGVySG9zdGVkV2ViLkJyb3dzZXJIVFRQLmNhbGwoY29ubiwgW10pCiAgICAgICAgICBfIC0+IGVycm9yKGNvbm4sIDQwMCkKICAgICAgICBlbmQKCiAgICAgIHsiUE9TVCIsICIvYXV0aC9sb2dpbiJ9IC0+CiAgICAgICAgd2l0aCB0cnVlIDwtIGNvbm4ucXVlcnlfc3RyaW5nID09ICIiLAogICAgICAgICAgICAgezpvaywgY29va2llfSB3aGVuIGlzX2JpbmFyeShjb29raWUpIDwtCiAgICAgICAgICAgICAgIFByb3RvY29sLnBhcnNlX3Nlc3Npb25fY29va2llKGNvbm4ucmVxX2hlYWRlcnMpLAogICAgICAgICAgICAgezpvaywgY29ubn0gPC0gZW1wdHlfYm9keShjb25uKSwKICAgICAgICAgICAgIHs6b2ssICVQcmVhdXRoRHJhZnQuQXV0aG9yaXphdGlvbnt1cmw6IHVybCwgZXhwaXJlc19hdDogZXhwaXJlc319IDwtCiAgICAgICAgICAgICAgIFJ1bnRpbWVPd25lci5iZWdpbl9sb2dpbihjb29raWUsIGNvbm4ucmVxX2hlYWRlcnMsIDp3b3Jrc3BhY2UsIG1ldGFkYXRhKCkpLAogICAgICAgICAgICAgdHJ1ZSA8LSBleHBpcmVzID4gU3lzdGVtLnN5c3RlbV90aW1lKDpzZWNvbmQpIGRvCiAgICAgICAgICByZWRpcmVjdChjb25uLCB1cmwpCiAgICAgICAgZWxzZQogICAgICAgICAgXyAtPiBlcnJvcihjb25uLCA1MDMpCiAgICAgICAgZW5kCgogICAgICB7IkdFVCIsICIvYXV0aC9jYWxsYmFjayJ9IC0+CiAgICAgICAgd2l0aCB7Om9rLCBffSA8LSBQcm90b2NvbC5wYXJzZV9zZXNzaW9uX2Nvb2tpZShjb25uLnJlcV9oZWFkZXJzKSwKICAgICAgICAgICAgIHs6b2ssIGNvbm59IDwtIGVtcHR5X2JvZHkoY29ubiksCiAgICAgICAgICAgICB7Om9rLCAlQ2FsbGJhY2tMaWZlY3ljbGUuUmVzdWx0e2Nvb2tpZTogY29va2llLCBleHBpcmVzX2F0OiBleHBpcmVzfX0gPC0KICAgICAgICAgICAgICAgUnVudGltZU93bmVyLmNhbGxiYWNrKGNvbm4ucmVxX2hlYWRlcnMsIGNvbm4ucXVlcnlfc3RyaW5nKSwKICAgICAgICAgICAgIHs6b2ssIHZhbHVlfSA8LSBjb29raWUoY29va2llLCBleHBpcmVzLCA5MDApIGRvCiAgICAgICAgICBjb25uIHw+IHB1dF9yZXNwX2hlYWRlcigic2V0LWNvb2tpZSIsIHZhbHVlKSB8PiByZWRpcmVjdCgiL3dvcmtzcGFjZSIpCiAgICAgICAgZWxzZQogICAgICAgICAgXyAtPiBlcnJvcihjb25uLCA1MDMpCiAgICAgICAgZW5kCgogICAgICBfIC0+CiAgICAgICAgTWl4ZXJIb3N0ZWRXZWIuQnJvd3NlckhUVFAuY2FsbChjb25uLCBbXSkKICAgIGVuZAogIHJlc2N1ZQogICAgXyAtPiBlcnJvcihjb25uLCA1MDMpCiAgY2F0Y2gKICAgIF8sIF8gLT4gZXJyb3IoY29ubiwgNTAzKQogIGVuZAoKICBkZWZwIGJvb3RzdHJhcChjb25uKSBkbwogICAgd2l0aCB7Om9rLCAlUHJlYXV0aERyYWZ0LlByZWF1dGh7Y29va2llOiBjb29raWUsIGNzcmY6IGNzcmYsIGV4cGlyZXNfYXQ6IGV4cGlyZXN9fSA8LQogICAgICAgICAgIFJ1bnRpbWVPd25lci5ib290c3RyYXAobWV0YWRhdGEoKSksCiAgICAgICAgIHs6b2ssIHZhbHVlfSA8LSBjb29raWUoY29va2llLCBleHBpcmVzLCAzMDApIGRvCiAgICAgIGNvbm4KICAgICAgfD4gcHV0X3Jlc3BfaGVhZGVyKCJzZXQtY29va2llIiwgdmFsdWUpCiAgICAgIHw+IGpzb24oMjAwLCAle3N0YXRlOiAidW5hdXRoZW50aWNhdGVkIiwgY3NyZl90b2tlbjogY3NyZn0pCiAgICBlbHNlCiAgICAgIF8gLT4gZXJyb3IoY29ubiwgNTAzKQogICAgZW5kCiAgZW5kCgogIGRlZnAgY29va2llKHRva2VuLCBleHBpcmVzLCBjYXApLAogICAgZG86IFByb3RvY29sLnNlc3Npb25fY29va2llKHRva2VuLCBtaW4oY2FwLCBleHBpcmVzIC0gU3lzdGVtLnN5c3RlbV90aW1lKDpzZWNvbmQpKSkKCiAgZGVmcCBtZXRhZGF0YSwgZG86ICV7cmVxdWVzdF9pZDogQmFzZS5lbmNvZGUxNig6Y3J5cHRvLnN0cm9uZ19yYW5kX2J5dGVzKDE2KSwgY2FzZTogOmxvd2VyKX0KCiAgZGVmcCBlbXB0eV9ib2R5KGNvbm4pIGRvCiAgICBpZiBFbnVtLmFueT8oY29ubi5yZXFfaGVhZGVycywgZm4ge2ssIHZ9IC0+CiAgICAgICAgIGsgPT0gInRyYW5zZmVyLWVuY29kaW5nIiBvciAoayA9PSAiY29udGVudC1sZW5ndGgiIGFuZCB2ICE9ICIwIikKICAgICAgIGVuZCkgZG8KICAgICAgOmVycm9yCiAgICBlbHNlCiAgICAgIGNhc2UgcmVhZF9ib2R5KGNvbm4sIGxlbmd0aDogMCwgcmVhZF9sZW5ndGg6IDEsIHJlYWRfdGltZW91dDogMV8wMDApIGRvCiAgICAgICAgezpvaywgIiIsIGNvbm59IC0+IHs6b2ssIGNvbm59CiAgICAgICAgXyAtPiA6ZXJyb3IKICAgICAgZW5kCiAgICBlbmQKICBlbmQKCiAgZGVmcCByZWRpcmVjdChjb25uLCBsb2NhdGlvbikgZG8KICAgIGNvbm4KICAgIHw+IHB1dF9yZXNwX2hlYWRlcigiY2FjaGUtY29udHJvbCIsICJuby1zdG9yZSIpCiAgICB8PiBwdXRfcmVzcF9oZWFkZXIoInJlZmVycmVyLXBvbGljeSIsICJuby1yZWZlcnJlciIpCiAgICB8PiBwdXRfcmVzcF9oZWFkZXIoImxvY2F0aW9uIiwgbG9jYXRpb24pCiAgICB8PiBzZW5kX3Jlc3AoMzAzLCAiIikKICBlbmQKCiAgZGVmcCBlcnJvcihjb25uLCBzdGF0dXMpIGRvCiAgICBjb25uCiAgICB8PiBkZWxldGVfcmVzcF9oZWFkZXIoInNldC1jb29raWUiKQogICAgfD4gZGVsZXRlX3Jlc3BfaGVhZGVyKCJsb2NhdGlvbiIpCiAgICB8PiBqc29uKHN0YXR1cywgJXsKICAgICAgZXJyb3I6ICV7Y29kZTogImF1dGhvcml6YXRpb25fdW5hdmFpbGFibGUiLCBtZXNzYWdlOiAiQnJvd3NlciByZXF1ZXN0IHJlZnVzZWQuIn0KICAgIH0pCiAgZW5kCgogIGRlZnAganNvbihjb25uLCBzdGF0dXMsIHZhbHVlKSBkbwogICAgY29ubgogICAgfD4gcHV0X3Jlc3BfaGVhZGVyKCJjYWNoZS1jb250cm9sIiwgIm5vLXN0b3JlIikKICAgIHw+IHB1dF9yZXNwX2hlYWRlcigiY29udGVudC10eXBlIiwgImFwcGxpY2F0aW9uL2pzb247IGNoYXJzZXQ9dXRmLTgiKQogICAgfD4gc2VuZF9yZXNwKHN0YXR1cywgSmFzb24uZW5jb2RlISh2YWx1ZSkpCiAgZW5kCmVuZAoKZGVmbW9kdWxlIE1peGVySG9zdGVkV2ViLkJyb3dzZXJMb2dpbkhUVFAuU2VydmVyIGRvCiAgQG1vZHVsZWRvYyAiRXhwbGljaXQgcHJpdmF0ZSBsb29wYmFjay1vbmx5IEhUVFAvMSBsaXN0ZW5lciBmb3Igc3ludGhldGljIGRldmVsb3BtZW50LiIKICBkZWYgc3RhcnRfbGluayhbXSkgZG8KICAgIEJhbmRpdC5zdGFydF9saW5rKAogICAgICBwbHVnOiBNaXhlckhvc3RlZFdlYi5Ccm93c2VyTG9naW5IVFRQLAogICAgICBpcDogezEyNywgMCwgMCwgMX0sCiAgICAgIHBvcnQ6IDAsCiAgICAgIHN0YXJ0dXBfbG9nOiBmYWxzZSwKICAgICAgaHR0cF8yX29wdGlvbnM6IFtlbmFibGVkOiBmYWxzZV0sCiAgICAgIHdlYnNvY2tldF9vcHRpb25zOiBbZW5hYmxlZDogZmFsc2VdLAogICAgICBodHRwXzFfb3B0aW9uczogWwogICAgICAgIG1heF9oZWFkZXJfY291bnQ6IDY0LAogICAgICAgIG1heF9oZWFkZXJfbGVuZ3RoOiA4XzMyMCwKICAgICAgICBtYXhfcmVxdWVzdF9saW5lX2xlbmd0aDogOF8zODQKICAgICAgXQogICAgKQogIGVuZAplbmQK","hosted/lib/mixer_hosted_web/endpoint.ex":"ZGVmbW9kdWxlIE1peGVySG9zdGVkV2ViLkVuZHBvaW50IGRvCiAgdXNlIFBob2VuaXguRW5kcG9pbnQsIG90cF9hcHA6IDptaXhlcl9ob3N0ZWQKCiAgcGx1ZyhQbHVnLlJlcXVlc3RJZCkKICBwbHVnKFBsdWcuSGVhZCkKICBwbHVnKE1peGVySG9zdGVkV2ViLlJvdXRlcikKZW5kCg==","hosted/lib/mixer_hosted/application.ex":"ZGVmbW9kdWxlIE1peGVySG9zdGVkLkFwcGxpY2F0aW9uIGRvCiAgQG1vZHVsZWRvYyBmYWxzZQogIHVzZSBBcHBsaWNhdGlvbgogIGFsaWFzIE1peGVySG9zdGVkLklkZW50aXR5LntLZXlPd25lclN1cGVydmlzb3IsIFN0YXJ0dXBDb25maWd9CgogIEBpbXBsIHRydWUKICBkZWYgc3RhcnQoX3R5cGUsIF9hcmdzKSBkbwogICAgcm9sZSA9IEFwcGxpY2F0aW9uLmZldGNoX2VudiEoOm1peGVyX2hvc3RlZCwgOnJvbGUpCgogICAgY2hpbGRyZW4gPQogICAgICBjaGlsZHJlbigKICAgICAgICByb2xlLAogICAgICAgIEFwcGxpY2F0aW9uLmZldGNoX2VudiEoOm1peGVyX2hvc3RlZCwgT2JhbiksCiAgICAgICAgQXBwbGljYXRpb24uZmV0Y2hfZW52ISg6bWl4ZXJfaG9zdGVkLCA6aWRlbnRpdHlfc3RhcnR1cCkKICAgICAgKQoKICAgIFN1cGVydmlzb3Iuc3RhcnRfbGluayhjaGlsZHJlbiwgc3RyYXRlZ3k6IDpvbmVfZm9yX29uZSwgbmFtZTogTWl4ZXJIb3N0ZWQuU3VwZXJ2aXNvcikKICBlbmQKCiAgQGRvYyBmYWxzZQogIGRlZiBjaGlsZHJlbihyb2xlLCBvYmFuKSwKICAgIGRvOiBjaGlsZHJlbihyb2xlLCBvYmFuLCAlU3RhcnR1cENvbmZpZ3ttb2RlOiA6ZGlzYWJsZWQsIG93bmVyX29wdGlvbnM6IFtdfSkKCiAgQGRvYyBmYWxzZQogIGRlZiBjaGlsZHJlbig6YXBpLCBvYmFuLCAlU3RhcnR1cENvbmZpZ3ttb2RlOiA6ZGlzYWJsZWR9KSwKICAgIGRvOiBbTWl4ZXJIb3N0ZWQuUmVwbywge09iYW4sIG9iYW59LCBNaXhlckhvc3RlZFdlYi5FbmRwb2ludF0KCiAgZGVmIGNoaWxkcmVuKDphcGksIG9iYW4sICVTdGFydHVwQ29uZmlne21vZGU6IDpjb25maWd1cmVkLCBvd25lcl9vcHRpb25zOiBvcHRpb25zfSksCiAgICBkbzogW01peGVySG9zdGVkLlJlcG8sIHtPYmFuLCBvYmFufSwge0tleU93bmVyU3VwZXJ2aXNvciwgb3B0aW9uc30sIE1peGVySG9zdGVkV2ViLkVuZHBvaW50XQoKICBkZWYgY2hpbGRyZW4oOnByb2Nlc3Nvciwgb2JhbiwgJVN0YXJ0dXBDb25maWd7bW9kZTogOmRpc2FibGVkfSksCiAgICBkbzogW01peGVySG9zdGVkLlJlcG8sIHtPYmFuLCBvYmFufV0KCiAgQGltcGwgdHJ1ZQogIGRlZiBjb25maWdfY2hhbmdlKGNoYW5nZWQsIF9uZXcsIHJlbW92ZWQpIGRvCiAgICBpZiBBcHBsaWNhdGlvbi5mZXRjaF9lbnYhKDptaXhlcl9ob3N0ZWQsIDpyb2xlKSA9PSA6YXBpIGRvCiAgICAgIE1peGVySG9zdGVkV2ViLkVuZHBvaW50LmNvbmZpZ19jaGFuZ2UoY2hhbmdlZCwgcmVtb3ZlZCkKICAgIGVuZAoKICAgIDpvawogIGVuZAplbmQK","hosted/test/foundation_integration_test.exs":"ZGVmbW9kdWxlIE1peGVySG9zdGVkLkZvdW5kYXRpb25JbnRlZ3JhdGlvblRlc3QgZG8KICB1c2UgRXhVbml0LkNhc2UsIGFzeW5jOiBmYWxzZQogIGFsaWFzIE1peGVySG9zdGVkLntSZXBvLCBSdW50aW1lQ29uZmlnfQogIGFsaWFzIE1peGVySG9zdGVkLlRlc3QuUHJvYmVXb3JrZXIKICBAbW9kdWxldGFnIDpkYXRhYmFzZQoKICBkZWZwIGxvY2FsX3JlcG8gZG8KICAgIFsKICAgICAgaG9zdG5hbWU6ICIxMjcuMC4wLjEiLAogICAgICBwb3J0OiBTeXN0ZW0uZmV0Y2hfZW52ISgiTUlYRVJfVEVTVF9EQVRBQkFTRV9QT1JUIikgfD4gU3RyaW5nLnRvX2ludGVnZXIoKSwKICAgICAgZGF0YWJhc2U6ICJtaXhlcl9mb3VuZGF0aW9uX3Rlc3QiLAogICAgICB1c2VybmFtZTogIm1peGVyX2ZpeHR1cmUiLAogICAgICBwb29sX3NpemU6IDIsCiAgICAgIHNzbDogZmFsc2UKICAgIF0KICBlbmQKCiAgZGVmcCBzZXR0aW5ncyhyb2xlKSBkbwogICAgUnVudGltZUNvbmZpZy5sb2FkISglewogICAgICAiTUlYRVJfSE9TVEVEX1JPTEUiID0+IHJvbGUsCiAgICAgICJNSVhFUl9EQVRBQkFTRV9IT1NUIiA9PiAiZGIuZXhhbXBsZS50ZXN0IiwKICAgICAgIk1JWEVSX0RBVEFCQVNFX05BTUUiID0+ICJtaXhlcl9mb3VuZGF0aW9uX3Rlc3QiLAogICAgICAiTUlYRVJfREFUQUJBU0VfVVNFUiIgPT4gIm1peGVyX2ZpeHR1cmUiLAogICAgICAiTUlYRVJfREFUQUJBU0VfUEFTU1dPUkQiID0+ICJzeW50aGV0aWMiLAogICAgICAiTUlYRVJfU0VDUkVUX0tFWV9CQVNFIiA9PiBTdHJpbmcuZHVwbGljYXRlKCJzeW50aGV0aWMtIiwgOCkKICAgIH0pCiAgZW5kCgogIGRlZnAgYm9vdChyb2xlKSBkbwogICAgc2V0dGluZ3MgPSBzZXR0aW5ncyhyb2xlKQogICAgQXBwbGljYXRpb24ucHV0X2Vudig6bWl4ZXJfaG9zdGVkLCA6cm9sZSwgc2V0dGluZ3Mucm9sZSkKICAgIEFwcGxpY2F0aW9uLnB1dF9lbnYoOm1peGVyX2hvc3RlZCwgOmlkZW50aXR5X3N0YXJ0dXAsIHNldHRpbmdzLmlkZW50aXR5X3N0YXJ0dXApCiAgICBBcHBsaWNhdGlvbi5wdXRfZW52KDptaXhlcl9ob3N0ZWQsIFJlcG8sIGxvY2FsX3JlcG8oKSkKICAgIEFwcGxpY2F0aW9uLnB1dF9lbnYoOm1peGVyX2hvc3RlZCwgT2Jhbiwgc2V0dGluZ3Mub2JhbikKCiAgICBlbmRwb2ludCA9CiAgICAgIEFwcGxpY2F0aW9uLmdldF9lbnYoOm1peGVyX2hvc3RlZCwgTWl4ZXJIb3N0ZWRXZWIuRW5kcG9pbnQpCiAgICAgIHw+IEtleXdvcmQubWVyZ2Uoc2V0dGluZ3MuZW5kcG9pbnQpCiAgICAgIHw+IEtleXdvcmQucHV0KDpodHRwLCBpcDogezEyNywgMCwgMCwgMX0sIHBvcnQ6IDApCgogICAgQXBwbGljYXRpb24ucHV0X2Vudig6bWl4ZXJfaG9zdGVkLCBNaXhlckhvc3RlZFdlYi5FbmRwb2ludCwgZW5kcG9pbnQpCiAgICBhc3NlcnQgezpvaywgX30gPSBBcHBsaWNhdGlvbi5lbnN1cmVfYWxsX3N0YXJ0ZWQoOm1peGVyX2hvc3RlZCkKICBlbmQKCiAgdGVzdCAicmV2aWV3ZWQgbWlncmF0aW9uIG1lbWJlcnNoaXAgcmVqZWN0cyBtaXNzaW5nIGFuZCBmb3JlaWduIG1pZ3JhdGlvbnMgYmVmb3JlIGV4ZWN1dGlvbiIgZG8KICAgIHBhdGggPQogICAgICBQYXRoLmpvaW4oCiAgICAgICAgU3lzdGVtLnRtcF9kaXIhKCksCiAgICAgICAgIm1peGVyLW1pZ3JhdGlvbi1tZW1iZXJzaGlwLSN7U3lzdGVtLnVuaXF1ZV9pbnRlZ2VyKFs6cG9zaXRpdmVdKX0iCiAgICAgICkKCiAgICBGaWxlLm1rZGlyIShwYXRoKQogICAgb25fZXhpdChmbiAtPiBGaWxlLnJtX3JmIShwYXRoKSBlbmQpCiAgICBzb3VyY2UgPSBBcHBsaWNhdGlvbi5hcHBfZGlyKDptaXhlcl9ob3N0ZWQsICJwcml2L3JlcG8vbWlncmF0aW9ucyIpCgogICAgZm9yIGZpbGUgPC0gUGF0aC53aWxkY2FyZChQYXRoLmpvaW4oc291cmNlLCAiKi5leHMiKSksCiAgICAgICAgZG86IEZpbGUuY3AhKGZpbGUsIFBhdGguam9pbihwYXRoLCBQYXRoLmJhc2VuYW1lKGZpbGUpKSkKCiAgICBhc3NlcnQgOm9rID0gTWl4ZXJIb3N0ZWQuVGVzdC5NaWdyYXRpb25zLmNoZWNrX2ZpbGVzIShwYXRoKQogICAgZXh0cmEgPSBQYXRoLmpvaW4ocGF0aCwgIjIwMjYxMTEwMDAwMDAxX2ZvcmVpZ24uZXhzIikKICAgIEZpbGUud3JpdGUhKGV4dHJhLCAicmFpc2UgXCJmb3JlaWduIG1pZ3JhdGlvbiBtdXN0IG5ldmVyIGV4ZWN1dGVcIiIpCgogICAgYXNzZXJ0X3JhaXNlIFJ1bnRpbWVFcnJvciwgfnIvbWlncmF0aW9uIGZpbGVzIGRpZmZlci8sIGZuIC0+CiAgICAgIE1peGVySG9zdGVkLlRlc3QuTWlncmF0aW9ucy51cCEoUmVwbywgcGF0aCkKICAgIGVuZAoKICAgIEZpbGUucm0hKGV4dHJhKQogICAgW2ZpbGUgfCBfXSA9IFBhdGgud2lsZGNhcmQoUGF0aC5qb2luKHBhdGgsICIqLmV4cyIpKQogICAgRmlsZS5ybSEoZmlsZSkKCiAgICBhc3NlcnRfcmFpc2UgUnVudGltZUVycm9yLCB+ci9taWdyYXRpb24gZmlsZXMgZGlmZmVyLywgZm4gLT4KICAgICAgTWl4ZXJIb3N0ZWQuVGVzdC5NaWdyYXRpb25zLnVwIShSZXBvLCBwYXRoKQogICAgZW5kCiAgZW5kCgogIHNldHVwX2FsbCBkbwogICAgezpvaywgcmVwb30gPSBSZXBvLnN0YXJ0X2xpbmsobG9jYWxfcmVwbygpKQogICAgcGF0aCA9IEFwcGxpY2F0aW9uLmFwcF9kaXIoOm1peGVyX2hvc3RlZCwgInByaXYvcmVwby9taWdyYXRpb25zIikKCiAgICBNaXhlckhvc3RlZC5UZXN0Lk1pZ3JhdGlvbnMudXAhKFJlcG8sIHBhdGgpCgogICAgYXNzZXJ0IFtdID0gRWN0by5NaWdyYXRvci5ydW4oUmVwbywgcGF0aCwgOnVwLCBhbGw6IHRydWUpCgogICAgUmVwby5xdWVyeSEoCiAgICAgICJDUkVBVEUgVEFCTEUgZm91bmRhdGlvbl9wcm9iZSAoaWQgdGV4dCBQUklNQVJZIEtFWSwgZWZmZWN0IGJvb2xlYW4gTk9UIE5VTEwgREVGQVVMVCBmYWxzZSkiCiAgICApCgogICAgU3VwZXJ2aXNvci5zdG9wKHJlcG8pCiAgICA6b2sKICBlbmQKCiAgc2V0dXAgZG8KICAgIGJvb3QoImFwaSIpCiAgICBSZXBvLnF1ZXJ5ISgiVFJVTkNBVEUgZm91bmRhdGlvbl9wcm9iZSwgb2Jhbl9qb2JzIikKICAgIG9uX2V4aXQoZm4gLT4gQXBwbGljYXRpb24uc3RvcCg6bWl4ZXJfaG9zdGVkKSBlbmQpCiAgICA6b2sKICBlbmQKCiAgdGVzdCAicmVhbCBCYW5kaXQgc2VydmVzIGxpdmVuZXNzLCBoaWRlcyB1bmtub3duIHJvdXRlcywgYW5kIG5ldmVyIGRpc3BhdGNoZXMgQVBJIGpvYnMiIGRvCiAgICB7Om9rLCB7X2FkZHJlc3MsIHBvcnR9fSA9IE1peGVySG9zdGVkV2ViLkVuZHBvaW50LnNlcnZlcl9pbmZvKDpodHRwKQogICAgdXJsID0gfmMiaHR0cDovLzEyNy4wLjAuMToiICsrIEludGVnZXIudG9fY2hhcmxpc3QocG9ydCkKCiAgICBhc3NlcnQgezpvaywge3tfLCAyMDAsIF99LCBoZWFkZXJzLCBib2R5fX0gPQogICAgICAgICAgICAgOmh0dHBjLnJlcXVlc3QoOmdldCwge3VybCArKyB+YyIvaGVhbHRoL2xpdmUiLCBbXX0sIFt0aW1lb3V0OiAyXzAwMF0sIFtdKQoKICAgIGFzc2VydCBKYXNvbi5kZWNvZGUhKGJvZHkpID09ICV7InN0YXR1cyIgPT4gImFsaXZlIn0KICAgIGFzc2VydCB7fmMiY2FjaGUtY29udHJvbCIsIH5jIm5vLXN0b3JlIn0gaW4gaGVhZGVycwoKICAgIGFzc2VydCB7Om9rLCB7e18sIDQwNCwgX30sIF8sIGJvZHl9fSA9CiAgICAgICAgICAgICA6aHR0cGMucmVxdWVzdCg6Z2V0LCB7dXJsICsrIH5jIi92My9wcml2YXRlL2FydGlmYWN0cyIsIFtdfSwgW3RpbWVvdXQ6IDJfMDAwXSwgW10pCgogICAgYXNzZXJ0IEphc29uLmRlY29kZSEoYm9keSkgPT0gJXsiZXJyb3IiID0+ICV7Im1lc3NhZ2UiID0+ICJOb3QgRm91bmQifX0KICAgIGFzc2VydCB7Om9rLCBqb2J9ID0gJXsicHJvYmUiID0+ICJhcGktb25seSJ9IHw+IFByb2JlV29ya2VyLm5ldygpIHw+IE9iYW4uaW5zZXJ0KCkKICAgIGFzc2VydCBPYmFuLmNvbmZpZygpLnF1ZXVlcyA9PSBbXQogICAgYXNzZXJ0IE9iYW4uY29uZmlnKCkucGVlciA9PSB7T2Jhbi5QZWVycy5Jc29sYXRlZCwgW2xlYWRlcj86IGZhbHNlXX0KICAgIGFzc2VydCBPYmFuLmNoZWNrX3F1ZXVlKHF1ZXVlOiA6cmVsZWFzZXMpID09IG5pbAogICAgYXNzZXJ0IFJlcG8uZ2V0IShPYmFuLkpvYiwgam9iLmlkKS5zdGF0ZSA9PSAiYXZhaWxhYmxlIgogICAgYXNzZXJ0ICV7cm93czogW1swXV19ID0gUmVwby5xdWVyeSEoIlNFTEVDVCBjb3VudCgqKSBGUk9NIGZvdW5kYXRpb25fcHJvYmUiKQogIGVuZAoKICB0ZXN0ICJFY3RvIE11bHRpIGNvbW1pdHMgYSBkb21haW4gZml4dHVyZSBhbmQgYSBwZXJzaXN0ZWQgam9iIHRvZ2V0aGVyIiBkbwogICAgbXVsdGkgPQogICAgICBFY3RvLk11bHRpLm5ldygpCiAgICAgIHw+IEVjdG8uTXVsdGkucnVuKDpkb21haW4sIGZuIHJlcG8sIF8gLT4KICAgICAgICB7Om9rLCByZXBvLnF1ZXJ5ISgiSU5TRVJUIElOVE8gZm91bmRhdGlvbl9wcm9iZSAoaWQpIFZBTFVFUyAoJDEpIiwgWyJjb21taXQiXSl9CiAgICAgIGVuZCkKICAgICAgfD4gT2Jhbi5pbnNlcnQoOmpvYiwgUHJvYmVXb3JrZXIubmV3KCV7InByb2JlIiA9PiAiY29tbWl0In0pKQoKICAgIGFzc2VydCB7Om9rLCAle2pvYjogam9ifX0gPSBSZXBvLnRyYW5zYWN0aW9uKG11bHRpKQogICAgYXNzZXJ0IFJlcG8uZ2V0IShPYmFuLkpvYiwgam9iLmlkKS5hcmdzID09ICV7InByb2JlIiA9PiAiY29tbWl0In0KCiAgICBhc3NlcnQgJXtyb3dzOiBbW2ZhbHNlXV19ID0KICAgICAgICAgICAgIFJlcG8ucXVlcnkhKCJTRUxFQ1QgZWZmZWN0IEZST00gZm91bmRhdGlvbl9wcm9iZSBXSEVSRSBpZCA9ICdjb21taXQnIikKICBlbmQKCiAgdGVzdCAiRWN0byBNdWx0aSByb2xscyBiYWNrIHRoZSBhbHJlYWR5IGluc2VydGVkIGpvYiBhbmQgZG9tYWluIGZpeHR1cmUiIGRvCiAgICBtdWx0aSA9CiAgICAgIEVjdG8uTXVsdGkubmV3KCkKICAgICAgfD4gRWN0by5NdWx0aS5ydW4oOmRvbWFpbiwgZm4gcmVwbywgXyAtPgogICAgICAgIHs6b2ssIHJlcG8ucXVlcnkhKCJJTlNFUlQgSU5UTyBmb3VuZGF0aW9uX3Byb2JlIChpZCkgVkFMVUVTICgkMSkiLCBbInJvbGxiYWNrIl0pfQogICAgICBlbmQpCiAgICAgIHw+IE9iYW4uaW5zZXJ0KDpqb2IsIFByb2JlV29ya2VyLm5ldygleyJwcm9iZSIgPT4gInJvbGxiYWNrIn0pKQogICAgICB8PiBFY3RvLk11bHRpLnJ1big6cmVqZWN0LCBmbiBfcmVwbywgX2NoYW5nZXMgLT4gezplcnJvciwgOmZvcmNlZF9maXh0dXJlX2ZhaWx1cmV9IGVuZCkKCiAgICBhc3NlcnQgezplcnJvciwgOnJlamVjdCwgOmZvcmNlZF9maXh0dXJlX2ZhaWx1cmUsICV7am9iOiBffX0gPSBSZXBvLnRyYW5zYWN0aW9uKG11bHRpKQogICAgYXNzZXJ0ICV7cm93czogW1swXV19ID0gUmVwby5xdWVyeSEoIlNFTEVDVCBjb3VudCgqKSBGUk9NIGZvdW5kYXRpb25fcHJvYmUiKQogICAgYXNzZXJ0ICV7cm93czogW1swXV19ID0gUmVwby5xdWVyeSEoIlNFTEVDVCBjb3VudCgqKSBGUk9NIG9iYW5fam9icyIpCiAgZW5kCgogIHRlc3QgInByb2Nlc3NvciBjb21wbGV0ZXMgYSBkZWxheWVkIGpvYiB3aXRob3V0IGFueSBIVFRQIGVuZHBvaW50IG9yIHJlcXVlc3QiIGRvCiAgICBBcHBsaWNhdGlvbi5zdG9wKDptaXhlcl9ob3N0ZWQpCiAgICBib290KCJwcm9jZXNzb3IiKQogICAgYXNzZXJ0IFByb2Nlc3Mud2hlcmVpcyhNaXhlckhvc3RlZFdlYi5FbmRwb2ludCkgPT0gbmlsCgogICAgYXNzZXJ0IHs6b2ssIGpvYn0gPQogICAgICAgICAgICAgJXsicHJvYmUiID0+ICJkZWxheWVkIn0gfD4gUHJvYmVXb3JrZXIubmV3KHNjaGVkdWxlX2luOiAxKSB8PiBPYmFuLmluc2VydCgpCgogICAgZXZlbnR1YWxseShmbiAtPiBSZXBvLmdldCEoT2Jhbi5Kb2IsIGpvYi5pZCkuc3RhdGUgPT0gImNvbXBsZXRlZCIgZW5kKQoKICAgIGFzc2VydCAle3Jvd3M6IFtbdHJ1ZV1dfSA9CiAgICAgICAgICAgICBSZXBvLnF1ZXJ5ISgiU0VMRUNUIGVmZmVjdCBGUk9NIGZvdW5kYXRpb25fcHJvYmUgV0hFUkUgaWQgPSAnZGVsYXllZCciKQogIGVuZAoKICBkZWZwIGV2ZW50dWFsbHkoY2hlY2spIGRvCiAgICBkZWFkbGluZSA9IFN5c3RlbS5tb25vdG9uaWNfdGltZSg6bWlsbGlzZWNvbmQpICsgOF8wMDAKICAgIHBvbGwoY2hlY2ssIGRlYWRsaW5lKQogIGVuZAoKICBkZWZwIHBvbGwoY2hlY2ssIGRlYWRsaW5lKSBkbwogICAgdW5sZXNzIGNoZWNrLigpIGRvCiAgICAgIGFzc2VydCBTeXN0ZW0ubW9ub3RvbmljX3RpbWUoOm1pbGxpc2Vjb25kKSA8IGRlYWRsaW5lLAogICAgICAgICAgICAgImpvYiBkaWQgbm90IGNvbXBsZXRlIGJlZm9yZSBkZWFkbGluZSIKCiAgICAgIFByb2Nlc3Muc2xlZXAoMjApCiAgICAgIHBvbGwoY2hlY2ssIGRlYWRsaW5lKQogICAgZW5kCiAgZW5kCmVuZAo=","hosted/test/mixer_hosted/browser_auth/private_login_http_test.exs":"ZGVmbW9kdWxlIFI5NDIuUmVjZWlwdEZhdWx0IGRvCiAgZGVmIGhhbmRsZShfLCBfLCAle3F1ZXJ5OiAiYmVnaW4ifSwgOm1pc3NpbmcpIGRvCiAgICA6dGVsZW1ldHJ5LmRldGFjaCh7TWl4ZXJIb3N0ZWQuQnJvd3NlckF1dGguU3RvcmUsIDp0cmFuc2FjdGlvbl9yZWNlaXB0fSkKICBlbmQKCiAgZGVmIGhhbmRsZShfLCBfLCBfLCBfKSwgZG86IDpvawplbmQKCkNvZGUucmVxdWlyZV9maWxlKCJzdG9yYWdlX2ZpeHR1cmUuZXhzIiwgX19ESVJfXykKCmRlZm1vZHVsZSBSNjg2LkF1dGhvcml6YXRpb25IVFRQIGRvCiAgaW1wb3J0IFBsdWcuQ29ubgogIGRlZiBpbml0KG9wdHMpLCBkbzogb3B0cwoKICBkZWYgY2FsbChjb25uLCAle3Byb3ZpZGVyOiBwcm92aWRlciwgY29uZmlnOiBjb25maWd9KSBkbwogICAgaWYgY29ubi5tZXRob2QgPT0gIkdFVCIgYW5kIGNvbm4ucmVxdWVzdF9wYXRoID09ICIvYXV0aG9yaXplIiBkbwogICAgICBjb2RlID0gR2VuU2VydmVyLmNhbGwocHJvdmlkZXIsIHs6cmVnaXN0ZXIsIGNvbm4ucXVlcnlfc3RyaW5nfSkKICAgICAgc3RhdGUgPSBVUkkuZGVjb2RlX3F1ZXJ5KGNvbm4ucXVlcnlfc3RyaW5nKVsic3RhdGUiXQogICAgICBxdWVyeSA9IFVSSS5lbmNvZGVfcXVlcnkoW3sic3RhdGUiLCBzdGF0ZX0sIHsiaXNzIiwgY29uZmlnLmlzc3Vlcn0sIHsiY29kZSIsIGNvZGV9XSkKCiAgICAgIGNvbm4KICAgICAgfD4gcHV0X3Jlc3BfaGVhZGVyKCJsb2NhdGlvbiIsIGNvbmZpZy5yZWRpcmVjdF91cmkgPD4gIj8iIDw+IHF1ZXJ5KQogICAgICB8PiBzZW5kX3Jlc3AoMzAyLCAiIikKICAgIGVsc2UKICAgICAgc2VuZF9yZXNwKGNvbm4sIDQwNCwgIiIpCiAgICBlbmQKICBlbmQKZW5kCgpkZWZtb2R1bGUgUjY4Ni5Qcm92aWRlciBkbwogIHVzZSBHZW5TZXJ2ZXIKICBhbGlhcyBNaXhlckhvc3RlZC5Ccm93c2VyQXV0aC5Qcm90b2NvbAogIGRlZiBzdGFydF9saW5rKG9wdHMpLCBkbzogR2VuU2VydmVyLnN0YXJ0X2xpbmsoX19NT0RVTEVfXywgb3B0cykKICBkZWYgaW5pdChvcHRzKSwgZG86IHs6b2ssIE1hcC5tZXJnZShvcHRzLCAle2NvZGVzOiAle30sIG1vZGU6IDpvaywgY291bnQ6IDB9KX0KCiAgZGVmIGhhbmRsZV9jYWxsKHs6cmVnaXN0ZXIsIHF1ZXJ5fSwgXywgcykgZG8KICAgIHZhbHVlcyA9IFVSSS5kZWNvZGVfcXVlcnkocXVlcnkpCiAgICBjb2RlID0gUHJvdG9jb2wucmFuZG9tX3Rva2VuKCkKICAgIHs6cmVwbHksIGNvZGUsIHB1dF9pbihzLmNvZGVzW2NvZGVdLCB2YWx1ZXMpfQogIGVuZAoKICBkZWYgaGFuZGxlX2NhbGwoezptb2RlLCBtb2RlfSwgXywgcyksIGRvOiB7OnJlcGx5LCA6b2ssICV7cyB8IG1vZGU6IG1vZGV9fQogIGRlZiBoYW5kbGVfY2FsbCg6Y291bnQsIF8sIHMpLCBkbzogezpyZXBseSwgcy5jb3VudCwgc30KCiAgZGVmIGhhbmRsZV9jYWxsKHs6ZXhjaGFuZ2UsIHJ9LCBfLCBzKSBkbwogICAge3YsIGNvZGVzfSA9IE1hcC5wb3Aocy5jb2Rlcywgci5jb2RlKQogICAgcyA9ICV7cyB8IGNvZGVzOiBjb2RlcywgY291bnQ6IHMuY291bnQgKyAxfQoKICAgIHZhbGlkID0KICAgICAgdiAhPT0gbmlsIGFuZCByLmlzc3VlciA9PT0gcy5jb25maWcuaXNzdWVyIGFuZCByLmNsaWVudF9pZCA9PT0gdlsiY2xpZW50X2lkIl0gYW5kCiAgICAgICAgci5yZWRpcmVjdF91cmkgPT09IHZbInJlZGlyZWN0X3VyaSJdIGFuZCByLnRva2VuX2VuZHBvaW50ID09PSBzLmNvbmZpZy50b2tlbl9lbmRwb2ludCBhbmQKICAgICAgICByLmdyYW50X3R5cGUgPT09ICJhdXRob3JpemF0aW9uX2NvZGUiIGFuZCByLmNsaWVudF9hdXRoX21ldGhvZCA9PT0gOmNsaWVudF9zZWNyZXRfYmFzaWMgYW5kCiAgICAgICAgci5jbGllbnRfY3JlZGVudGlhbF9yZWYgPT09IHMuY29uZmlnLmNsaWVudF9jcmVkZW50aWFsX3JlZiBhbmQKICAgICAgICBQcm90b2NvbC5wa2NlX2NoYWxsZW5nZShyLmNvZGVfdmVyaWZpZXIpID09PSB7Om9rLCB2WyJjb2RlX2NoYWxsZW5nZSJdfQoKICAgIGNvbmQgZG8KICAgICAgbm90IHZhbGlkIG9yIHMubW9kZSA9PT0gOnBrY2UgLT4KICAgICAgICB7OnJlcGx5LCB7OmVycm9yLCA6aW52YWxpZF9ncmFudH0sIHN9CgogICAgICBzLm1vZGUgPT09IDpsYXRlIC0+CiAgICAgICAgUHJvY2Vzcy5zbGVlcCgxMTAwKQogICAgICAgIHs6cmVwbHksIHs6ZXJyb3IsIDpsYXRlfSwgc30KCiAgICAgIHRydWUgLT4KICAgICAgICBub3cgPSBTeXN0ZW0uc3lzdGVtX3RpbWUoOnNlY29uZCkKCiAgICAgICAgY2xhaW1zID0gJXsKICAgICAgICAgICJpc3MiID0+IHMuY29uZmlnLmlzc3VlciwKICAgICAgICAgICJhdWQiID0+IHMuY29uZmlnLmFwaV9hdWRpZW5jZSwKICAgICAgICAgICJzdWIiID0+ICJzdWJqZWN0LTEiLAogICAgICAgICAgImNsaWVudF9pZCIgPT4gcy5jb25maWcuY2xpZW50X2lkLAogICAgICAgICAgImlhdCIgPT4gbm93IC0gMSwKICAgICAgICAgICJleHAiID0+IG5vdyArIGlmKHMubW9kZSA9PT0gOnNob3J0LCBkbzogMiwgZWxzZTogMTIwKSwKICAgICAgICAgICJqdGkiID0+IFByb3RvY29sLnJhbmRvbV90b2tlbigpLAogICAgICAgICAgInNjb3BlIiA9PgogICAgICAgICAgICBpZihzLm1vZGUgPT0gOm5vX2J1aWxkX3Njb3BlLAogICAgICAgICAgICAgIGRvOiAibWl4ZXIud29ya3NwYWNlLnJlYWQiLAogICAgICAgICAgICAgIGVsc2U6IFN0cmluZy5yZXBsYWNlKHZbInNjb3BlIl0sICJvcGVuaWQgIiwgIiIpCiAgICAgICAgICAgICkKICAgICAgICB9CgogICAgICAgIGFjY2VzcyA9IHNpZ24ocy5rZXksIGNsYWltcywgImF0K2p3dCIpCiAgICAgICAgPDxoYWxmOjpiaW5hcnktc2l6ZSgxNiksIF86OmJpbmFyeT4+ID0gOmNyeXB0by5oYXNoKDpzaGEyNTYsIGFjY2VzcykKCiAgICAgICAgaWQgPSAlewogICAgICAgICAgImlzcyIgPT4gcy5jb25maWcuaXNzdWVyLAogICAgICAgICAgImF1ZCIgPT4gcy5jb25maWcuY2xpZW50X2lkLAogICAgICAgICAgInN1YiIgPT4gInN1YmplY3QtMSIsCiAgICAgICAgICAiaWF0IiA9PiBub3cgLSAxLAogICAgICAgICAgImV4cCIgPT4KICAgICAgICAgICAgbm93ICsKICAgICAgICAgICAgICBjYXNlIHMubW9kZSBkbwogICAgICAgICAgICAgICAgOnNob3J0IC0+IDIKICAgICAgICAgICAgICAgIDpzZXNzaW9uX3Nob3J0IC0+IDQ1CiAgICAgICAgICAgICAgICBfIC0+IDEyMAogICAgICAgICAgICAgIGVuZCwKICAgICAgICAgICJub25jZSIgPT4gdlsibm9uY2UiXSwKICAgICAgICAgICJhdF9oYXNoIiA9PiBCYXNlLnVybF9lbmNvZGU2NChoYWxmLCBwYWRkaW5nOiBmYWxzZSkKICAgICAgICB9CgogICAgICAgIGlkID0KICAgICAgICAgIGNhc2Ugcy5tb2RlIGRvCiAgICAgICAgICAgIDpub25jZSAtPiBNYXAucHV0KGlkLCAibm9uY2UiLCBQcm90b2NvbC5yYW5kb21fdG9rZW4oKSkKICAgICAgICAgICAgOmF1ZCAtPiBNYXAucHV0KGlkLCAiYXVkIiwgIndyb25nLWNsaWVudCIpCiAgICAgICAgICAgIDppc3N1ZXIgLT4gTWFwLnB1dChpZCwgImlzcyIsICJodHRwczovL3dyb25nLmV4YW1wbGUuaW52YWxpZCIpCiAgICAgICAgICAgIDpsaW5rIC0+IE1hcC5wdXQoaWQsICJhdF9oYXNoIiwgUHJvdG9jb2wucmFuZG9tX3Rva2VuKCkpCiAgICAgICAgICAgIDphenAgLT4gaWQgfD4gTWFwLnB1dCgiYXVkIiwgW3MuY29uZmlnLmNsaWVudF9pZCwgIm90aGVyIl0pIHw+IE1hcC5wdXQoImF6cCIsICJvdGhlciIpCiAgICAgICAgICAgIDpleHBpcmVkIC0+IE1hcC5wdXQoaWQsICJleHAiLCBub3cgLSAyKQogICAgICAgICAgICBfIC0+IGlkCiAgICAgICAgICBlbmQKCiAgICAgICAgdG9rZW4gPSBzaWduKGlmKHMubW9kZSA9PT0gOnNpZ25hdHVyZSwgZG86IHMud3Jvbmdfa2V5LCBlbHNlOiBzLmtleSksIGlkLCAiSldUIikKICAgICAgICBpZiBpc190dXBsZShzLm1vZGUpLCBkbzogc2VuZChlbGVtKHMubW9kZSwgMSksIHs6cHJvdmlkZXJfZXhjaGFuZ2UsIHNlbGYoKX0pCgogICAgICAgIGlmIGlzX3R1cGxlKHMubW9kZSkgZG8KICAgICAgICAgIHJlY2VpdmUgZG8KICAgICAgICAgICAgOmNvbnRpbnVlIC0+IDpvawogICAgICAgICAgYWZ0ZXIKICAgICAgICAgICAgMTUwMCAtPiA6b2sKICAgICAgICAgIGVuZAogICAgICAgIGVuZAoKICAgICAgICB7OnJlcGx5LAogICAgICAgICB7Om9rLAogICAgICAgICAgSmFzb24uZW5jb2RlISglewogICAgICAgICAgICAidG9rZW5fdHlwZSIgPT4gIkJlYXJlciIsCiAgICAgICAgICAgICJhY2Nlc3NfdG9rZW4iID0+IGFjY2VzcywKICAgICAgICAgICAgImlkX3Rva2VuIiA9PiB0b2tlbgogICAgICAgICAgfSl9LCBzfQogICAgZW5kCiAgZW5kCgogIGRlZnAgc2lnbihrLCBjLCB0KSwKICAgIGRvOgogICAgICBKT1NFLkpXUy5zaWduKGssIEphc29uLmVuY29kZSEoYyksICV7ImFsZyIgPT4gIlJTMjU2IiwgInR5cCIgPT4gdCwgImtpZCIgPT4gImtleTEifSkKICAgICAgfD4gSk9TRS5KV1MuY29tcGFjdCgpCiAgICAgIHw+IGVsZW0oMSkKZW5kCgpkZWZtb2R1bGUgUjk2Ni5Mb2dpbkZpeHR1cmUgZG8KICBhbGlhcyBNaXhlckhvc3RlZC5Ccm93c2VyQXV0aC5TdG9yYWdlRml4dHVyZSwgYXM6IE9yaWdpbmFsCiAgZGVmZGVsZWdhdGUgcG9ydCgpLCB0bzogT3JpZ2luYWwKICBkZWZkZWxlZ2F0ZSBxIShyZXBvLCBzcWwsIHBhcmFtcyBcXCBbXSksIHRvOiBPcmlnaW5hbAogIGRlZmRlbGVnYXRlIGNhbGwoY29ubiwgbmFtZSwgYXJncyksIHRvOiBPcmlnaW5hbAogIGRlZiBpbnN0YWxsISwgZG86IE9yaWdpbmFsLmluc3RhbGwhKCkKCiAgZGVmIGNvbm5lY3Rpb24hKHJvbGUgXFwgImJyb3dzZXJfbGlmZWN5Y2xlIiwgZGF0YWJhc2UgXFwgImJyb3dzZXJfbG9naW5fc3RvcmFnZSIpIGRvCiAgICB7Om9rLCBjb25ufSA9CiAgICAgIFBvc3RncmV4LnN0YXJ0X2xpbmsoCiAgICAgICAgaG9zdG5hbWU6ICIxMjcuMC4wLjEiLAogICAgICAgIHBvcnQ6IHBvcnQoKSwKICAgICAgICB1c2VybmFtZTogcm9sZSwKICAgICAgICBkYXRhYmFzZTogZGF0YWJhc2UsCiAgICAgICAgc3NsOiBmYWxzZSwKICAgICAgICBiYWNrb2ZmX3R5cGU6IDpzdG9wCiAgICAgICkKCiAgICBQcm9jZXNzLnVubGluayhjb25uKQogICAgUG9zdGdyZXgucXVlcnkhKGNvbm4sICJTRVQgc3RhdGVtZW50X3RpbWVvdXQ9JzVzJyIsIFtdKQogICAgUG9zdGdyZXgucXVlcnkhKGNvbm4sICJTRVQgbG9ja190aW1lb3V0PSc1MDBtcyciLCBbXSkKICAgIFBvc3RncmV4LnF1ZXJ5IShjb25uLCAiU0VUIGlkbGVfaW5fdHJhbnNhY3Rpb25fc2Vzc2lvbl90aW1lb3V0PSc1cyciLCBbXSkKICAgIGNvbm4KICBlbmQKCiAgZGVmIHByb3Zpc2lvbiEgZG8KICAgIGNvbm4gPSBjb25uZWN0aW9uISgiYnJvd3Nlcl9hZG1pbiIpCgogICAgdHJ5IGRvCiAgICAgIGZvciBzcWwgPC0KICAgICAgICAgICAgTWl4ZXJIb3N0ZWQuQnJvd3NlckF1dGguU3RvcmFnZVNjaGVtYS5wcm92aXNpb25pbmdfc3RhdGVtZW50cygKICAgICAgICAgICAgICAiYnJvd3Nlcl93cml0ZXIiLAogICAgICAgICAgICAgICJicm93c2VyX2xpZmVjeWNsZSIKICAgICAgICAgICAgKSwKICAgICAgICAgIGRvOiBQb3N0Z3JleC5xdWVyeSEoY29ubiwgc3FsLCBbXSkKICAgIGFmdGVyCiAgICAgIEdlblNlcnZlci5zdG9wKGNvbm4pCiAgICBlbmQKICBlbmQKZW5kCgpkZWZtb2R1bGUgTWl4ZXJIb3N0ZWQuQnJvd3NlckxvZ2luSFRUUFRlc3QgZG8KICB1c2UgRXhVbml0LkNhc2UsIGFzeW5jOiBmYWxzZQoKICBhbGlhcyBNaXhlckhvc3RlZC5Ccm93c2VyQXV0aC57CiAgICBSdW50aW1lT3duZXIsCiAgICBSdW50aW1lQ29uZmlnLAogICAgQ29uZmlnLAogICAgQ29uZmlndXJhdGlvbkRpZ2VzdCwKICAgIEN1c3RvZHksCiAgICBMaWZlY3ljbGVSZXBvLAogICAgUHJvdmlkZXJPd25lciwKICAgIEFjdGl2YXRpb25QcmVwYXJhdGlvblNjaGVtYSwKICAgIFZhdWx0LAogICAgU3RvcmVkU25hcHNob3QsCiAgICBQcm90b2NvbAogIH0KCiAgYWxpYXMgUjk2Ni5Mb2dpbkZpeHR1cmUsIGFzOiBGCiAgYWxpYXMgTWl4ZXJIb3N0ZWQuQnJvd3NlckF1dGguU3RvcmFnZUZpeHR1cmUue0FkbWluLCBNaWdyYXRpb259CiAgYWxpYXMgTWl4ZXJIb3N0ZWQuSWRlbnRpdHkue0tleU93bmVyLCBUTFNGaXh0dXJlLCBUcnVzdFNuYXBzaG90fQoKICBzZXR1cF9hbGwgZG8KICAgIGNvbm4gPSBGLmNvbm5lY3Rpb24hKCJicm93c2VyX2FkbWluIiwgInBvc3RncmVzIikKCiAgICB0cnkgZG8KICAgICAgUG9zdGdyZXgucXVlcnkhKAogICAgICAgIGNvbm4sCiAgICAgICAgIkNSRUFURSBEQVRBQkFTRSBicm93c2VyX2xvZ2luX3N0b3JhZ2UgT1dORVIgYnJvd3Nlcl9zY2hlbWFfb3duZXIiLAogICAgICAgIFtdCiAgICAgICkKICAgIGFmdGVyCiAgICAgIEdlblNlcnZlci5zdG9wKGNvbm4pCiAgICBlbmQKCiAgICBvbl9leGl0KGZuIC0+CiAgICAgIGNvbm4gPSBGLmNvbm5lY3Rpb24hKCJicm93c2VyX2FkbWluIiwgInBvc3RncmVzIikKCiAgICAgIHRyeSBkbwogICAgICAgIFBvc3RncmV4LnF1ZXJ5IShjb25uLCAiRFJPUCBEQVRBQkFTRSBicm93c2VyX2xvZ2luX3N0b3JhZ2UiLCBbXSkKICAgICAgYWZ0ZXIKICAgICAgICBHZW5TZXJ2ZXIuc3RvcChjb25uKQogICAgICBlbmQKICAgIGVuZCkKCiAgICBmb3IgYXBwIDwtIFs6ZWN0b19zcWwsIDpwb3N0Z3JleCwgOmphc29uLCA6am9zZSwgOm1pbnQsIDpzc2wsIDpiYW5kaXRdLAogICAgICAgIGRvOiBBcHBsaWNhdGlvbi5lbnN1cmVfYWxsX3N0YXJ0ZWQoYXBwKQoKICAgIHNldHRpbmdzID0gWwogICAgICBob3N0bmFtZTogIjEyNy4wLjAuMSIsCiAgICAgIHBvcnQ6IEYucG9ydCgpLAogICAgICBkYXRhYmFzZTogImJyb3dzZXJfbG9naW5fc3RvcmFnZSIsCiAgICAgIHBvb2xfc2l6ZTogMiwKICAgICAgbG9nOiBmYWxzZQogICAgXQoKICAgIHByZXZpb3VzX2FkbWluID0gQXBwbGljYXRpb24uZmV0Y2hfZW52KDpicm93c2VyX3N0b3JhZ2VfZml4dHVyZSwgQWRtaW4pCgogICAgb25fZXhpdChmbiAtPgogICAgICBjYXNlIHByZXZpb3VzX2FkbWluIGRvCiAgICAgICAgezpvaywgdmFsdWV9IC0+IEFwcGxpY2F0aW9uLnB1dF9lbnYoOmJyb3dzZXJfc3RvcmFnZV9maXh0dXJlLCBBZG1pbiwgdmFsdWUpCiAgICAgICAgOmVycm9yIC0+IEFwcGxpY2F0aW9uLmRlbGV0ZV9lbnYoOmJyb3dzZXJfc3RvcmFnZV9maXh0dXJlLCBBZG1pbikKICAgICAgZW5kCiAgICBlbmQpCgogICAgQXBwbGljYXRpb24ucHV0X2Vudig6YnJvd3Nlcl9zdG9yYWdlX2ZpeHR1cmUsIEFkbWluLCBzZXR0aW5ncyArKyBbdXNlcm5hbWU6ICJicm93c2VyX2FkbWluIl0pCgogICAgc3RhcnRfc3VwZXJ2aXNlZCEoe0FkbWluLCBzZXR0aW5ncyArKyBbdXNlcm5hbWU6ICJicm93c2VyX2FkbWluIl19KQoKICAgIHN0YXJ0X3N1cGVydmlzZWQhKAogICAgICB7TWlncmF0aW9uLAogICAgICAgc2V0dGluZ3MgKysKICAgICAgICAgWwogICAgICAgICAgIHVzZXJuYW1lOiAiYnJvd3Nlcl9hZG1pbiIsCiAgICAgICAgICAgYWZ0ZXJfY29ubmVjdDogZm4gYyAtPiBQb3N0Z3JleC5xdWVyeSEoYywgIlNFVCBST0xFIGJyb3dzZXJfc2NoZW1hX293bmVyIiwgW10pIGVuZAogICAgICAgICBdfQogICAgKQoKICAgIEYuaW5zdGFsbCEoKQogICAgRi5xIShBZG1pbiwgIkdSQU5UIFVTQUdFIE9OIFNDSEVNQSBwdWJsaWMgVE8gYnJvd3Nlcl9vcmRpbmFyeSIpCiAgICBGLnEhKEFkbWluLCAiR1JBTlQgU0VMRUNUIE9OIEFMTCBUQUJMRVMgSU4gU0NIRU1BIHB1YmxpYyBUTyBicm93c2VyX29yZGluYXJ5IikKCiAgICBmb3IgaGVscGVyIDwtIH53KHByb2ZpbGVzIHByaW5jaXBhbHMgZmFtaWxpZXMgY3JlZGVudGlhbHMgb3JnYW5pemF0aW9uX2hlYWRzIHByb2plY3RfaGVhZHMpLAogICAgICAgIGRvOgogICAgICAgICAgRi5xISgKICAgICAgICAgICAgQWRtaW4sCiAgICAgICAgICAgICJHUkFOVCBFWEVDVVRFIE9OIEZVTkNUSU9OIHB1YmxpYy5taXhlcl9hdXRoel9sb2NrXyN7aGVscGVyfSgpIFRPIGJyb3dzZXJfb3JkaW5hcnkiCiAgICAgICAgICApCgogICAgZm9yIHRhYmxlIDwtIH53KHNlc3Npb25zIHNlc3Npb25fdmF1bHQgb2lkY19hdHRlbXB0cyBzZXNzaW9uX2V2ZW50cyksCiAgICAgICAgZG86IEYucSEoQWRtaW4sICJSRVZPS0UgU0VMRUNUIE9OIHB1YmxpYy5taXhlcl9icm93c2VyXyN7dGFibGV9IEZST00gYnJvd3Nlcl9vcmRpbmFyeSIpCgogICAgZm9yIHNxbCA8LSBBY3RpdmF0aW9uUHJlcGFyYXRpb25TY2hlbWEuc3RhdGVtZW50cygpLCBkbzogRi5xIShNaWdyYXRpb24sIHNxbCkKICAgIEYucHJvdmlzaW9uISgpCiAgICBjb25uID0gRi5jb25uZWN0aW9uISgiYnJvd3Nlcl9hZG1pbiIpCgogICAgZm9yIHNxbCA8LQogICAgICAgICAgQWN0aXZhdGlvblByZXBhcmF0aW9uU2NoZW1hLnByb3Zpc2lvbmluZ19zdGF0ZW1lbnRzKAogICAgICAgICAgICAiYnJvd3Nlcl93cml0ZXIiLAogICAgICAgICAgICAiYnJvd3Nlcl9saWZlY3ljbGUiLAogICAgICAgICAgICAiYnJvd3Nlcl9zY2hlbWFfb3duZXIiCiAgICAgICAgICApLAogICAgICAgIGRvOiBQb3N0Z3JleC5xdWVyeSEoY29ubiwgc3FsLCBbXSkKCiAgICBHZW5TZXJ2ZXIuc3RvcChjb25uKQoKICAgIEYucSEoCiAgICAgIEFkbWluLAogICAgICAiSU5TRVJUIElOVE8gcHVibGljLm1peGVyX2F1dGh6X3Byb2ZpbGVzIFZBTFVFUygnaHVtYW5zJywxLCdodHRwczovL2lzc3Vlci5maXh0dXJlLmludmFsaWQnLCdjb25zb2xlJywnaHVtYW4nLHRydWUsMSkiCiAgICApCgogICAgRi5xIShBZG1pbiwgIklOU0VSVCBJTlRPIHB1YmxpYy5taXhlcl9hdXRoel9wcmluY2lwYWxzIFZBTFVFUygncGVyc29uLTEnLCdodW1hbicsdHJ1ZSwwLDEpIikKCiAgICBGLnEhKAogICAgICBBZG1pbiwKICAgICAgIklOU0VSVCBJTlRPIHB1YmxpYy5taXhlcl9hdXRoel9iaW5kaW5ncyBWQUxVRVMoJ2h1bWFucycsMSwnc3ViamVjdC0xJywnaHVtYW4nLCdwZXJzb24tMScsdHJ1ZSwxKSIKICAgICkKCiAgICBmaXh0dXJlID0gc3RhcnRfc3VwZXJ2aXNlZCEoVExTRml4dHVyZSkKICAgIGF1dGggPSBHZW5TZXJ2ZXIuY2FsbChmaXh0dXJlLCA6YXV0aG9yaXR5KQogICAga2V5ID0gSk9TRS5KV0suZ2VuZXJhdGVfa2V5KHs6cnNhLCAyMDQ4fSkKICAgIHdyb25nID0gSk9TRS5KV0suZ2VuZXJhdGVfa2V5KHs6cnNhLCAyMDQ4fSkKCiAgICBwdWJsaWMgPQogICAgICBrZXkKICAgICAgfD4gSk9TRS5KV0sudG9fcHVibGljKCkKICAgICAgfD4gSk9TRS5KV0sudG9fbWFwKCkKICAgICAgfD4gZWxlbSgxKQogICAgICB8PiBNYXAubWVyZ2UoJXsia2lkIiA9PiAia2V5MSIsICJhbGciID0+ICJSUzI1NiIsICJ1c2UiID0+ICJzaWcifSkKCiAgICBqd2tzID0gSmFzb24uZW5jb2RlISgleyJrZXlzIiA9PiBbcHVibGljXX0pCiAgICBUTFNGaXh0dXJlLmNvbmZpZ3VyZShmaXh0dXJlLCB7OmJvZHksIGp3a3N9KQoKICAgIHByb2ZpbGUgPSAlewogICAgICBwcm9maWxlX2lkOiAiaHVtYW5zIiwKICAgICAgcHJvZmlsZV92ZXJzaW9uOiAxLAogICAgICBpc3N1ZXI6ICJodHRwczovL2lzc3Vlci5maXh0dXJlLmludmFsaWQiLAogICAgICBhdWRpZW5jZTogIm1peGVyLWFwaSIsCiAgICAgIGNsaWVudF9pZDogImNvbnNvbGUiLAogICAgICBpZGVudGl0eV9jbGFzczogOmh1bWFuLAogICAgICBlbmFibGVkOiB0cnVlCiAgICB9CgogICAgZW50cnkgPSAlewogICAgICBwcm9maWxlOiBwcm9maWxlLAogICAgICBqd2tzX2VuZHBvaW50OiAle2hvc3Q6ICJqd2tzLmZpeHR1cmUuaW52YWxpZCIsIHBvcnQ6IDQ0MywgcGF0aDogIi9rZXlzIn0sCiAgICAgIHRyYW5zcG9ydDogOmhvc3RlZF9odHRwcwogICAgfQoKICAgIHdvcmtlcnMgPSBzdGFydF9zdXBlcnZpc2VkISh7RHluYW1pY1N1cGVydmlzb3IsIHN0cmF0ZWd5OiA6b25lX2Zvcl9vbmUsIG5hbWU6IFI2ODYuV29ya2Vyc30pCgogICAgc3RhcnRfc3VwZXJ2aXNlZCEoJXsKICAgICAgaWQ6IEtleU93bmVyLAogICAgICBzdGFydDoKICAgICAgICB7S2V5T3duZXIsIDpzdGFydF9maXh0dXJlLAogICAgICAgICBbCiAgICAgICAgICAgWwogICAgICAgICAgICAgbmFtZTogS2V5T3duZXIsCiAgICAgICAgICAgICBtYW5pZmVzdDogW2VudHJ5XSwKICAgICAgICAgICAgIGdlbmVyYXRpb246IDEsCiAgICAgICAgICAgICBiaW5kaW5nOiAiaHVtYW5zIiwKICAgICAgICAgICAgIGNhX3Jvb3RzOiBbYXV0aC5jYV0sCiAgICAgICAgICAgICByZXNvbHZlcnM6IFt7ezEyNywgMCwgMCwgMX0sIDl9XSwKICAgICAgICAgICAgIHdvcmtlcl9zdXBlcnZpc29yOiBSNjg2LldvcmtlcnMsCiAgICAgICAgICAgICBmaXh0dXJlOiBNYXAudGFrZShhdXRoLCBbOmlwLCA6cG9ydF0pCiAgICAgICAgICAgXQogICAgICAgICBdfSwKICAgICAgc2h1dGRvd246IDppbmZpbml0eQogICAgfSkKCiAgICBvYmplY3QgPSAlewogICAgICAidmVyc2lvbiIgPT4gMSwKICAgICAgInB1YmxpY19vcmlnaW4iID0+ICJodHRwczovL2NvbnNvbGUuZml4dHVyZS5pbnZhbGlkIiwKICAgICAgInByb2ZpbGVfaWQiID0+ICJodW1hbnMiLAogICAgICAicHJvZmlsZV92ZXJzaW9uIiA9PiAxLAogICAgICAiaXNzdWVyIiA9PiBwcm9maWxlLmlzc3VlciwKICAgICAgImNsaWVudF9pZCIgPT4gImNvbnNvbGUiLAogICAgICAiYXBpX2F1ZGllbmNlIiA9PiAibWl4ZXItYXBpIiwKICAgICAgImF1dGhvcml6YXRpb25fZW5kcG9pbnQiID0+ICJodHRwczovL2lzc3Vlci5maXh0dXJlLmludmFsaWQvYXV0aG9yaXplIiwKICAgICAgInRva2VuX2VuZHBvaW50IiA9PiAiaHR0cHM6Ly9pc3N1ZXIuZml4dHVyZS5pbnZhbGlkL3Rva2VuIiwKICAgICAgImlkX3Rva2VuX2p3a3NfZW5kcG9pbnQiID0+ICJodHRwczovL2lzc3Vlci5maXh0dXJlLmludmFsaWQvb2lkYy9rZXlzIiwKICAgICAgInJlZGlyZWN0X3VyaSIgPT4gImh0dHBzOi8vY29uc29sZS5maXh0dXJlLmludmFsaWQvYXV0aC9jYWxsYmFjayIsCiAgICAgICJjbGllbnRfYXV0aF9tZXRob2QiID0+ICJjbGllbnRfc2VjcmV0X2Jhc2ljIiwKICAgICAgImNsaWVudF9jcmVkZW50aWFsX3JlZiIgPT4gInNlY3JldDovL2ZpeHR1cmUvY2xpZW50IiwKICAgICAgInNlc3Npb25fdmF1bHRfcmVmIiA9PiAidmF1bHQ6Ly9maXh0dXJlL2Jyb3dzZXIiLAogICAgICAic2NvcGUiID0+ICJvcGVuaWQgbWl4ZXIud29ya3NwYWNlLnJlYWQgbWl4ZXIuYnVpbGQucmVhZCIsCiAgICAgICJyZXNwb25zZV9tb2RlIiA9PiAicXVlcnkiLAogICAgICAicmVzcG9uc2VfaXNzX3JlcXVpcmVkIiA9PiB0cnVlCiAgICB9CgogICAgaWRlbnRpdHkgPSAlTWl4ZXJIb3N0ZWQuSWRlbnRpdHkuU3RhcnR1cENvbmZpZ3sKICAgICAgbW9kZTogOmNvbmZpZ3VyZWQsCiAgICAgIG93bmVyX29wdGlvbnM6IFttYW5pZmVzdDogW2VudHJ5XSwgYmluZGluZzogImh1bWFucyJdCiAgICB9CgogICAgezpvaywgY29uZmlnfSA9CiAgICAgIENvbmZpZy5sb2FkKAogICAgICAgICV7CiAgICAgICAgICAiTUlYRVJfQlJPV1NFUl9BVVRIX01PREUiID0+ICJjb25maWd1cmVkIiwKICAgICAgICAgICJNSVhFUl9CUk9XU0VSX0FVVEhfQ09ORklHIiA9PiBKYXNvbi5lbmNvZGUhKG9iamVjdCkKICAgICAgICB9LAogICAgICAgIDphcGksCiAgICAgICAgaWRlbnRpdHkKICAgICAgKQoKICAgIHs6b2ssIGRpZ2VzdH0gPSBDb25maWd1cmF0aW9uRGlnZXN0LmRpZ2VzdChjb25maWcpCgogICAgezpvaywgY3VzdG9keX0gPQogICAgICBDdXN0b2R5Lm5ldyhjb25maWcuc2Vzc2lvbl92YXVsdF9yZWYsICV7CiAgICAgICAgcmVmZXJlbmNlOiBjb25maWcuc2Vzc2lvbl92YXVsdF9yZWYsCiAgICAgICAga2V5X2lkOiAicjUxMiIsCiAgICAgICAga2V5X2J5dGVzOiA6Y3J5cHRvLnN0cm9uZ19yYW5kX2J5dGVzKDMyKQogICAgICB9KQoKICAgIG9yZGluYXJ5ID0KICAgICAgc2V0dGluZ3MgfD4gS2V5d29yZC5wdXQoOnVzZXJuYW1lLCAiYnJvd3Nlcl9vcmRpbmFyeSIpIHw+IEtleXdvcmQucHV0KDpwb29sX3NpemUsIDEpCgogICAgcHJldmlvdXNfcmVwbyA9IEFwcGxpY2F0aW9uLmZldGNoX2Vudig6bWl4ZXJfaG9zdGVkLCBNaXhlckhvc3RlZC5SZXBvKQoKICAgIG9uX2V4aXQoZm4gLT4KICAgICAgY2FzZSBwcmV2aW91c19yZXBvIGRvCiAgICAgICAgezpvaywgdmFsdWV9IC0+IEFwcGxpY2F0aW9uLnB1dF9lbnYoOm1peGVyX2hvc3RlZCwgTWl4ZXJIb3N0ZWQuUmVwbywgdmFsdWUpCiAgICAgICAgOmVycm9yIC0+IEFwcGxpY2F0aW9uLmRlbGV0ZV9lbnYoOm1peGVyX2hvc3RlZCwgTWl4ZXJIb3N0ZWQuUmVwbykKICAgICAgZW5kCiAgICBlbmQpCgogICAgQXBwbGljYXRpb24ucHV0X2Vudig6bWl4ZXJfaG9zdGVkLCBNaXhlckhvc3RlZC5SZXBvLCBvcmRpbmFyeSkKICAgIHN0YXJ0X3N1cGVydmlzZWQhKHtNaXhlckhvc3RlZC5SZXBvLCBvcmRpbmFyeX0pCgogICAgY29tbWl0X3Byb3h5ID0gc3RhcnRfc3VwZXJ2aXNlZCEoe1I5MzIuUGhhc2VDb21taXRQcm94eSwgRi5wb3J0KCl9KQoKICAgIGxpZmUgPSBbCiAgICAgIGhvc3RuYW1lOiAiMTI3LjAuMC4xIiwKICAgICAgcG9ydDogR2VuU2VydmVyLmNhbGwoY29tbWl0X3Byb3h5LCA6cG9ydCksCiAgICAgIGRhdGFiYXNlOiAiYnJvd3Nlcl9sb2dpbl9zdG9yYWdlIiwKICAgICAgdXNlcm5hbWU6ICJicm93c2VyX2xpZmVjeWNsZSIsCiAgICAgIHBhc3N3b3JkOiAic3ludGhldGljIiwKICAgICAgcG9vbF9zaXplOiAyLAogICAgICBwb29sX2NvdW50OiAxLAogICAgICB0aW1lb3V0OiA1MDAwLAogICAgICBjb25uZWN0X3RpbWVvdXQ6IDUwMDAsCiAgICAgIHF1ZXVlOiBmYWxzZSwKICAgICAgc2hvd19zZW5zaXRpdmVfZGF0YV9vbl9jb25uZWN0aW9uX2Vycm9yOiBmYWxzZSwKICAgICAgc3NsOiBmYWxzZQogICAgXQoKICAgIHN0YXJ0X3N1cGVydmlzZWQhKHtMaWZlY3ljbGVSZXBvLCBsaWZlfSkKCiAgICBydW50aW1lID0gJVJ1bnRpbWVDb25maWd7CiAgICAgIGFkbWlzc2lvbl9wcm9maWxlOiA6YnVpbGRfY2F0YWxvZ192MywKICAgICAgbW9kZTogOmNvbmZpZ3VyZWQsCiAgICAgIGJyb3dzZXJfY29uZmlnOiBjb25maWcsCiAgICAgIGNvbmZpZ3VyYXRpb25fZGlnZXN0OiBkaWdlc3QsCiAgICAgIGxpZmVjeWNsZV9yZXBvOiBsaWZlLAogICAgICBleHBlY3RlZF9yb2xlczogJXsKICAgICAgICBsaWZlY3ljbGVfbG9naW46ICJicm93c2VyX2xpZmVjeWNsZSIsCiAgICAgICAgd3JpdGVyOiAiYnJvd3Nlcl93cml0ZXIiLAogICAgICAgIHJlbGF0aW9uX293bmVyOiAiYnJvd3Nlcl9zY2hlbWFfb3duZXIiLAogICAgICAgIG9yZGluYXJ5X3J1bnRpbWVfbG9naW46ICJicm93c2VyX29yZGluYXJ5IgogICAgICB9LAogICAgICBjdXN0b2R5OiBjdXN0b2R5CiAgICB9CgogICAgYXNzZXJ0IHs6b2ssIDpmdW5jdGlvbl9zdXJmYWNlX3ZlcmlmaWVkfSA9CiAgICAgICAgICAgICBMaWZlY3ljbGVSZXBvLnRyYW5zYWN0aW9uKAogICAgICAgICAgICAgICBmbiAtPgogICAgICAgICAgICAgICAgIEYucSEoTGlmZWN5Y2xlUmVwbywgIlNFVCBUUkFOU0FDVElPTiBJU09MQVRJT04gTEVWRUwgUkVBRCBDT01NSVRURUQiKQoKICAgICAgICAgICAgICAgICBmb3Igc2V0dGluZyA8LSBbCiAgICAgICAgICAgICAgICAgICAgICAgInNlYXJjaF9wYXRoPXBnX2NhdGFsb2ciLAogICAgICAgICAgICAgICAgICAgICAgICJqaXQ9b2ZmIiwKICAgICAgICAgICAgICAgICAgICAgICAic3RhdGVtZW50X3RpbWVvdXQ9JzVzJyIsCiAgICAgICAgICAgICAgICAgICAgICAgImxvY2tfdGltZW91dD0nNTAwbXMnIiwKICAgICAgICAgICAgICAgICAgICAgICAiaWRsZV9pbl90cmFuc2FjdGlvbl9zZXNzaW9uX3RpbWVvdXQ9JzVzJyIsCiAgICAgICAgICAgICAgICAgICAgICAgImJ5dGVhX291dHB1dD0naGV4JyIKICAgICAgICAgICAgICAgICAgICAgXSwKICAgICAgICAgICAgICAgICAgICAgZG86IEYucSEoTGlmZWN5Y2xlUmVwbywgIlNFVCBMT0NBTCAiIDw+IHNldHRpbmcpCgogICAgICAgICAgICAgICAgIE1peGVySG9zdGVkLkJyb3dzZXJBdXRoLkNhdGFsb2cuY2hlY2tfZnVuY3Rpb25fc3VyZmFjZSEoCiAgICAgICAgICAgICAgICAgICBMaWZlY3ljbGVSZXBvLAogICAgICAgICAgICAgICAgICAgcnVudGltZS5leHBlY3RlZF9yb2xlcywKICAgICAgICAgICAgICAgICAgIFN5c3RlbS5tb25vdG9uaWNfdGltZSg6bWlsbGlzZWNvbmQpICsgNTAwMCwKICAgICAgICAgICAgICAgICAgIDIKICAgICAgICAgICAgICAgICApCiAgICAgICAgICAgICAgIGVuZCwKICAgICAgICAgICAgICAgbG9nOiBmYWxzZQogICAgICAgICAgICAgKQoKICAgIElPLnB1dHMoIk9SSUdJTkFMX0NBVEFMT0cgZXhhY3RfdjJfYmVmb3JlX2FkZGl0aW9uPXRydWUiKQogICAgZm9yIHNxbCA8LSBNaXhlckhvc3RlZC5Ccm93c2VyQXV0aC5BY3RpdmVSZWFkU2NoZW1hLnN0YXRlbWVudHMoKSwgZG86IEYucSEoTWlncmF0aW9uLCBzcWwpCiAgICBjb25uID0gRi5jb25uZWN0aW9uISgiYnJvd3Nlcl9hZG1pbiIpCgogICAgZm9yIHNxbCA8LSBNaXhlckhvc3RlZC5Ccm93c2VyQXV0aC5BY3RpdmVSZWFkU2NoZW1hLnByb3Zpc2lvbmluZ19zdGF0ZW1lbnRzKCksCiAgICAgICAgZG86IFBvc3RncmV4LnF1ZXJ5IShjb25uLCBzcWwsIFtdKQoKICAgIEdlblNlcnZlci5zdG9wKGNvbm4pCgogICAgdW5sZXNzIENvZGUuZW5zdXJlX2xvYWRlZD8oTWl4ZXJIb3N0ZWQuUmVwby5NaWdyYXRpb25zLkFkZEJ1aWxkSm91cm5hbHMpLAogICAgICBkbzogQ29kZS5yZXF1aXJlX2ZpbGUoInByaXYvcmVwby9taWdyYXRpb25zLzIwMjYxMDI1MDAwMDAwX2FkZF9idWlsZF9qb3VybmFscy5leHMiKQoKICAgIDpvayA9CiAgICAgIEVjdG8uTWlncmF0b3IudXAoCiAgICAgICAgTWlncmF0aW9uLAogICAgICAgIDIwXzI2MV8wMjVfMDAwXzAwMCwKICAgICAgICBNaXhlckhvc3RlZC5SZXBvLk1pZ3JhdGlvbnMuQWRkQnVpbGRKb3VybmFscywKICAgICAgICBsb2c6IGZhbHNlCiAgICAgICkKCiAgICA6b2sgPSBFY3RvLk1pZ3JhdG9yLnVwKE1pZ3JhdGlvbiwgMSwgUjEwMjYuT2Jhbk1pZ3JhdGlvbiwgbG9nOiBmYWxzZSkKICAgIEYucSEoTWlncmF0aW9uLCBNaXhlckhvc3RlZC5DdXN0b21lckJ1aWxkcy5TY2hlbWEuZGRsKCkpCgogICAgRi5xISgKICAgICAgTWlncmF0aW9uLAogICAgICAiUkVWT0tFIEFMTCBPTiBGVU5DVElPTiBwdWJsaWMubWl4ZXJfY3VzdG9tZXJfYnVpbGRfcmVhZF92MSh0ZXh0LHRleHQsdGV4dCx0ZXh0LHRleHQpIEZST00gUFVCTElDIgogICAgKQoKICAgIEYucSEoCiAgICAgIE1pZ3JhdGlvbiwKICAgICAgIkdSQU5UIEVYRUNVVEUgT04gRlVOQ1RJT04gcHVibGljLm1peGVyX2N1c3RvbWVyX2J1aWxkX3JlYWRfdjEodGV4dCx0ZXh0LHRleHQsdGV4dCx0ZXh0KSBUTyBicm93c2VyX29yZGluYXJ5IgogICAgKQoKICAgIHN0YXJ0X3N1cGVydmlzZWQhKHtPYmFuLCByZXBvOiBBZG1pbiwgcXVldWVzOiBmYWxzZSwgcGx1Z2luczogZmFsc2UsIHRlc3Rpbmc6IDptYW51YWx9KQogICAgbm93ID0gU3lzdGVtLnN5c3RlbV90aW1lKDpzZWNvbmQpCiAgICB7Om9rLCBzbmFwc2hvdH0gPSBUcnVzdFNuYXBzaG90Lm5ldyhwcm9maWxlLCBqd2tzLCBub3csIG5vdyArIDMwMCkKICAgIHByb3ZpZGVyID0gc3RhcnRfc3VwZXJ2aXNlZCEoe1I2ODYuUHJvdmlkZXIsICV7a2V5OiBrZXksIHdyb25nX2tleTogd3JvbmcsIGNvbmZpZzogY29uZmlnfX0pCgogICAgc3RhcnRfc3VwZXJ2aXNlZCEoJXsKICAgICAgaWQ6IFByb3ZpZGVyT3duZXIsCiAgICAgIHN0YXJ0OiB7UHJvdmlkZXJPd25lciwgOnN0YXJ0X2ZpeHR1cmUsIFtjb25maWcsIHNuYXBzaG90LCBwcm92aWRlcl19CiAgICB9KQoKICAgIHs6b2ssIDpva30gPQogICAgICBNaWdyYXRpb24udHJhbnNhY3Rpb24oZm4gLT4KICAgICAgICBFbnVtLmVhY2goTWl4ZXJIb3N0ZWQuQ3VzdG9tZXJBcnRpZmFjdHMuU2NoZW1hLnN0YXRlbWVudHMoKSwgJkYucSEoTWlncmF0aW9uLCAmMSkpCiAgICAgIGVuZCkKCiAgICBGLnEhKAogICAgICBBZG1pbiwKICAgICAgIklOU0VSVCBJTlRPIHB1YmxpYy5taXhlcl9hdXRoel9vcmdhbml6YXRpb25zKGlkLGFjdGl2ZSxkaXNwbGF5X25hbWUpIFZBTFVFUygnb3JnLWEnLHRydWUsJ1Zpc2libGUnKSwoJ29yZy1iJyx0cnVlLCdIaWRkZW4nKSIKICAgICkKCiAgICBGLnEhKAogICAgICBBZG1pbiwKICAgICAgIklOU0VSVCBJTlRPIHB1YmxpYy5taXhlcl9hdXRoel9wcm9qZWN0cyhvcmdhbml6YXRpb25faWQsaWQsYWN0aXZlLGRpc3BsYXlfbmFtZSkgVkFMVUVTKCdvcmctYScsJ3Byb2plY3QtYScsdHJ1ZSwnUHJvamVjdCBBJyksKCdvcmctYicsJ3Byb2plY3QtYicsdHJ1ZSwnUHJvamVjdCBCJykiCiAgICApCgogICAgRi5xISgKICAgICAgQWRtaW4sCiAgICAgICJJTlNFUlQgSU5UTyBwdWJsaWMubWl4ZXJfYXV0aHpfYXBwbGljYXRpb25zIFZBTFVFUygnb3JnLWEnLCdwcm9qZWN0LWEnLCdmaWVsZGxvZycsdHJ1ZSkiCiAgICApCgogICAgRi5xISgKICAgICAgQWRtaW4sCiAgICAgICJJTlNFUlQgSU5UTyBwdWJsaWMubWl4ZXJfYXV0aHpfbWVtYmVyc2hpcHMgVkFMVUVTKCdtZW1iZXItYScsJ3BlcnNvbi0xJywnb3JnLWEnLE5VTEwsJ2FsbF9wcm9qZWN0cycsJ3ZpZXdlcicsdHJ1ZSwwLE5VTEwsMSkiCiAgICApCgogICAgRi5xISgKICAgICAgQWRtaW4sCiAgICAgICJJTlNFUlQgSU5UTyBwdWJsaWMubWl4ZXJfYXV0aHpfb3JnYW5pemF0aW9uX2hlYWRzIFNFTEVDVCBpZCwxIEZST00gcHVibGljLm1peGVyX2F1dGh6X29yZ2FuaXphdGlvbnMiCiAgICApCgogICAgRi5xISgKICAgICAgQWRtaW4sCiAgICAgICJJTlNFUlQgSU5UTyBwdWJsaWMubWl4ZXJfYXV0aHpfcHJvamVjdF9oZWFkcyBTRUxFQ1Qgb3JnYW5pemF0aW9uX2lkLGlkLDEgRlJPTSBwdWJsaWMubWl4ZXJfYXV0aHpfcHJvamVjdHMiCiAgICApCgogICAgZm9yIG4gPC0gMC4uNTEgZG8KICAgICAgaWQgPSAicjYwNC0iIDw+IFN0cmluZy5wYWRfbGVhZGluZyhJbnRlZ2VyLnRvX3N0cmluZyhuKSwgMiwgIjAiKQoKICAgICAgRi5xISgKICAgICAgICBBZG1pbiwKICAgICAgICAiSU5TRVJUIElOVE8gcHVibGljLm1peGVyX2F1dGh6X29yZ2FuaXphdGlvbnMoaWQsYWN0aXZlLGRpc3BsYXlfbmFtZSkgVkFMVUVTKCQxLHRydWUsJDEpIiwKICAgICAgICBbaWRdCiAgICAgICkKCiAgICAgIEYucSEoQWRtaW4sICJJTlNFUlQgSU5UTyBwdWJsaWMubWl4ZXJfYXV0aHpfb3JnYW5pemF0aW9uX2hlYWRzIFZBTFVFUygkMSwxKSIsIFtpZF0pCgogICAgICBGLnEhKAogICAgICAgIEFkbWluLAogICAgICAgICJJTlNFUlQgSU5UTyBwdWJsaWMubWl4ZXJfYXV0aHpfbWVtYmVyc2hpcHMgVkFMVUVTKCQxLCdwZXJzb24tMScsJDIsTlVMTCwnYWxsX3Byb2plY3RzJywndmlld2VyJyx0cnVlLDAsTlVMTCwxKSIsCiAgICAgICAgWyJtZW1iZXItIiA8PiBpZCwgaWRdCiAgICAgICkKCiAgICAgIEYucSEoCiAgICAgICAgQWRtaW4sCiAgICAgICAgIklOU0VSVCBJTlRPIHB1YmxpYy5taXhlcl9hdXRoel9wcm9qZWN0cyhvcmdhbml6YXRpb25faWQsaWQsYWN0aXZlLGRpc3BsYXlfbmFtZSkgVkFMVUVTKCdvcmctYScsJDEsdHJ1ZSwkMSkiLAogICAgICAgIFtpZF0KICAgICAgKQoKICAgICAgRi5xIShBZG1pbiwgIklOU0VSVCBJTlRPIHB1YmxpYy5taXhlcl9hdXRoel9wcm9qZWN0X2hlYWRzIFZBTFVFUygnb3JnLWEnLCQxLDEpIiwgW2lkXSkKICAgIGVuZAoKICAgICV7CiAgICAgIHJ1bnRpbWU6IHJ1bnRpbWUsCiAgICAgIGNvbmZpZzogY29uZmlnLAogICAgICBwcm92aWRlcjogcHJvdmlkZXIsCiAgICAgIHdvcmtlcnM6IHdvcmtlcnMsCiAgICAgIGZpeHR1cmU6IGZpeHR1cmUsCiAgICAgIGNvbW1pdF9wcm94eTogY29tbWl0X3Byb3h5CiAgICB9CiAgZW5kCgogIHNldHVwIGMgZG8KICAgIGFzc2VydCBMaWZlY3ljbGVSZXBvLmJvdW5kPyhjLnJ1bnRpbWUubGlmZWN5Y2xlX3JlcG8pCiAgICBhc3NlcnQgTWl4ZXJIb3N0ZWQuUmVwby5jb25maWcoKVs6dXNlcm5hbWVdID09PSAiYnJvd3Nlcl9vcmRpbmFyeSIKICAgIHN0YXJ0X3N1cGVydmlzZWQhKHtSdW50aW1lT3duZXIsIGMucnVudGltZX0pCiAgICBhc3NlcnQgUnVudGltZU93bmVyLnN0YXR1cygpLnBoYXNlID09PSA6c3RvcmFnZV9yZWFkeQogICAgR2VuU2VydmVyLmNhbGwoYy5wcm92aWRlciwgezptb2RlLCA6b2t9KQoKICAgIHNlcnZlciA9CiAgICAgIHN0YXJ0X3N1cGVydmlzZWQhKCV7CiAgICAgICAgaWQ6IDpyNjA0X2h0dHAsCiAgICAgICAgc3RhcnQ6IHtNaXhlckhvc3RlZFdlYi5Ccm93c2VyTG9naW5IVFRQLlNlcnZlciwgOnN0YXJ0X2xpbmssIFtbXV19CiAgICAgIH0pCgogICAgezpvaywge18sIHBvcnR9fSA9IFRob3VzYW5kSXNsYW5kLmxpc3RlbmVyX2luZm8oc2VydmVyKQoKICAgIGF1dGhvcml6YXRpb24gPQogICAgICBzdGFydF9zdXBlcnZpc2VkISglewogICAgICAgIGlkOiA6YXV0aG9yaXphdGlvbl9odHRwLAogICAgICAgIHN0YXJ0OgogICAgICAgICAge0JhbmRpdCwgOnN0YXJ0X2xpbmssCiAgICAgICAgICAgWwogICAgICAgICAgICAgWwogICAgICAgICAgICAgICBwbHVnOiB7UjY4Ni5BdXRob3JpemF0aW9uSFRUUCwgJXtwcm92aWRlcjogYy5wcm92aWRlciwgY29uZmlnOiBjLmNvbmZpZ319LAogICAgICAgICAgICAgICBpcDogezEyNywgMCwgMCwgMX0sCiAgICAgICAgICAgICAgIHBvcnQ6IDAsCiAgICAgICAgICAgICAgIHN0YXJ0dXBfbG9nOiBmYWxzZQogICAgICAgICAgICAgXQogICAgICAgICAgIF19CiAgICAgIH0pCgogICAgezpvaywge18sIHByb3ZpZGVyX3BvcnR9fSA9IFRob3VzYW5kSXNsYW5kLmxpc3RlbmVyX2luZm8oYXV0aG9yaXphdGlvbikKICAgICV7aHR0cF9wb3J0OiBwb3J0LCBwcm92aWRlcl9wb3J0OiBwcm92aWRlcl9wb3J0fQogIGVuZAoKICBkZWZwIHJhdyhjb29raWUsIGMpIGRvCiAgICBjb25uID0gRi5jb25uZWN0aW9uISgpCgogICAgezpvaywgc30gPQogICAgICBGLmNhbGwoY29ubiwgOmxvYWQsIFs6Y3J5cHRvLmhhc2goOnNoYTI1NiwgY29va2llKSwgYy5ydW50aW1lLmNvbmZpZ3VyYXRpb25fZGlnZXN0XSkKCiAgICBHZW5TZXJ2ZXIuc3RvcChjb25uKQogICAgcwogIGVuZAoKICBkZWZwIGhlYWRlcnMoY29va2llKSwgZG86IFt7ImNvb2tpZSIsICJfX0hvc3QtbWl4ZXItc2Vzc2lvbj0iIDw+IGNvb2tpZX1dCgogIGRlZnAgbGVhc2VzX2NsZWFuIGRvCiAgICBhc3NlcnQgbWFwX3NpemUoOnN5cy5nZXRfc3RhdGUoUnVudGltZU93bmVyKS5vcGVyYXRpb25zKSA9PSAwCiAgZW5kCgogIGRlZnAgaHR0cChjLCBwYXRoLCBoZWFkZXJzLCBtZXRob2QgXFwgIkdFVCIsIGJvZHkgXFwgIiIpIGRvCiAgICB7Om9rLCBzfSA9IDpnZW5fdGNwLmNvbm5lY3QoezEyNywgMCwgMCwgMX0sIGMuaHR0cF9wb3J0LCBbOmJpbmFyeSwgYWN0aXZlOiBmYWxzZV0sIDIwMDApCgogICAgcmVxdWVzdCA9IFsKICAgICAgbWV0aG9kLAogICAgICAiICIsCiAgICAgIHBhdGgsCiAgICAgICIgSFRUUC8xLjFcclxuSG9zdDogMTI3LjAuMC4xXHJcbkNvbm5lY3Rpb246IGNsb3NlXHJcbiIsCiAgICAgIEVudW0ubWFwKGhlYWRlcnMsIGZuIHtrLCB2fSAtPiBbaywgIjogIiwgdiwgIlxyXG4iXSBlbmQpLAogICAgICAiXHJcbiIsCiAgICAgIGJvZHkKICAgIF0KCiAgICA6b2sgPSA6Z2VuX3RjcC5zZW5kKHMsIHJlcXVlc3QpCgogICAgY29sbGVjdCA9IGZuIGFnYWluLCBhY2MgLT4KICAgICAgY2FzZSA6Z2VuX3RjcC5yZWN2KHMsIDAsIDcwMDApIGRvCiAgICAgICAgezpvaywgYn0gLT4KICAgICAgICAgIGlmIGNbOndpcmVfb2JzZXJ2ZXJdLCBkbzogc2VuZChjLndpcmVfb2JzZXJ2ZXIsIHs6aHR0cF9ieXRlcywgYnl0ZV9zaXplKGIpfSkKICAgICAgICAgIGFnYWluLihhZ2FpbiwgYWNjIDw+IGIpCgogICAgICAgIHs6ZXJyb3IsIDpjbG9zZWR9IC0+CiAgICAgICAgICBhY2MKCiAgICAgICAgXyAtPgogICAgICAgICAgcmFpc2UgImNsb3NlZCBIVFRQIHRyYW5zcG9ydCBmYWlsdXJlIgogICAgICBlbmQKICAgIGVuZAoKICAgIHJhdyA9IGNvbGxlY3QuKGNvbGxlY3QsICIiKQogICAgOmdlbl90Y3AuY2xvc2UocykKICAgIFtoZWFkLCBib2R5XSA9IFN0cmluZy5zcGxpdChyYXcsICJcclxuXHJcbiIsIHBhcnRzOiAyKQogICAgW2xpbmUgfCBoc10gPSBTdHJpbmcuc3BsaXQoaGVhZCwgIlxyXG4iKQogICAgW18sIGNvZGUgfCBfXSA9IFN0cmluZy5zcGxpdChsaW5lLCAiICIpCiAgICAle3N0YXR1czogU3RyaW5nLnRvX2ludGVnZXIoY29kZSksIGJvZHk6IGJvZHksIGhlYWRlcnM6IGhzfQogIGVuZAoKICBkZWZwIGV4cGlyeShjLCBjb29raWUpIGRvCiAgICBhc3NlcnQgezpvaywgc30gPSBTdG9yZWRTbmFwc2hvdC5kZWNvZGUocmF3KGNvb2tpZSwgYykpCgogICAgYXNzZXJ0IHs6b2ssICVWYXVsdC5BY3RpdmV7YWNjZXNzX3Rva2VuOiB0b2tlbn19ID0KICAgICAgICAgICAgIFZhdWx0Lm9wZW4oCiAgICAgICAgICAgICAgIGMucnVudGltZS5jdXN0b2R5LmtleSwKICAgICAgICAgICAgICAgcy5zZXNzaW9uX2VudmVsb3BlLmNvbnRleHQsCiAgICAgICAgICAgICAgIHMuc2Vzc2lvbl9lbnZlbG9wZS5zZWFsZWQKICAgICAgICAgICAgICkKCiAgICBhc3NlcnQgezpvaywgaX0gPQogICAgICAgICAgICAgTWl4ZXJIb3N0ZWQuSWRlbnRpdHkuQ29uZmlndXJlZFZlcmlmaWVyLmF1dGhlbnRpY2F0ZSgKICAgICAgICAgICAgICAgS2V5T3duZXIsCiAgICAgICAgICAgICAgICJodW1hbnMiLAogICAgICAgICAgICAgICB0b2tlbiwKICAgICAgICAgICAgICAgU3lzdGVtLnN5c3RlbV90aW1lKDpzZWNvbmQpCiAgICAgICAgICAgICApCgogICAge3MsIGksIG1pbihpLmV4cGlyZXNfYXQsIG1pbihzLmJyb3dzZXJbImlkbGVfZXhwaXJlc19hdCJdLCBzLmJyb3dzZXJbImFic29sdXRlX2V4cGlyZXNfYXQiXSkpfQogIGVuZAoKICBkZWZwIHJlc3BvbnNlX2hlYWRlcihyLCBuYW1lKSBkbwogICAgcHJlZml4ID0gbmFtZSA8PiAiOiAiCiAgICBmb3IgaCA8LSByLmhlYWRlcnMsIFN0cmluZy5zdGFydHNfd2l0aD8oaCwgcHJlZml4KSwgZG86IFN0cmluZy5yZXBsYWNlX3ByZWZpeChoLCBwcmVmaXgsICIiKQogIGVuZAoKICBkZWZwIHJlc3BvbnNlX2Nvb2tpZShyKSBkbwogICAgW2Nvb2tpZV0gPSByZXNwb25zZV9oZWFkZXIociwgInNldC1jb29raWUiKQogICAgYXNzZXJ0IFN0cmluZy5jb250YWlucz8oY29va2llLCAiOyBQYXRoPS87IFNlY3VyZTsgSHR0cE9ubHk7IFNhbWVTaXRlPUxheDsgTWF4LUFnZT0iKQogICAgW3BhaXIgfCBfXSA9IFN0cmluZy5zcGxpdChjb29raWUsICI7IikKICAgICJfX0hvc3QtbWl4ZXItc2Vzc2lvbj0iIDw+IHRva2VuID0gcGFpcgogICAgYXNzZXJ0IFByb3RvY29sLnRva2VuPyh0b2tlbikKICAgIHRva2VuCiAgZW5kCgogIGRlZnAgYm9vdHN0cmFwX2h0dHAoYykgZG8KICAgIHIgPSBodHRwKGMsICIvYXV0aC9zZXNzaW9uIiwgW10pCiAgICBhc3NlcnQgci5zdGF0dXMgPT0gMjAwCiAgICBwID0gcmVzcG9uc2VfY29va2llKHIpCiAgICBjc3JmID0gSmFzb24uZGVjb2RlIShyLmJvZHkpWyJjc3JmX3Rva2VuIl0KICAgIGFzc2VydCB7Om9rLCBsb2FkZWR9ID0gUnVudGltZU93bmVyLmxvYWQocCkKICAgIGFzc2VydCBsb2FkZWQuY29va2llID09IHAgYW5kIGxvYWRlZC5jc3JmID09IGNzcmYKICAgICV7Y29va2llOiBwLCBjc3JmOiBjc3JmfQogIGVuZAoKICBkZWZwIGJlZ2luX2h0dHAoYywgcCkgZG8KICAgIGhzID0gaGVhZGVycyhwLmNvb2tpZSkgKysgW3sib3JpZ2luIiwgYy5jb25maWcucHVibGljX29yaWdpbn0sIHsieC1taXhlci1jc3JmIiwgcC5jc3JmfV0KICAgIHIgPSBodHRwKGMsICIvYXV0aC9sb2dpbiIsIGhzLCAiUE9TVCIpCiAgICBhc3NlcnQgci5zdGF0dXMgPT0gMzAzCiAgICBhc3NlcnQgcmVzcG9uc2VfaGVhZGVyKHIsICJzZXQtY29va2llIikgPT0gW10KICAgIFtsb2NhdGlvbl0gPSByZXNwb25zZV9oZWFkZXIociwgImxvY2F0aW9uIikKICAgIHVyaSA9IFVSSS5wYXJzZShsb2NhdGlvbikKICAgIGFzc2VydCB1cmkuc2NoZW1lIDw+ICI6Ly8iIDw+IHVyaS5ob3N0IDw+IHVyaS5wYXRoID09IGMuY29uZmlnLmF1dGhvcml6YXRpb25fZW5kcG9pbnQKICAgIHYgPSBVUkkuZGVjb2RlX3F1ZXJ5KHVyaS5xdWVyeSkKICAgIGFzc2VydCB2WyJyZXNwb25zZV90eXBlIl0gPT0gImNvZGUiIGFuZCB2WyJyZXNwb25zZV9tb2RlIl0gPT0gInF1ZXJ5IgogICAgYXNzZXJ0IHZbInJlZGlyZWN0X3VyaSJdID09IGMuY29uZmlnLnJlZGlyZWN0X3VyaQogICAgYXNzZXJ0IHZbImNsaWVudF9pZCJdID09IGMuY29uZmlnLmNsaWVudF9pZCBhbmQgdlsiY29kZV9jaGFsbGVuZ2VfbWV0aG9kIl0gPT0gIlMyNTYiCiAgICBhc3NlcnQgUHJvdG9jb2wudG9rZW4/KHZbInN0YXRlIl0pIGFuZCBQcm90b2NvbC50b2tlbj8odlsibm9uY2UiXSkKICAgICMgVGhlIHN5bnRoZXRpYyBwcm92aWRlciByZWNlaXZlcyBvbmx5IHRoZSBIVFRQLXByb2R1Y2VkIGF1dGhvcml6YXRpb24gcXVlcnkuCiAgICBwcm92aWRlcl9yZXNwb25zZSA9IGh0dHAoJXtodHRwX3BvcnQ6IGMucHJvdmlkZXJfcG9ydH0sICIvYXV0aG9yaXplPyIgPD4gdXJpLnF1ZXJ5LCBbXSkKICAgIGFzc2VydCBwcm92aWRlcl9yZXNwb25zZS5zdGF0dXMgPT0gMzAyCiAgICBbY2FsbGJhY2tdID0gcmVzcG9uc2VfaGVhZGVyKHByb3ZpZGVyX3Jlc3BvbnNlLCAibG9jYXRpb24iKQogICAgYXNzZXJ0IFN0cmluZy5zdGFydHNfd2l0aD8oY2FsbGJhY2ssIGMuY29uZmlnLnJlZGlyZWN0X3VyaSA8PiAiPyIpCiAgICBxdWVyeSA9IFVSSS5wYXJzZShjYWxsYmFjaykucXVlcnkKICAgICV7aGVhZGVyczogaGVhZGVycyhwLmNvb2tpZSksIHF1ZXJ5OiBxdWVyeSwgY29va2llOiBwLmNvb2tpZX0KICBlbmQKCiAgZGVmcCBjb21waWxlZF9idWlsZF9yZWFkKGMsIHNlbGVjdGVkLCBjb29raWUsIHBoYXNlLCB3aXJlKSBkbwogICAgW3ZhbHVlc10gPQogICAgICBGLnEhKAogICAgICAgIEFkbWluLAogICAgICAgICJTRUxFQ1Qgb3JnYW5pemF0aW9uX2lkLHByb2plY3RfaWQsYXBwbGljYXRpb25faWQsYnVpbGRfaWQscGxhdGZvcm0scmVxdWVzdF9rZXkscmV2aXNpb24sam91cm5hbCBGUk9NIHB1YmxpYy5taXhlcl9idWlsZHMiCiAgICAgICkucm93cwoKICAgIHJlY29yZCA9CiAgICAgIE1hcC5uZXcoCiAgICAgICAgRW51bS56aXAoCiAgICAgICAgICB+dyhvcmdhbml6YXRpb25faWQgcHJvamVjdF9pZCBhcHBsaWNhdGlvbl9pZCBidWlsZF9pZCBwbGF0Zm9ybSByZXF1ZXN0X2tleSByZXZpc2lvbiBqb3VybmFsKWEsCiAgICAgICAgICB2YWx1ZXMKICAgICAgICApCiAgICAgICkKCiAgICBhc3NlcnQgezpvaywgcHJvamVjdGVkfSA9IE1peGVySG9zdGVkLkN1c3RvbWVyQnVpbGRzLlNuYXBzaG90LnByb2plY3QocmVjb3JkLCBzZWxlY3RlZCkKICAgIGV4cGVjdGVkID0gcHJvamVjdGVkIHw+IEphc29uLmVuY29kZSEoKSB8PiBKYXNvbi5kZWNvZGUhKCkKICAgIGFzc2VydCBleHBlY3RlZCA9PT0gd2lyZQogICAgYXNzZXJ0IHs6b2ssIHJlc3RvcmVkfSA9IE1peGVySG9zdGVkLkJ1aWxkcy5Kb3VybmFsLnJlc3RvcmUocmVjb3JkLmpvdXJuYWwpCiAgICBhc3NlcnQgezpvaywgc3RhdHVzfSA9IE1peGVySG9zdGVkLkJ1aWxkcy5MaWZlY3ljbGUuY3VzdG9tZXJfc3RhdHVzKHJlc3RvcmVkKQogICAgYXNzZXJ0IHdpcmVbImF0dGVtcHQiXSA9PT0gc3RhdHVzLmF0dGVtcHQKICAgIGFzc2VydCB3aXJlWyJtYXhBdHRlbXB0cyJdID09PSBzdGF0dXMubWF4X2F0dGVtcHRzCiAgICBhc3NlcnQgd2lyZVsic3RhdGUiXSA9PT0gQXRvbS50b19zdHJpbmcoc3RhdHVzLnN0YXRlKQogICAgYXNzZXJ0IHdpcmVbInJldmlzaW9uIl0gPT09IGxlbmd0aChyZWNvcmQuam91cm5hbFsiZXZlbnRzIl0pCgogICAgZml4dHVyZSA9CiAgICAgIFBhdGguam9pbigKICAgICAgICBTeXN0ZW0udG1wX2RpciEoKSwKICAgICAgICAiYnJvd3Nlci1idWlsZC1jbGllbnQtIiA8PgogICAgICAgICAgQmFzZS51cmxfZW5jb2RlNjQoOmNyeXB0by5zdHJvbmdfcmFuZF9ieXRlcygxMiksIHBhZGRpbmc6IGZhbHNlKSA8PiAiLmpzb24iCiAgICAgICkKCiAgICBGaWxlLndyaXRlISgKICAgICAgZml4dHVyZSwKICAgICAgSmFzb24uZW5jb2RlISgle3BvcnQ6IGMuaHR0cF9wb3J0LCBjb29raWU6IGNvb2tpZSwgZHRvOiBleHBlY3RlZCwgcGhhc2U6IHBoYXNlfSkKICAgICkKCiAgICB0cnkgZG8KICAgICAge291dCwgY29kZX0gPQogICAgICAgIFN5c3RlbS5jbWQoIm5vZGUiLCBbU3lzdGVtLmZldGNoX2VudiEoIk1JWEVSX0JST1dTRVJfQlVJTERfTk9ERV9EUklWRVIiKSwgZml4dHVyZV0sCiAgICAgICAgICBzdGRlcnJfdG9fc3Rkb3V0OiB0cnVlCiAgICAgICAgKQoKICAgICAgYXNzZXJ0IGNvZGUgPT0gMCwgb3V0CiAgICAgIGFzc2VydCBvdXQgPX4gfnMoInN0YXR1cyI6IlBBU1MiKSwgb3V0CiAgICBhZnRlcgogICAgICBGaWxlLnJtIShmaXh0dXJlKQogICAgZW5kCiAgZW5kCgogIGRlZnAgY29tcGlsZWRfY2F0YWxvZ19qb2luKGMsIGNvb2tpZSwgcGFnZSwgcGhhc2UsIGV4cGVjdGVkKSBkbwogICAgcm9vdCA9IFN5c3RlbS5mZXRjaF9lbnYhKCJNSVhFUl9CUk9XU0VSX0NBVEFMT0dfRklYVFVSRV9ST09UIikKCiAgICBmaXh0dXJlID0KICAgICAgUGF0aC5qb2luKAogICAgICAgIFN5c3RlbS50bXBfZGlyISgpLAogICAgICAgICJtaXhlci1jYXRhbG9nLSIgPD4KICAgICAgICAgIEludGVnZXIudG9fc3RyaW5nKFN5c3RlbS51bmlxdWVfaW50ZWdlcihbOnBvc2l0aXZlXSkpIDw+ICItIiA8PiBwaGFzZSA8PiAiLmpzb24iCiAgICAgICkKCiAgICBvdXRwdXQgPSBQYXRoLmpvaW4ocm9vdCwgImNvbXBpbGVkLSIgPD4gcGhhc2UgPD4gIi5qc29uIikKCiAgICBGaWxlLndyaXRlISgKICAgICAgZml4dHVyZSwKICAgICAgSmFzb24uZW5jb2RlISglewogICAgICAgIHVybDogImh0dHA6Ly8xMjcuMC4wLjE6I3tjLmh0dHBfcG9ydH0iLAogICAgICAgIHB1YmxpY09yaWdpbjogYy5jb25maWcucHVibGljX29yaWdpbiwKICAgICAgICBjb29raWU6IGNvb2tpZSwKICAgICAgICBwcm9qZWN0OiBNYXAudGFrZShwYWdlLCBbIm9yZ2FuaXphdGlvbklkIiwgInByb2plY3RJZCJdKSwKICAgICAgICBwaGFzZTogcGhhc2UsCiAgICAgICAgb3V0cHV0OiBvdXRwdXQsCiAgICAgICAgcHJldmlvdXM6IFBhdGguam9pbihyb290LCAiY29tcGlsZWQtcXVldWVkLmpzb24iKQogICAgICB9KQogICAgKQoKICAgIHRyeSBkbwogICAgICB7b3V0LCBjb2RlfSA9CiAgICAgICAgU3lzdGVtLmNtZCgKICAgICAgICAgIFN5c3RlbS5maW5kX2V4ZWN1dGFibGUoIm5vZGUiKSB8fCByYWlzZSgibm9kZSB1bmF2YWlsYWJsZSIpLAogICAgICAgICAgW1N5c3RlbS5mZXRjaF9lbnYhKCJNSVhFUl9CUk9XU0VSX0NBVEFMT0dfTk9ERV9EUklWRVIiKSwgZml4dHVyZV0sCiAgICAgICAgICBzdGRlcnJfdG9fc3Rkb3V0OiB0cnVlCiAgICAgICAgKQoKICAgICAgRmlsZS53cml0ZSEoUGF0aC5qb2luKHJvb3QsICJub2RlLSIgPD4gcGhhc2UgPD4gIi5zdGRvdXQiKSwgb3V0KQogICAgICBhc3NlcnQgY29kZSA9PSAwLCBvdXQKICAgICAgcmVzdWx0ID0gb3V0cHV0IHw+IEZpbGUucmVhZCEoKSB8PiBKYXNvbi5kZWNvZGUhKCkKICAgICAgYXNzZXJ0IHJlc3VsdFsic3RhdHVzIl0gPT0gIlBBU1MiCiAgICAgIGFzc2VydCByZXN1bHRbImR0byJdID09IGV4cGVjdGVkCiAgICAgIGFzc2VydCBtYXBfc2l6ZShyZXN1bHRbInNlbGVjdGlvbiJdKSA9PSA4CiAgICBhZnRlcgogICAgICBGaWxlLnJtIShmaXh0dXJlKQogICAgZW5kCiAgZW5kCgogIGRlZnAgY2F0YWxvZ19maXh0dXJlX3Jvd3MgZG8KICAgIGJ1aWxkcyA9CiAgICAgIEYucSEoCiAgICAgICAgQWRtaW4sCiAgICAgICAgIlNFTEVDVCBpZDo6dGV4dCwgcmVxdWVzdF9rZXksIHJldmlzaW9uLCBqb3VybmFsIEZST00gbWl4ZXJfYnVpbGRzIFdIRVJFIG9yZ2FuaXphdGlvbl9pZD0nb3JnLWEnIEFORCBwcm9qZWN0X2lkPSdwcm9qZWN0LWEnIEFORCBhcHBsaWNhdGlvbl9pZD0nZmllbGRsb2cnIEFORCBidWlsZF9pZD0nYnVpbGQtYScgQU5EIHBsYXRmb3JtPSdpb3MnIgogICAgICApLnJvd3MKCiAgICBqb2JzID0KICAgICAgRi5xISgKICAgICAgICBBZG1pbiwKICAgICAgICAiU0VMRUNUIGlkLCBhcmdzIEZST00gb2Jhbl9qb2JzIFdIRVJFIGFyZ3MtPj4nb3JnYW5pemF0aW9uX2lkJz0nb3JnLWEnIEFORCBhcmdzLT4+J3Byb2plY3RfaWQnPSdwcm9qZWN0LWEnIEFORCBhcmdzLT4+J2FwcGxpY2F0aW9uX2lkJz0nZmllbGRsb2cnIEFORCBhcmdzLT4+J2J1aWxkX2lkJz0nYnVpbGQtYScgQU5EIGFyZ3MtPj4ncGxhdGZvcm0nPSdpb3MnIE9SREVSIEJZIGlkIgogICAgICApLnJvd3MKCiAgICAle2J1aWxkczogYnVpbGRzLCBqb2JzOiBqb2JzfQogIGVuZAoKICBkZWZwIG93bl9jYXRhbG9nX2ZpeHR1cmUhIGRvCiAgICBhc3NlcnQgY2F0YWxvZ19maXh0dXJlX3Jvd3MoKSA9PSAle2J1aWxkczogW10sIGpvYnM6IFtdfQoKICAgIGFzc2VydCBbXSA9PQogICAgICAgICAgICAgRi5xISgKICAgICAgICAgICAgICAgQWRtaW4sCiAgICAgICAgICAgICAgICJTRUxFQ1QgaWQgRlJPTSBtaXhlcl9hdXRoel9hcHBsaWNhdGlvbnMgV0hFUkUgKG9yZ2FuaXphdGlvbl9pZD0nb3JnLWEnIEFORCBwcm9qZWN0X2lkPSdwcm9qZWN0LWEnIEFORCBpZD0nZW1wdHktYXBwJykgT1IgKG9yZ2FuaXphdGlvbl9pZD0nb3JnLWInIEFORCBwcm9qZWN0X2lkPSdwcm9qZWN0LWInIEFORCBpZD0nZmllbGRsb2cnKSIKICAgICAgICAgICAgICkucm93cwoKICAgIHJvb3QgPSBTeXN0ZW0uZmV0Y2hfZW52ISgiTUlYRVJfQlJPV1NFUl9DQVRBTE9HX0ZJWFRVUkVfUk9PVCIpCiAgICBvd25lciA9IFBhdGguam9pbihyb290LCAib3duZWQtYnVpbGQuanNvbiIpCiAgICBGaWxlLndyaXRlIShQYXRoLmpvaW4ocm9vdCwgInByaW9yLWFic2VuY2UuanNvbiIpLCBKYXNvbi5lbmNvZGUhKGNhdGFsb2dfZml4dHVyZV9yb3dzKCkpKQoKICAgIG9uX2V4aXQoZm4gLT4KICAgICAgaWYgRmlsZS5leGlzdHM/KG93bmVyKSBkbwogICAgICAgICV7ImJ1aWxkX2lkIiA9PiBpZCwgImpvYl9pZHMiID0+IGpvYnN9ID0gb3duZXIgfD4gRmlsZS5yZWFkISgpIHw+IEphc29uLmRlY29kZSEoKQogICAgICAgIHJvd3MgPSBjYXRhbG9nX2ZpeHR1cmVfcm93cygpCgogICAgICAgIGFzc2VydCBFbnVtLmFsbD8ocm93cy5idWlsZHMsIGZuIFthY3R1YWwsIGtleSwgXywgX10gLT4KICAgICAgICAgICAgICAgICBhY3R1YWwgPT0gaWQgYW5kIGtleSA9PSAicjExMDQtYnVpbGQiCiAgICAgICAgICAgICAgIGVuZCkKCiAgICAgICAgYXNzZXJ0IEVudW0uYWxsPyhyb3dzLmpvYnMsIGZuIFtqb2IsIGFyZ3NdIC0+CiAgICAgICAgICAgICAgICAgam9iIGluIGpvYnMgYW5kIGFyZ3NbImJ1aWxkX3JlY29yZF9pZCJdID09IGlkCiAgICAgICAgICAgICAgIGVuZCkKCiAgICAgICAgezpvaywgY2xlYW5lZH0gPQogICAgICAgICAgQWRtaW4udHJhbnNhY3Rpb24oZm4gLT4KICAgICAgICAgICAgZGVsZXRlZF9qb2JzID0KICAgICAgICAgICAgICBGLnEhKAogICAgICAgICAgICAgICAgQWRtaW4sCiAgICAgICAgICAgICAgICAiREVMRVRFIEZST00gb2Jhbl9qb2JzIFdIRVJFIGlkPUFOWSgkMTo6YmlnaW50W10pIEFORCBhcmdzLT4+J2J1aWxkX3JlY29yZF9pZCc9JDIgUkVUVVJOSU5HIGlkIiwKICAgICAgICAgICAgICAgIFtqb2JzLCBpZF0KICAgICAgICAgICAgICApLnJvd3MKCiAgICAgICAgICAgIGRlbGV0ZWRfYnVpbGQgPQogICAgICAgICAgICAgIEYucSEoCiAgICAgICAgICAgICAgICBBZG1pbiwKICAgICAgICAgICAgICAgICJERUxFVEUgRlJPTSBtaXhlcl9idWlsZHMgV0hFUkUgaWQ9JDE6OnV1aWQgQU5EIHJlcXVlc3Rfa2V5PSdyMTEwNC1idWlsZCcgQU5EIG9yZ2FuaXphdGlvbl9pZD0nb3JnLWEnIEFORCBwcm9qZWN0X2lkPSdwcm9qZWN0LWEnIEFORCBhcHBsaWNhdGlvbl9pZD0nZmllbGRsb2cnIEFORCBidWlsZF9pZD0nYnVpbGQtYScgQU5EIHBsYXRmb3JtPSdpb3MnIFJFVFVSTklORyBpZDo6dGV4dCIsCiAgICAgICAgICAgICAgICBbRWN0by5VVUlELmR1bXAhKGlkKV0KICAgICAgICAgICAgICApLnJvd3MKCiAgICAgICAgICAgIGFzc2VydCBkZWxldGVkX2J1aWxkID09IFtbaWRdXQogICAgICAgICAgICBhc3NlcnQgRW51bS5zb3J0KExpc3QuZmxhdHRlbihkZWxldGVkX2pvYnMpKSA9PSBFbnVtLnNvcnQoam9icykKCiAgICAgICAgICAgIGFwcHMgPQogICAgICAgICAgICAgIEYucSEoCiAgICAgICAgICAgICAgICBBZG1pbiwKICAgICAgICAgICAgICAgICJERUxFVEUgRlJPTSBtaXhlcl9hdXRoel9hcHBsaWNhdGlvbnMgV0hFUkUgKG9yZ2FuaXphdGlvbl9pZD0nb3JnLWEnIEFORCBwcm9qZWN0X2lkPSdwcm9qZWN0LWEnIEFORCBpZD0nZW1wdHktYXBwJykgT1IgKG9yZ2FuaXphdGlvbl9pZD0nb3JnLWInIEFORCBwcm9qZWN0X2lkPSdwcm9qZWN0LWInIEFORCBpZD0nZmllbGRsb2cnKSBSRVRVUk5JTkcgb3JnYW5pemF0aW9uX2lkLHByb2plY3RfaWQsaWQiCiAgICAgICAgICAgICAgKS5yb3dzCgogICAgICAgICAgICAlewogICAgICAgICAgICAgIGJ1aWxkX2lkOiBpZCwKICAgICAgICAgICAgICBqb2JfaWRzOiBqb2JzLAogICAgICAgICAgICAgIHJlbW92ZWRfYXBwbGljYXRpb25zOiBhcHBzLAogICAgICAgICAgICAgIHRlcm1pbmFsX2JlZm9yZV9jbGVhbnVwOiByb3dzCiAgICAgICAgICAgIH0KICAgICAgICAgIGVuZCkKCiAgICAgICAgYXNzZXJ0IGNhdGFsb2dfZml4dHVyZV9yb3dzKCkgPT0gJXtidWlsZHM6IFtdLCBqb2JzOiBbXX0KICAgICAgICBGaWxlLndyaXRlIShQYXRoLmpvaW4ocm9vdCwgImZpeHR1cmUtY2xlYW51cC5qc29uIiksIEphc29uLmVuY29kZSEoY2xlYW5lZCkpCiAgICAgIGVuZAogICAgZW5kKQogIGVuZAoKICBkZWZwIGNhcHR1cmVfY2F0YWxvZ19maXh0dXJlISBkbwogICAgJXtidWlsZHM6IFtbaWQsICJyMTEwNC1idWlsZCIsIDAsIF9dXSwgam9iczogam9ic30gPSBjYXRhbG9nX2ZpeHR1cmVfcm93cygpCiAgICBhc3NlcnQgam9icyAhPSBbXQogICAgYXNzZXJ0IEVudW0uYWxsPyhqb2JzLCBmbiBbXywgYXJnc10gLT4gYXJnc1siYnVpbGRfcmVjb3JkX2lkIl0gPT0gaWQgZW5kKQoKICAgIEZpbGUud3JpdGUhKAogICAgICBQYXRoLmpvaW4oU3lzdGVtLmZldGNoX2VudiEoIk1JWEVSX0JST1dTRVJfQ0FUQUxPR19GSVhUVVJFX1JPT1QiKSwgIm93bmVkLWJ1aWxkLmpzb24iKSwKICAgICAgSmFzb24uZW5jb2RlISgle2J1aWxkX2lkOiBpZCwgam9iX2lkczogRW51bS5tYXAoam9icywgJmhkLzEpfSkKICAgICkKICBlbmQKCiAgZGVmcCBidWlsZF9zZWxlY3Rpb24gZG8KICAgICV7CiAgICAgIG9yZ2FuaXphdGlvbl9pZDogIm9yZy1hIiwKICAgICAgcHJvamVjdF9pZDogInByb2plY3QtYSIsCiAgICAgIGFwcGxpY2F0aW9uX2lkOiAiZmllbGRsb2ciLAogICAgICBidWlsZF9pZDogImJ1aWxkLWEiLAogICAgICBwbGF0Zm9ybTogImlvcyIsCiAgICAgIHNvdXJjZV9zaGEyNTY6IFN0cmluZy5kdXBsaWNhdGUoImEiLCA2NCksCiAgICAgIHRvb2xjaGFpbl9sb2NrX3NoYTI1NjogU3RyaW5nLmR1cGxpY2F0ZSgiYiIsIDY0KSwKICAgICAgYnVpbGRfZGVmaW5pdGlvbl9zaGEyNTY6IFN0cmluZy5kdXBsaWNhdGUoImMiLCA2NCkKICAgIH0KICBlbmQKCiAgZGVmcCBidWlsZF9wYXRoKHNlbGVjdGlvbiksIGRvOiAiL2NvbnNvbGUtYXBpL3YxL2J1aWxkcz8iIDw+IFVSSS5lbmNvZGVfcXVlcnkoc2VsZWN0aW9uKQoKICBkZWZwIGNyZWF0ZV9idWlsZCBkbwogICAgcyA9IGJ1aWxkX3NlbGVjdGlvbigpCgogICAgc3BlYyA9CiAgICAgIE1hcC50YWtlKHMsIFs6b3JnYW5pemF0aW9uX2lkLCA6cHJvamVjdF9pZCwgOmFwcGxpY2F0aW9uX2lkLCA6YnVpbGRfaWRdKQogICAgICB8PiBNYXAubWVyZ2UoJXsKICAgICAgICBwbGF0Zm9ybTogOmlvcywKICAgICAgICBzb3VyY2U6ICV7a2luZDogOnJldmlzaW9uLCBzaGEyNTY6IHMuc291cmNlX3NoYTI1NiwgcmVmZXJlbmNlOiAiaW1tdXRhYmxlLXRlc3QtcmV2aXNpb24ifSwKICAgICAgICB0b29sY2hhaW5fbG9ja19zaGEyNTY6IHMudG9vbGNoYWluX2xvY2tfc2hhMjU2LAogICAgICAgIGJ1aWxkX2RlZmluaXRpb25fc2hhMjU2OiBzLmJ1aWxkX2RlZmluaXRpb25fc2hhMjU2CiAgICAgIH0pCgogICAgbXVsdGkgPQogICAgICBNaXhlckhvc3RlZC5CdWlsZHMuU3RvcmFnZS5jcmVhdGVfbXVsdGkoCiAgICAgICAgRWN0by5NdWx0aS5uZXcoKSwKICAgICAgICA6YnVpbGQsCiAgICAgICAgc3BlYywKICAgICAgICAle21heF9hdHRlbXB0czogMiwgdGltZW91dF9tczogMTAwLCByZXRyeV9iYWNrb2ZmX21zOiAwfSwKICAgICAgICAicjExMDQtYnVpbGQiLAogICAgICAgIDAsCiAgICAgICAgJk1peGVySG9zdGVkLkJ1aWxkcy5Db29yZGluYXRvci5uZXcvMQogICAgICApCgogICAgYXNzZXJ0IHs6b2ssIF99ID0gQWRtaW4udHJhbnNhY3Rpb24obXVsdGkpCiAgICBzCiAgZW5kCgogICMgUjExNjYgZXhwbGljaXQgcHJpdmF0ZSBjYXRhbG9nIGF1dGhvcml0eSBpbnN0YWxsZXI7IHByb2R1Y3Rpb24gbWlncmF0aW9uIHNldCB1bmNoYW5nZWQuCiAgc2V0dXBfYWxsIGMgZG8KICAgIG9ic2VydmUgPSBmbiBwcm9maWxlLCBleHBlY3RlZCAtPgogICAgICBydW50aW1lID0gJXtjLnJ1bnRpbWUgfCBhZG1pc3Npb25fcHJvZmlsZTogcHJvZmlsZX0KICAgICAgcGlkID0gc3RhcnRfc3VwZXJ2aXNlZCEoe1J1bnRpbWVPd25lciwgcnVudGltZX0pCiAgICAgIGFzc2VydCBSdW50aW1lT3duZXIuc3RhdHVzKCkucGhhc2UgPT09IGV4cGVjdGVkCiAgICAgIHJlc3VsdCA9IFJ1bnRpbWVPd25lci5ib290c3RyYXAoJXtyZXF1ZXN0X2lkOiBTdHJpbmcuZHVwbGljYXRlKCJhIiwgMzIpfSkKCiAgICAgIGlmIGV4cGVjdGVkID09IDpzdG9yYWdlX3JlYWR5IGRvCiAgICAgICAgYXNzZXJ0IG1hdGNoPyh7Om9rLCBffSwgcmVzdWx0KSwgaW5zcGVjdChyZXN1bHQpCiAgICAgIGVsc2UKICAgICAgICBhc3NlcnQgbWF0Y2g/KHs6ZXJyb3IsIF99LCByZXN1bHQpLCBpbnNwZWN0KHJlc3VsdCkKICAgICAgZW5kCgogICAgICBhc3NlcnQgUHJvY2Vzcy5hbGl2ZT8ocGlkKQogICAgICBzdG9wX3N1cGVydmlzZWQhKFJ1bnRpbWVPd25lcikKICAgICAgJXtwcm9maWxlOiBwcm9maWxlLCBzdGFydHVwOiBleHBlY3RlZCwgc3Vic2VxdWVudF9zdG9yZTogaW5zcGVjdChlbGVtKHJlc3VsdCwgMCkpfQogICAgZW5kCgogICAgYmFzZWxpbmUgPSBbCiAgICAgIG9ic2VydmUuKDpicm93c2VyX2F1dGhfdjIsIDpzdG9yYWdlX3JlYWR5KSwKICAgICAgb2JzZXJ2ZS4oOmJ1aWxkX2NhdGFsb2dfdjMsIDp1bmF2YWlsYWJsZSkKICAgIF0KCiAgICBmb3Igc3FsIDwtIE1peGVySG9zdGVkLkN1c3RvbWVyQnVpbGRDYXRhbG9nLlNjaGVtYS5wcml2YXRlX3N0YXRlbWVudHMoKSwgZG86IEYucSEoQWRtaW4sIHNxbCkKCiAgICBpbnN0YWxsZWQgPSBbCiAgICAgIG9ic2VydmUuKDpicm93c2VyX2F1dGhfdjIsIDp1bmF2YWlsYWJsZSksCiAgICAgIG9ic2VydmUuKDpidWlsZF9jYXRhbG9nX3YzLCA6c3RvcmFnZV9yZWFkeSkKICAgIF0KCiAgICBGaWxlLndyaXRlISgKICAgICAgUGF0aC5qb2luKAogICAgICAgIFN5c3RlbS5mZXRjaF9lbnYhKCJNSVhFUl9CUk9XU0VSX0NBVEFMT0dfRklYVFVSRV9ST09UIiksCiAgICAgICAgImZvdXItc3RhcnR1cC1zdG9yZS1jYXNlcy5qc29uIgogICAgICApLAogICAgICBKYXNvbi5lbmNvZGUhKCV7YmFzZWxpbmU6IGJhc2VsaW5lLCBpbnN0YWxsZWQ6IGluc3RhbGxlZH0pCiAgICApCgogICAgOm9rCiAgZW5kCgogIEB0YWcgOmNhdGFsb2dfYnJvd3Nlcl9jdXJyZW50X3N1cmZhY2Vfam9pbgogIEB0YWcgOnIxMTU4CiAgdGVzdCAiUjExNTggZ2VudWluZSBQS0NFIGFwcGxpY2F0aW9uIHNlbGVjdGlvbiBjYXRhbG9nIHF1ZXVlZCBkZXRhaWwgdGVybWluYWwgcmVmcmVzaCIsIGMgZG8KICAgIG93bl9jYXRhbG9nX2ZpeHR1cmUhKCkKICAgIGNyZWF0ZV9idWlsZCgpCiAgICBjYXB0dXJlX2NhdGFsb2dfZml4dHVyZSEoKQoKICAgIEYucSEoCiAgICAgIEFkbWluLAogICAgICAiSU5TRVJUIElOVE8gbWl4ZXJfYXV0aHpfYXBwbGljYXRpb25zIFZBTFVFUygnb3JnLWEnLCdwcm9qZWN0LWEnLCdlbXB0eS1hcHAnLHRydWUpLCgnb3JnLWInLCdwcm9qZWN0LWInLCdmaWVsZGxvZycsdHJ1ZSkiCiAgICApCgogICAgcHJlYXV0aCA9IGJvb3RzdHJhcF9odHRwKGMpCiAgICBsb2dpbiA9IGJlZ2luX2h0dHAoYywgcHJlYXV0aCkKICAgIGFjdGl2YXRpb24gPSBodHRwKGMsICIvYXV0aC9jYWxsYmFjaz8iIDw+IGxvZ2luLnF1ZXJ5LCBsb2dpbi5oZWFkZXJzKQogICAgYXNzZXJ0IGFjdGl2YXRpb24uc3RhdHVzID09IDMwMwogICAgY29va2llID0gcmVzcG9uc2VfY29va2llKGFjdGl2YXRpb24pCiAgICBocyA9IGhlYWRlcnMoY29va2llKQogICAgcHJvamVjdCA9ICJvcmdhbml6YXRpb25faWQ9b3JnLWEmcHJvamVjdF9pZD1wcm9qZWN0LWEiCiAgICBhcHBsaWNhdGlvbnMgPSBodHRwKGMsICIvY29uc29sZS1hcGkvdjEvYXBwbGljYXRpb25zPyIgPD4gcHJvamVjdCwgaHMpCiAgICBhc3NlcnQgYXBwbGljYXRpb25zLnN0YXR1cyA9PSAyMDAKICAgIHBhZ2UgPSBKYXNvbi5kZWNvZGUhKGFwcGxpY2F0aW9ucy5ib2R5KQoKICAgIGFzc2VydCBwYWdlID09ICV7CiAgICAgICAgICAgICAib3JnYW5pemF0aW9uSWQiID0+ICJvcmctYSIsCiAgICAgICAgICAgICAicHJvamVjdElkIiA9PiAicHJvamVjdC1hIiwKICAgICAgICAgICAgICJhcHBsaWNhdGlvbnMiID0+IFsKICAgICAgICAgICAgICAgJXsiYXBwbGljYXRpb25JZCIgPT4gImVtcHR5LWFwcCJ9LAogICAgICAgICAgICAgICAleyJhcHBsaWNhdGlvbklkIiA9PiAiZmllbGRsb2cifQogICAgICAgICAgICAgXSwKICAgICAgICAgICAgICJuZXh0Q3Vyc29yIiA9PiBuaWwKICAgICAgICAgICB9CgogICAgYXNzZXJ0IGh0dHAoYywgIi9jb25zb2xlLWFwaS92MS9idWlsZC1jYXRhbG9nPyIgPD4gcHJvamVjdCA8PiAiJmFwcGxpY2F0aW9uX2lkPWVtcHR5LWFwcCIsIGhzKS5ib2R5CiAgICAgICAgICAgfD4gSmFzb24uZGVjb2RlISgpID09ICV7CiAgICAgICAgICAgICAib3JnYW5pemF0aW9uSWQiID0+ICJvcmctYSIsCiAgICAgICAgICAgICAicHJvamVjdElkIiA9PiAicHJvamVjdC1hIiwKICAgICAgICAgICAgICJhcHBsaWNhdGlvbklkIiA9PiAiZW1wdHktYXBwIiwKICAgICAgICAgICAgICJidWlsZHMiID0+IFtdLAogICAgICAgICAgICAgIm5leHRDdXJzb3IiID0+IG5pbAogICAgICAgICAgIH0KCiAgICBjYXRhbG9nX3BhdGggPSAiL2NvbnNvbGUtYXBpL3YxL2J1aWxkLWNhdGFsb2c/IiA8PiBwcm9qZWN0IDw+ICImYXBwbGljYXRpb25faWQ9ZmllbGRsb2ciCiAgICBsaXN0ZWQgPSBodHRwKGMsIGNhdGFsb2dfcGF0aCwgaHMpCiAgICBhc3NlcnQgbGlzdGVkLnN0YXR1cyA9PSAyMDAKICAgIFtkdG9dID0gSmFzb24uZGVjb2RlIShsaXN0ZWQuYm9keSlbImJ1aWxkcyJdCiAgICBhc3NlcnQgZHRvWyJzdGF0ZSJdID09ICJxdWV1ZWQiIGFuZCBtYXBfc2l6ZShkdG8pID09IDE0CgogICAgd2lyZSA9IFsKICAgICAgeyJvcmdhbml6YXRpb25JZCIsIDpvcmdhbml6YXRpb25faWR9LAogICAgICB7InByb2plY3RJZCIsIDpwcm9qZWN0X2lkfSwKICAgICAgeyJhcHBsaWNhdGlvbklkIiwgOmFwcGxpY2F0aW9uX2lkfSwKICAgICAgeyJidWlsZElkIiwgOmJ1aWxkX2lkfSwKICAgICAgeyJwbGF0Zm9ybSIsIDpwbGF0Zm9ybX0sCiAgICAgIHsic291cmNlU2hhMjU2IiwgOnNvdXJjZV9zaGEyNTZ9LAogICAgICB7InRvb2xjaGFpbkxvY2tTaGEyNTYiLCA6dG9vbGNoYWluX2xvY2tfc2hhMjU2fSwKICAgICAgeyJidWlsZERlZmluaXRpb25TaGEyNTYiLCA6YnVpbGRfZGVmaW5pdGlvbl9zaGEyNTZ9CiAgICBdCgogICAgc2VsZWN0ZWQgPSBNYXAubmV3KHdpcmUsIGZuIHtrZXksIGF0b219IC0+IHthdG9tLCBNYXAuZmV0Y2ghKGR0bywga2V5KX0gZW5kKQogICAgYXNzZXJ0IHs6b2ssIF99ID0gTWl4ZXJIb3N0ZWQuQ3VzdG9tZXJCdWlsZHMuU2VsZWN0aW9uLm5ldyhzZWxlY3RlZCkKICAgIGRldGFpbCA9IGh0dHAoYywgYnVpbGRfcGF0aChzZWxlY3RlZCksIGhzKQogICAgYXNzZXJ0IGRldGFpbC5zdGF0dXMgPT0gMjAwCiAgICBhc3NlcnQgSmFzb24uZGVjb2RlIShkZXRhaWwuYm9keSlbImJ1aWxkIl0gPT0gZHRvCiAgICBjb21waWxlZF9jYXRhbG9nX2pvaW4oYywgY29va2llLCBwYWdlLCAicXVldWVkIiwgZHRvKQoKICAgIFtbam91cm5hbF1dID0KICAgICAgRi5xISgKICAgICAgICBBZG1pbiwKICAgICAgICAiU0VMRUNUIGpvdXJuYWwgRlJPTSBtaXhlcl9idWlsZHMgV0hFUkUgb3JnYW5pemF0aW9uX2lkPSdvcmctYScgQU5EIHByb2plY3RfaWQ9J3Byb2plY3QtYScgQU5EIGFwcGxpY2F0aW9uX2lkPSdmaWVsZGxvZycgQU5EIGJ1aWxkX2lkPSdidWlsZC1hJyBBTkQgcGxhdGZvcm09J2lvcyciCiAgICAgICkucm93cwoKICAgIGFzc2VydCB7Om9rLCBidWlsZH0gPSBNaXhlckhvc3RlZC5CdWlsZHMuSm91cm5hbC5yZXN0b3JlKGpvdXJuYWwpCiAgICBhc3NlcnQgezpvaywgcmVmfSA9IE1peGVySG9zdGVkLkJ1aWxkcy5MaWZlY3ljbGUud29ya2VyX3JlZihidWlsZCkKCiAgICBhc3NlcnQgezpvaywgcnVubmluZywgXywgOmFwcGxpZWR9ID0KICAgICAgICAgICAgIE1peGVySG9zdGVkLkJ1aWxkcy5Kb3VybmFsLmFwcGVuZCgKICAgICAgICAgICAgICAgam91cm5hbCwKICAgICAgICAgICAgICAgInIxMTU4LXN0YXJ0IiwKICAgICAgICAgICAgICAgJXt0eXBlOiA6c3RhcnQsIHJlZjogcmVmfSwKICAgICAgICAgICAgICAgMQogICAgICAgICAgICAgKQoKICAgIGFzc2VydCB7Om9rLCBmYWlsZWQsIF8sIDphcHBsaWVkfSA9CiAgICAgICAgICAgICBNaXhlckhvc3RlZC5CdWlsZHMuSm91cm5hbC5hcHBlbmQoCiAgICAgICAgICAgICAgIHJ1bm5pbmcsCiAgICAgICAgICAgICAgICJyMTE1OC1mYWlsIiwKICAgICAgICAgICAgICAgJXsKICAgICAgICAgICAgICAgICB0eXBlOiA6Y29tcGxldGVkLAogICAgICAgICAgICAgICAgIHJlZjogcmVmLAogICAgICAgICAgICAgICAgIHJlc3VsdDogJXsKICAgICAgICAgICAgICAgICAgIG91dGNvbWU6IDpmYWlsZWQsCiAgICAgICAgICAgICAgICAgICBjbGFzczogOmNvbXBpbGVyLAogICAgICAgICAgICAgICAgICAgY29kZTogOmNvbXBpbGVyX2Vycm9yLAogICAgICAgICAgICAgICAgICAgZGlhZ25vc3RpY19zaGEyNTY6IFN0cmluZy5kdXBsaWNhdGUoImQiLCA2NCkKICAgICAgICAgICAgICAgICB9CiAgICAgICAgICAgICAgIH0sCiAgICAgICAgICAgICAgIDIKICAgICAgICAgICAgICkKCiAgICBGLnEhKAogICAgICBBZG1pbiwKICAgICAgIlVQREFURSBtaXhlcl9idWlsZHMgU0VUIGpvdXJuYWw9JDEscmV2aXNpb249MiBXSEVSRSBvcmdhbml6YXRpb25faWQ9J29yZy1hJyBBTkQgcHJvamVjdF9pZD0ncHJvamVjdC1hJyBBTkQgYXBwbGljYXRpb25faWQ9J2ZpZWxkbG9nJyBBTkQgYnVpbGRfaWQ9J2J1aWxkLWEnIEFORCBwbGF0Zm9ybT0naW9zJyIsCiAgICAgIFtmYWlsZWRdCiAgICApCgogICAgcmVmcmVzaGVkID0gaHR0cChjLCBidWlsZF9wYXRoKHNlbGVjdGVkKSwgaHMpCiAgICBhc3NlcnQgcmVmcmVzaGVkLnN0YXR1cyA9PSAyMDAKICAgIHRlcm1pbmFsID0gSmFzb24uZGVjb2RlIShyZWZyZXNoZWQuYm9keSlbImJ1aWxkIl0KCiAgICBhc3NlcnQgdGVybWluYWxbInN0YXRlIl0gPT0gImZhaWxlZCIgYW5kIHRlcm1pbmFsWyJyZXZpc2lvbiJdID09IDIgYW5kCiAgICAgICAgICAgICB0ZXJtaW5hbFsiZmFpbHVyZUNvZGUiXSA9PSAiY29tcGlsZXJfZXJyb3IiCgogICAgW150ZXJtaW5hbF0gPSBKYXNvbi5kZWNvZGUhKGh0dHAoYywgY2F0YWxvZ19wYXRoLCBocykuYm9keSlbImJ1aWxkcyJdCiAgICBjb21waWxlZF9jYXRhbG9nX2pvaW4oYywgY29va2llLCBwYWdlLCAidGVybWluYWwiLCB0ZXJtaW5hbCkKCiAgICBhc3NlcnQgaHR0cChjLCAiL2NvbnNvbGUtYXBpL3YxL2FwcGxpY2F0aW9ucz9vcmdhbml6YXRpb25faWQ9b3JnLWImcHJvamVjdF9pZD1wcm9qZWN0LWIiLCBocykuc3RhdHVzID09CiAgICAgICAgICAgICA0MDQKCiAgICBhc3NlcnQgezplcnJvciwgJVBvc3RncmV4LkVycm9ye3Bvc3RncmVzOiAle2NvZGU6IDppbnN1ZmZpY2llbnRfcHJpdmlsZWdlfX19ID0KICAgICAgICAgICAgIEVjdG8uQWRhcHRlcnMuU1FMLnF1ZXJ5KE1peGVySG9zdGVkLlJlcG8sICJTRUxFQ1Qgam91cm5hbCBGUk9NIG1peGVyX2J1aWxkcyIsIFtdKQoKICAgIGFzc2VydCBbXSA9PSBGLnEhKE1peGVySG9zdGVkLlJlcG8sICJTRUxFQ1QgaWQgRlJPTSBtaXhlcl9hdXRoel9hcHBsaWNhdGlvbnMiKS5yb3dzCiAgICBhc3NlcnQgaHR0cChjLCAiL3YzL2J1aWxkLWNhdGFsb2ciLCBocykuc3RhdHVzID09IDQwNAoKICAgIEZpbGUud3JpdGUhKAogICAgICBTeXN0ZW0uZmV0Y2hfZW52ISgiTUlYRVJfQlJPV1NFUl9DQVRBTE9HX0VWSURFTkNFIiksCiAgICAgIEphc29uLmVuY29kZSEoJXsKICAgICAgICBhcHBsaWNhdGlvbnM6IHBhZ2UsCiAgICAgICAgY2F0YWxvZzogZHRvLAogICAgICAgIHNlbGVjdGVkOiBzZWxlY3RlZCwKICAgICAgICBkZXRhaWw6IEphc29uLmRlY29kZSEoZGV0YWlsLmJvZHkpLAogICAgICAgIHRlcm1pbmFsOiB0ZXJtaW5hbCwKICAgICAgICByZWFsX3BrY2U6IHRydWUsCiAgICAgICAgYnVpbGRfc2VsZWN0OiAiNDI1MDEiLAogICAgICAgIGRpcmVjdF9hcHBsaWNhdGlvbl9yb3dzOiAwCiAgICAgIH0pCiAgICApCgogICAgbGVhc2VzX2NsZWFuKCkKICBlbmQKCiAgQHRhZyA6cjExMDQKICB0ZXN0ICJSMTEwNCBnZW51aW5lIFBLQ0UgY29va2llIGFkbWl0cyBleGFjdCBxdWV1ZWQgYW5kIHRlcm1pbmFsIGJ1aWxkIHRoZW4gY2xvc2VkIHJlZnVzYWxzIiwKICAgICAgIGMgZG8KICAgIHNlbGVjdGVkID0gY3JlYXRlX2J1aWxkKCkKCiAgICBbW2ZhbHNlLCBmYWxzZSwgZmFsc2VdXSA9CiAgICAgIEYucSEoCiAgICAgICAgTWl4ZXJIb3N0ZWQuUmVwbywKICAgICAgICAiU0VMRUNUIHJvbHN1cGVyLHJvbGJ5cGFzc3JscyxoYXNfdGFibGVfcHJpdmlsZWdlKGN1cnJlbnRfdXNlciwncHVibGljLm1peGVyX2J1aWxkcycsJ1NFTEVDVCcpIEZST00gcGdfcm9sZXMgV0hFUkUgcm9sbmFtZT1jdXJyZW50X3VzZXIiCiAgICAgICkucm93cwoKICAgIHAgPSBib290c3RyYXBfaHR0cChjKQogICAgbG9naW4gPSBiZWdpbl9odHRwKGMsIHApCiAgICByZXNwb25zZSA9IGh0dHAoYywgIi9hdXRoL2NhbGxiYWNrPyIgPD4gbG9naW4ucXVlcnksIGxvZ2luLmhlYWRlcnMpCiAgICBhc3NlcnQgcmVzcG9uc2Uuc3RhdHVzID09IDMwMwogICAgY29va2llID0gcmVzcG9uc2VfY29va2llKHJlc3BvbnNlKQogICAgaHMgPSBoZWFkZXJzKGNvb2tpZSkKICAgIGFzc2VydCBjb29raWUgIT0gcC5jb29raWUKCiAgICBiZWZvcmUgPQogICAgICBGLnEhKAogICAgICAgIEFkbWluLAogICAgICAgICJTRUxFQ1QgKFNFTEVDVCBjb3VudCgqKSBGUk9NIHB1YmxpYy5vYmFuX2pvYnMpLChTRUxFQ1QgY291bnQoKikgRlJPTSBwdWJsaWMubWl4ZXJfYnVpbGRzKSIKICAgICAgKS5yb3dzCgogICAgciA9IGh0dHAoYywgYnVpbGRfcGF0aChzZWxlY3RlZCksIGhzKQogICAgYXNzZXJ0IHIuc3RhdHVzID09IDIwMCwgaW5zcGVjdChyKQogICAgZHRvID0gSmFzb24uZGVjb2RlIShyLmJvZHkpWyJidWlsZCJdCiAgICBhc3NlcnQgbWFwX3NpemUoZHRvKSA9PSAxNAogICAgYXNzZXJ0IGR0b1sic3RhdGUiXSA9PSAicXVldWVkIiBhbmQgZHRvWyJyZXZpc2lvbiJdID09IDAKCiAgICBmb3Ige3dpcmUsIGtleX0gPC0gWwogICAgICAgICAgeyJvcmdhbml6YXRpb25JZCIsIDpvcmdhbml6YXRpb25faWR9LAogICAgICAgICAgeyJwcm9qZWN0SWQiLCA6cHJvamVjdF9pZH0sCiAgICAgICAgICB7ImFwcGxpY2F0aW9uSWQiLCA6YXBwbGljYXRpb25faWR9LAogICAgICAgICAgeyJidWlsZElkIiwgOmJ1aWxkX2lkfSwKICAgICAgICAgIHsicGxhdGZvcm0iLCA6cGxhdGZvcm19LAogICAgICAgICAgeyJzb3VyY2VTaGEyNTYiLCA6c291cmNlX3NoYTI1Nn0sCiAgICAgICAgICB7InRvb2xjaGFpbkxvY2tTaGEyNTYiLCA6dG9vbGNoYWluX2xvY2tfc2hhMjU2fSwKICAgICAgICAgIHsiYnVpbGREZWZpbml0aW9uU2hhMjU2IiwgOmJ1aWxkX2RlZmluaXRpb25fc2hhMjU2fQogICAgICAgIF0sCiAgICAgICAgZG86IGFzc2VydChkdG9bd2lyZV0gPT0gc2VsZWN0ZWRba2V5XSkKCiAgICBhc3NlcnQgcmVzcG9uc2VfaGVhZGVyKHIsICJjYWNoZS1jb250cm9sIikgPT0gWyJuby1zdG9yZSJdCiAgICBhc3NlcnQgcmVzcG9uc2VfaGVhZGVyKHIsICJzZXQtY29va2llIikgPT0gW10KICAgIGFzc2VydCBbaWRdID0gcmVzcG9uc2VfaGVhZGVyKHIsICJ4LXJlcXVlc3QtaWQiKQogICAgYXNzZXJ0IGJ5dGVfc2l6ZShpZCkgPT0gMzIKCiAgICBhc3NlcnQgRi5xISgKICAgICAgICAgICAgIEFkbWluLAogICAgICAgICAgICAgIlNFTEVDVCAoU0VMRUNUIGNvdW50KCopIEZST00gcHVibGljLm9iYW5fam9icyksKFNFTEVDVCBjb3VudCgqKSBGUk9NIHB1YmxpYy5taXhlcl9idWlsZHMpIgogICAgICAgICAgICkucm93cyA9PSBiZWZvcmUKCiAgICBsZWFzZXNfY2xlYW4oKQoKICAgIEZpbGUud3JpdGUhKAogICAgICBTeXN0ZW0uZmV0Y2hfZW52ISgiUjExMDRfUE9TSVRJVkUiKSwKICAgICAgSmFzb24uZW5jb2RlISglewogICAgICAgIHF1ZXVlZDogZHRvLAogICAgICAgIHJvdGF0ZWRfY29va2llOiB0cnVlLAogICAgICAgIGFjdHVhbF9IVFRQOiB0cnVlLAogICAgICAgIG9yZGluYXJ5X3JvbGU6ICJicm93c2VyX29yZGluYXJ5IiwKICAgICAgICBkaXJlY3RfYnVpbGRfc2VsZWN0OiBmYWxzZSwKICAgICAgICBub19yZWFkX2pvYl9vcl9yb3dfaW5zZXJ0OiB0cnVlCiAgICAgIH0pCiAgICApCgogICAgSU8ucHV0cygiUjExMDRfRklSU1RfR0VOVUlORV9IVFRQX0dBVEVfUEFTUyBxdWV1ZWQgZXhhY3QgRFRPIGNvb2tpZS1vbmx5IikKICAgIGNvbXBpbGVkX2J1aWxkX3JlYWQoYywgc2VsZWN0ZWQsIGNvb2tpZSwgInF1ZXVlZCIsIGR0bykKCiAgICBbW2pvdXJuYWxdXSA9IEYucSEoQWRtaW4sICJTRUxFQ1Qgam91cm5hbCBGUk9NIHB1YmxpYy5taXhlcl9idWlsZHMiKS5yb3dzCiAgICBhc3NlcnQgezpvaywgYnVpbGR9ID0gTWl4ZXJIb3N0ZWQuQnVpbGRzLkpvdXJuYWwucmVzdG9yZShqb3VybmFsKQogICAgYXNzZXJ0IHs6b2ssIHJlZn0gPSBNaXhlckhvc3RlZC5CdWlsZHMuTGlmZWN5Y2xlLndvcmtlcl9yZWYoYnVpbGQpCgogICAgYXNzZXJ0IHs6b2ssIHJ1bm5pbmcsIF8sIDphcHBsaWVkfSA9CiAgICAgICAgICAgICBNaXhlckhvc3RlZC5CdWlsZHMuSm91cm5hbC5hcHBlbmQoam91cm5hbCwgInN0YXJ0IiwgJXt0eXBlOiA6c3RhcnQsIHJlZjogcmVmfSwgMSkKCiAgICBhc3NlcnQgezpvaywgdGVybWluYWwsIF8sIDphcHBsaWVkfSA9CiAgICAgICAgICAgICBNaXhlckhvc3RlZC5CdWlsZHMuSm91cm5hbC5hcHBlbmQoCiAgICAgICAgICAgICAgIHJ1bm5pbmcsCiAgICAgICAgICAgICAgICJmYWlsIiwKICAgICAgICAgICAgICAgJXsKICAgICAgICAgICAgICAgICB0eXBlOiA6Y29tcGxldGVkLAogICAgICAgICAgICAgICAgIHJlZjogcmVmLAogICAgICAgICAgICAgICAgIHJlc3VsdDogJXsKICAgICAgICAgICAgICAgICAgIG91dGNvbWU6IDpmYWlsZWQsCiAgICAgICAgICAgICAgICAgICBjbGFzczogOmNvbXBpbGVyLAogICAgICAgICAgICAgICAgICAgY29kZTogOmNvbXBpbGVyX2Vycm9yLAogICAgICAgICAgICAgICAgICAgZGlhZ25vc3RpY19zaGEyNTY6IFN0cmluZy5kdXBsaWNhdGUoImQiLCA2NCkKICAgICAgICAgICAgICAgICB9CiAgICAgICAgICAgICAgIH0sCiAgICAgICAgICAgICAgIDIKICAgICAgICAgICAgICkKCiAgICBGLnEhKEFkbWluLCAiVVBEQVRFIHB1YmxpYy5taXhlcl9idWlsZHMgU0VUIGpvdXJuYWw9JDEscmV2aXNpb249MiIsIFt0ZXJtaW5hbF0pCiAgICByZXN1bHQgPSBodHRwKGMsIGJ1aWxkX3BhdGgoc2VsZWN0ZWQpLCBocykKICAgIGFzc2VydCByZXN1bHQuc3RhdHVzID09IDIwMAogICAgYXNzZXJ0IEphc29uLmRlY29kZSEocmVzdWx0LmJvZHkpWyJidWlsZCJdWyJzdGF0ZSJdID09ICJmYWlsZWQiCiAgICBhc3NlcnQgSmFzb24uZGVjb2RlIShyZXN1bHQuYm9keSlbImJ1aWxkIl1bImZhaWx1cmVDb2RlIl0gPT0gImNvbXBpbGVyX2Vycm9yIgogICAgY29tcGlsZWRfYnVpbGRfcmVhZChjLCBzZWxlY3RlZCwgY29va2llLCAidGVybWluYWwiLCBKYXNvbi5kZWNvZGUhKHJlc3VsdC5ib2R5KVsiYnVpbGQiXSkKICAgIGFzc2VydCBodHRwKGMsICIvYXV0aC9zZXNzaW9uIiwgaHMpLnN0YXR1cyA9PSAyMDAKICAgIGFzc2VydCBodHRwKGMsICIvY29uc29sZS1hcGkvdjEvb3Jncz9saW1pdD0xIiwgaHMpLnN0YXR1cyA9PSAyMDAKICAgIGFzc2VydCBodHRwKGMsICIvY29uc29sZS1hcGkvdjEvcHJvamVjdHM/b3JnYW5pemF0aW9uX2lkPW9yZy1hJmxpbWl0PTEiLCBocykuc3RhdHVzID09IDIwMAoKICAgIGZvciB7a2V5LCB2YWx1ZX0gPC0gWwogICAgICAgICAgb3JnYW5pemF0aW9uX2lkOiAib3JnLWIiLAogICAgICAgICAgcHJvamVjdF9pZDogInByb2plY3QtYiIsCiAgICAgICAgICBhcHBsaWNhdGlvbl9pZDogIm90aGVyIiwKICAgICAgICAgIGJ1aWxkX2lkOiAib3RoZXIiLAogICAgICAgICAgcGxhdGZvcm06ICJhbmRyb2lkIiwKICAgICAgICAgIHNvdXJjZV9zaGEyNTY6IFN0cmluZy5kdXBsaWNhdGUoImUiLCA2NCksCiAgICAgICAgICB0b29sY2hhaW5fbG9ja19zaGEyNTY6IFN0cmluZy5kdXBsaWNhdGUoImUiLCA2NCksCiAgICAgICAgICBidWlsZF9kZWZpbml0aW9uX3NoYTI1NjogU3RyaW5nLmR1cGxpY2F0ZSgiZSIsIDY0KQogICAgICAgIF0gZG8KICAgICAgYmFkID0gaHR0cChjLCBidWlsZF9wYXRoKE1hcC5wdXQoc2VsZWN0ZWQsIGtleSwgdmFsdWUpKSwgaHMpCiAgICAgIGFzc2VydCBiYWQuc3RhdHVzIGluIFs0MDMsIDQwNF0sIGluc3BlY3Qoe2tleSwgYmFkfSkKICAgICAgcmVmdXRlIE1hcC5oYXNfa2V5PyhKYXNvbi5kZWNvZGUhKGJhZC5ib2R5KSwgImJ1aWxkIikKICAgIGVuZAoKICAgIHBhdGggPSBidWlsZF9wYXRoKHNlbGVjdGVkKQoKICAgIGZvciBiYWQgPC0gWwogICAgICAgICAgcGF0aCA8PiAiJmJ1aWxkX2lkPWJ1aWxkLWEiLAogICAgICAgICAgcGF0aCA8PiAiJmF1dGhvcml0eT10cnVlIiwKICAgICAgICAgIFN0cmluZy5yZXBsYWNlKHBhdGgsICJidWlsZF9pZD1idWlsZC1hIiwgImJ1aWxkX2lkPSVHRyIpLAogICAgICAgICAgU3RyaW5nLnJlcGxhY2UocGF0aCwgImJ1aWxkX2lkPWJ1aWxkLWEiLCAiYnVpbGRfaWQ9JTJmIiksCiAgICAgICAgICBTdHJpbmcucmVwbGFjZShwYXRoLCAiYnVpbGRfaWQ9YnVpbGQtYSIsICIlNjJ1aWxkX2lkPWJ1aWxkLWEiKQogICAgICAgIF0gZG8KICAgICAgYXNzZXJ0IGh0dHAoYywgYmFkLCBocykuc3RhdHVzID09IDQwMAogICAgZW5kCgogICAgYXNzZXJ0IGh0dHAoYywgcGF0aCwgaHMgKysgaHMpLnN0YXR1cyA9PSA0MDAKICAgIGFzc2VydCBodHRwKGMsIHBhdGgsIGhzICsrIFt7ImF1dGhvcml6YXRpb24iLCAiQmVhcmVyIGZha2UifV0pLnN0YXR1cyA9PSA0MDAKICAgIGFzc2VydCBodHRwKGMsIHBhdGgsIGhzICsrIFt7ImNvbnRlbnQtbGVuZ3RoIiwgIjEifV0sICJHRVQiLCAieCIpLnN0YXR1cyA9PSA0MDAKICAgIGFzc2VydCBodHRwKGMsIHBhdGgsIGhzLCAiUE9TVCIpLnN0YXR1cyA9PSA0MDQKCiAgICBhc3NlcnQgaHR0cChjLCAiL3YzL29yZ3Mvb3JnLWEvcHJvamVjdHMvcHJvamVjdC1hL2FwcHMvZmllbGRsb2cvYnVpbGRzL2J1aWxkLWEvaW9zIiwgaHMpLnN0YXR1cyA9PQogICAgICAgICAgICAgNDA0CgogICAgRi5xIShBZG1pbiwgIlVQREFURSBwdWJsaWMubWl4ZXJfYXV0aHpfbWVtYmVyc2hpcHMgU0VUIGFjdGl2ZT1mYWxzZSBXSEVSRSBpZD0nbWVtYmVyLWEnIikKICAgIGFzc2VydCBodHRwKGMsIHBhdGgsIGhzKS5zdGF0dXMgaW4gWzQwMywgNDA0XQogICAgRi5xIShBZG1pbiwgIlVQREFURSBwdWJsaWMubWl4ZXJfYXV0aHpfbWVtYmVyc2hpcHMgU0VUIGFjdGl2ZT10cnVlIFdIRVJFIGlkPSdtZW1iZXItYSciKQogICAgYXNzZXJ0IGh0dHAoYywgcGF0aCwgaHMpLnN0YXR1cyA9PSAyMDAKICAgIEYucSEoQWRtaW4sICJVUERBVEUgcHVibGljLm1peGVyX2F1dGh6X2NyZWRlbnRpYWxzIFNFVCBhY3RpdmU9ZmFsc2UiKQogICAgYXNzZXJ0IGh0dHAoYywgcGF0aCwgaHMpLnN0YXR1cyA9PSA1MDMKICAgIEYucSEoQWRtaW4sICJVUERBVEUgcHVibGljLm1peGVyX2F1dGh6X2NyZWRlbnRpYWxzIFNFVCBhY3RpdmU9dHJ1ZSIpCiAgICBGLnEhKEFkbWluLCAiVVBEQVRFIHB1YmxpYy5taXhlcl9hdXRoel9mYW1pbGllcyBTRVQgYWN0aXZlPWZhbHNlIikKICAgIGFzc2VydCBodHRwKGMsIHBhdGgsIGhzKS5zdGF0dXMgPT0gNTAzCiAgICBGLnEhKEFkbWluLCAiVVBEQVRFIHB1YmxpYy5taXhlcl9hdXRoel9mYW1pbGllcyBTRVQgYWN0aXZlPXRydWUiKQogICAgYXNzZXJ0IGh0dHAoYywgcGF0aCwgaHMpLnN0YXR1cyA9PSAyMDAKICAgIGxlYXNlc19jbGVhbigpCgogICAgR2VuU2VydmVyLmNhbGwoYy5wcm92aWRlciwgezptb2RlLCA6bm9fYnVpbGRfc2NvcGV9KQogICAgbmV4dCA9IGJvb3RzdHJhcF9odHRwKGMpCiAgICBzZWNvbmQgPSBiZWdpbl9odHRwKGMsIG5leHQpCiAgICBtaXNzaW5nID0gaHR0cChjLCAiL2F1dGgvY2FsbGJhY2s/IiA8PiBzZWNvbmQucXVlcnksIHNlY29uZC5oZWFkZXJzKQogICAgYXNzZXJ0IG1pc3Npbmcuc3RhdHVzID09IDMwMwogICAgbWlzc2luZ19jb29raWUgPSByZXNwb25zZV9jb29raWUobWlzc2luZykKICAgIGFzc2VydCBodHRwKGMsIHBhdGgsIGhlYWRlcnMobWlzc2luZ19jb29raWUpKS5zdGF0dXMgPT0gNDAzCiAgICBhc3NlcnQgaHR0cChjLCAiL2F1dGgvc2Vzc2lvbiIsIGhlYWRlcnMobWlzc2luZ19jb29raWUpKS5zdGF0dXMgPT0gMjAwCiAgICBHZW5TZXJ2ZXIuY2FsbChjLnByb3ZpZGVyLCB7Om1vZGUsIDpva30pCiAgICBsZWFzZXNfY2xlYW4oKQogICAgc3RvcF9zdXBlcnZpc2VkIShSdW50aW1lT3duZXIpCiAgICBhc3NlcnQgaHR0cChjLCBwYXRoLCBocykuc3RhdHVzID09IDUwMwoKICAgIHN0YXJ0X3N1cGVydmlzZWQhKAogICAgICB7UnVudGltZU93bmVyLAogICAgICAgJVJ1bnRpbWVDb25maWd7CiAgICAgICAgIG1vZGU6IDpkaXNhYmxlZCwKICAgICAgICAgYnJvd3Nlcl9jb25maWc6IG5pbCwKICAgICAgICAgY29uZmlndXJhdGlvbl9kaWdlc3Q6IG5pbCwKICAgICAgICAgbGlmZWN5Y2xlX3JlcG86IG5pbCwKICAgICAgICAgZXhwZWN0ZWRfcm9sZXM6IG5pbCwKICAgICAgICAgY3VzdG9keTogbmlsCiAgICAgICB9fQogICAgKQoKICAgIGFzc2VydCBodHRwKGMsIHBhdGgsIGhzKS5zdGF0dXMgPT0gNTAzCgogICAgRmlsZS53cml0ZSEoCiAgICAgIFN5c3RlbS5mZXRjaF9lbnYhKCJSMTEwNF9DT05UUk9MUyIpLAogICAgICBKYXNvbi5lbmNvZGUhKCV7CiAgICAgICAgdGVybWluYWw6IHRydWUsCiAgICAgICAgZWlnaHRfc2VsZWN0aW9uX3JlZnVzYWxzOiB0cnVlLAogICAgICAgIHJhd19kdXBsaWNhdGVzOiB0cnVlLAogICAgICAgIG1hbGZvcm1lZF9xdWVyeTogdHJ1ZSwKICAgICAgICBub19idWlsZF9zY29wZTogdHJ1ZSwKICAgICAgICByZXZva2VkX2NyZWRlbnRpYWw6IHRydWUsCiAgICAgICAgcmV2b2tlZF9mYW1pbHk6IHRydWUsCiAgICAgICAgcmV2b2tlZF9tZW1iZXJzaGlwOiB0cnVlLAogICAgICAgIGV4aXN0aW5nX3JlYWRzOiB0cnVlLAogICAgICAgIG1pc3NpbmdfZGlzYWJsZWRfcnVudGltZTogdHJ1ZSwKICAgICAgICBsZWFzZXNfY2xlYW46IHRydWUKICAgICAgfSkKICAgICkKICBlbmQKCiAgdGVzdCAicmF3IEhUVFAgYm9vdHN0cmFwIFBLQ0UgY2FsbGJhY2sgcm90YXRlcyBjb29raWUgdGhlbiB1bmNoYW5nZWQgY2xpZW50IHJlYWRzIiwgYyBkbwogICAgcCA9IGJvb3RzdHJhcF9odHRwKGMpCiAgICBsID0gYmVnaW5faHR0cChjLCBwKQogICAgYmVmb3JlID0gR2VuU2VydmVyLmNhbGwoYy5wcm92aWRlciwgOmNvdW50KQogICAgciA9IGh0dHAoYywgIi9hdXRoL2NhbGxiYWNrPyIgPD4gbC5xdWVyeSwgbC5oZWFkZXJzKQogICAgYXNzZXJ0IHIuc3RhdHVzID09IDMwMwogICAgYXNzZXJ0IHJlc3BvbnNlX2hlYWRlcihyLCAibG9jYXRpb24iKSA9PSBbIi93b3Jrc3BhY2UiXQogICAgYWN0aXZlX2Nvb2tpZSA9IHJlc3BvbnNlX2Nvb2tpZShyKQogICAgcmVmdXRlIGFjdGl2ZV9jb29raWUgPT0gcC5jb29raWUKICAgIGFzc2VydCBHZW5TZXJ2ZXIuY2FsbChjLnByb3ZpZGVyLCA6Y291bnQpID09IGJlZm9yZSArIDEKICAgIGFzc2VydCBodHRwKGMsICIvYXV0aC9zZXNzaW9uIiwgaGVhZGVycyhwLmNvb2tpZSkpLnN0YXR1cyA9PSA1MDMKICAgIHtfLCBfLCBleHB9ID0gZXhwaXJ5KGMsIGFjdGl2ZV9jb29raWUpCgogICAgYXNzZXJ0IEphc29uLmRlY29kZSEoaHR0cChjLCAiL2F1dGgvc2Vzc2lvbiIsIGhlYWRlcnMoYWN0aXZlX2Nvb2tpZSkpLmJvZHkpWyJzdGF0ZSJdID09CiAgICAgICAgICAgICAiYXV0aGVudGljYXRlZCIKCiAgICBmID0gUGF0aC5qb2luKFN5c3RlbS50bXBfZGlyISgpLCAiY2xpZW50Lmpzb24iKQoKICAgIEZpbGUud3JpdGUhKAogICAgICBmLAogICAgICBKYXNvbi5lbmNvZGUhKCV7CiAgICAgICAgb3JpZ2luOiAiaHR0cDovLzEyNy4wLjAuMToje2MuaHR0cF9wb3J0fSIsCiAgICAgICAgZmlyc3RDb29raWU6IFByb3RvY29sLnJhbmRvbV90b2tlbigpLAogICAgICAgIGFjdGl2ZUNvb2tpZTogYWN0aXZlX2Nvb2tpZSwKICAgICAgICBleHBpcmVzOiBleHAKICAgICAgfSkKICAgICkKCiAgICBGaWxlLmNobW9kIShmLCAwbzYwMCkKCiAgICB0cnkgZG8KICAgICAge291dCwgY29kZX0gPQogICAgICAgIFN5c3RlbS5jbWQoIm5vZGUiLCBbU3lzdGVtLmZldGNoX2VudiEoIk1JWEVSX0JST1dTRVJfUkVBRF9OT0RFX0RSSVZFUiIpLCBmXSwKICAgICAgICAgIHN0ZGVycl90b19zdGRvdXQ6IHRydWUKICAgICAgICApCgogICAgICBhc3NlcnQgY29kZSA9PSAwLCBvdXQKICAgICAgSU8ucHV0cygiUjY4Nl9DTElFTlQgIiA8PiBvdXQpCiAgICBhZnRlcgogICAgICBGaWxlLnJtIShmKQogICAgZW5kCgogICAgcmVwbGF5ID0gaHR0cChjLCAiL2F1dGgvY2FsbGJhY2s/IiA8PiBsLnF1ZXJ5LCBsLmhlYWRlcnMpCiAgICBhc3NlcnQgcmVwbGF5LnN0YXR1cyA9PSA1MDMKICAgIGFzc2VydCByZXNwb25zZV9oZWFkZXIocmVwbGF5LCAic2V0LWNvb2tpZSIpID09IFtdCiAgICBhc3NlcnQgR2VuU2VydmVyLmNhbGwoYy5wcm92aWRlciwgOmNvdW50KSA9PSBiZWZvcmUgKyAxCiAgICBsZWFzZXNfY2xlYW4oKQoKICAgIElPLnB1dHMoCiAgICAgICJSNjg2X0hUVFAgdmFsaWRfYm9vdHN0cmFwX2JlZ2luX2NhbGxiYWNrPXRydWUgY29tbWl0dGVkX2Nvb2tpZV9yb3RhdGlvbj10cnVlIHJlcGxheV9ub19jb29raWU9dHJ1ZSB1bmNoYW5nZWRfY2xpZW50PXRydWUiCiAgICApCiAgZW5kCgogIHRlc3QgInJhdyBIVFRQIGR1cGxpY2F0ZXMgYm9kaWVzIG9yaWdpbnMgYXJiaXRyYXJ5IGlucHV0cyBhbmQgYWxpYXNlcyBmYWlsIGNsb3NlZCIsIGMgZG8KICAgIHAgPSBib290c3RyYXBfaHR0cChjKQogICAgaCA9IGhlYWRlcnMocC5jb29raWUpCiAgICBocyA9IGggKysgW3sib3JpZ2luIiwgYy5jb25maWcucHVibGljX29yaWdpbn0sIHsieC1taXhlci1jc3JmIiwgcC5jc3JmfV0KICAgIGJlZm9yZSA9IEdlblNlcnZlci5jYWxsKGMucHJvdmlkZXIsIDpjb3VudCkKCiAgICBmb3IgYmFkIDwtIFsKICAgICAgICAgIGgsCiAgICAgICAgICBocyArKyBoLAogICAgICAgICAgaHMgKysgW3siT3JpZ2luIiwgYy5jb25maWcucHVibGljX29yaWdpbn1dLAogICAgICAgICAgaHMgKysgW3siWC1NaXhlci1DU1JGIiwgcC5jc3JmfV0sCiAgICAgICAgICBocyArKyBbeyJhdXRob3JpemF0aW9uIiwgIkJlYXJlciByZWZ1c2VkIn1dLAogICAgICAgICAgaCArKyBbeyJvcmlnaW4iLCAiaHR0cHM6Ly9ldmlsLmludmFsaWQifSwgeyJ4LW1peGVyLWNzcmYiLCBwLmNzcmZ9XQogICAgICAgIF0gZG8KICAgICAgciA9IGh0dHAoYywgIi9hdXRoL2xvZ2luIiwgYmFkLCAiUE9TVCIpCiAgICAgIGFzc2VydCByLnN0YXR1cyA9PSA1MDMKICAgICAgYXNzZXJ0IHJlc3BvbnNlX2hlYWRlcihyLCAic2V0LWNvb2tpZSIpID09IFtdIGFuZCByZXNwb25zZV9oZWFkZXIociwgImxvY2F0aW9uIikgPT0gW10KICAgIGVuZAoKICAgIGZvciBxdWVyeSA8LSBbCiAgICAgICAgICAiP3JlZGlyZWN0X3VyaT1odHRwczovL2V2aWwuaW52YWxpZCIsCiAgICAgICAgICAiP3RlbmFudD1vcmctYiIsCiAgICAgICAgICAiP3Rva2VuPWNhbGxlciIsCiAgICAgICAgICAiP3JldHVybl90bz0vZXZpbCIKICAgICAgICBdIGRvCiAgICAgIGFzc2VydCBodHRwKGMsICIvYXV0aC9sb2dpbiIgPD4gcXVlcnksIGhzLCAiUE9TVCIpLnN0YXR1cyA9PSA1MDMKICAgIGVuZAoKICAgIGFzc2VydCBodHRwKGMsICIvYXV0aC9sb2dpbiIsIGhzICsrIFt7ImNvbnRlbnQtbGVuZ3RoIiwgIjEifV0sICJQT1NUIiwgIngiKS5zdGF0dXMgPT0gNTAzCgogICAgZm9yIHBhdGggPC0gWyIvYXV0aC9sb2dpbi8iLCAiL2F1dGgvJTZjb2dpbiIsICIvQVVUSC9sb2dpbiIsICIvYXV0aC9sb2dvdXQiXSBkbwogICAgICBhc3NlcnQgaHR0cChjLCBwYXRoLCBocywgIlBPU1QiKS5zdGF0dXMgPT0gNDA0CiAgICBlbmQKCiAgICBsID0gYmVnaW5faHR0cChjLCBwKQogICAgc3RhdGUgPSBVUkkuZGVjb2RlX3F1ZXJ5KGwucXVlcnkpWyJzdGF0ZSJdCgogICAgZm9yIHF1ZXJ5IDwtIFsKICAgICAgICAgIGwucXVlcnkgPD4gIiZzdGF0ZT0iIDw+IHN0YXRlLAogICAgICAgICAgbC5xdWVyeSA8PiAiJmNvZGU9ZHVwbGljYXRlIiwKICAgICAgICAgIGwucXVlcnkgPD4gIiYlNzN0YXRlPSIgPD4gc3RhdGUsCiAgICAgICAgICBsLnF1ZXJ5IDw+ICImdGVuYW50PW9yZy1iIiwKICAgICAgICAgIFN0cmluZy5yZXBsYWNlKGwucXVlcnksICJzdGF0ZT0iIDw+IHN0YXRlLCAic3RhdGU9IiA8PiBQcm90b2NvbC5yYW5kb21fdG9rZW4oKSkKICAgICAgICBdIGRvCiAgICAgIHIgPSBodHRwKGMsICIvYXV0aC9jYWxsYmFjaz8iIDw+IHF1ZXJ5LCBoKQogICAgICBhc3NlcnQgci5zdGF0dXMgPT0gNTAzCiAgICAgIGFzc2VydCByZXNwb25zZV9oZWFkZXIociwgInNldC1jb29raWUiKSA9PSBbXQogICAgZW5kCgogICAgYXNzZXJ0IGh0dHAoYywgIi9hdXRoL2NhbGxiYWNrPyIgPD4gbC5xdWVyeSwgaCArKyBoKS5zdGF0dXMgPT0gNTAzCgogICAgYXNzZXJ0IGh0dHAoYywgIi9hdXRoL2NhbGxiYWNrPyIgPD4gbC5xdWVyeSwgaCArKyBbeyJjb250ZW50LWxlbmd0aCIsICIxIn1dLCAiR0VUIiwgIngiKS5zdGF0dXMgPT0KICAgICAgICAgICAgIDUwMwoKICAgIGFzc2VydCBHZW5TZXJ2ZXIuY2FsbChjLnByb3ZpZGVyLCA6Y291bnQpID09IGJlZm9yZQogICAgYXNzZXJ0IGh0dHAoYywgIi9hdXRoL2NhbGxiYWNrPyIgPD4gbC5xdWVyeSwgaCkuc3RhdHVzID09IDMwMwogICAgbGVhc2VzX2NsZWFuKCkKCiAgICBJTy5wdXRzKAogICAgICAiUjY4Nl9CT1VOREFSSUVTIGR1cGxpY2F0ZV9oZWFkZXJzX3F1ZXJ5PXRydWUgY3NyZl9vcmlnaW49dHJ1ZSBhbGlhc2VzX2NhbGxlcl9jaG9pY2VzX2JvZHlfcmVmdXNlZD10cnVlIgogICAgKQogIGVuZAoKICB0ZXN0ICJjYWxsYmFjayBjbGFpbSB0cmFuc2FjdGlvbiByb2xsYmFjayBuZXZlciBwdWJsaXNoZXMgY29va2llIiwgYyBkbwogICAgcCA9IGJvb3RzdHJhcF9odHRwKGMpCiAgICBsID0gYmVnaW5faHR0cChjLCBwKQogICAgcHJvdmlkZXJfYmVmb3JlID0gR2VuU2VydmVyLmNhbGwoYy5wcm92aWRlciwgOmNvdW50KQoKICAgIHBlbmRpbmcgPSBmbiAtPgogICAgICAle3Jvd3M6IHJvd3N9ID0KICAgICAgICBGLnEhKAogICAgICAgICAgQWRtaW4sCiAgICAgICAgICAiIiIKICAgICAgICAgIFNFTEVDVCBiLmVwb2NoLGIucmV2aXNpb24sYS5zdGF0dXMsYS5jbGFpbV9kaWdlc3QgSVMgTlVMTCxhLmNsYWltZWRfYXQgSVMgTlVMTAogICAgICAgICAgRlJPTSBwdWJsaWMubWl4ZXJfYnJvd3Nlcl9zZXNzaW9ucyBiCiAgICAgICAgICBKT0lOIHB1YmxpYy5taXhlcl9icm93c2VyX29pZGNfYXR0ZW1wdHMgYSBPTiBhLmJyb3dzZXJfaWQ9Yi5pZAogICAgICAgICAgV0hFUkUgYi5jb29raWVfZGlnZXN0PSQxCiAgICAgICAgICAiIiIsCiAgICAgICAgICBbOmNyeXB0by5oYXNoKDpzaGEyNTYsIHAuY29va2llKV0KICAgICAgICApCgogICAgICByb3dzCiAgICBlbmQKCiAgICBwZW5kaW5nX2JlZm9yZSA9IHBlbmRpbmcuKCkKICAgIGFzc2VydCBbWzIsIDIsICJwZW5kaW5nIiwgdHJ1ZSwgdHJ1ZV1dID0gcGVuZGluZ19iZWZvcmUKICAgIDpvayA9IEdlblNlcnZlci5jYWxsKGMuY29tbWl0X3Byb3h5LCB7OmFybSwgc2VsZigpfSkKICAgIHIgPSBodHRwKGMsICIvYXV0aC9jYWxsYmFjaz8iIDw+IGwucXVlcnksIGwuaGVhZGVycykKICAgIGFzc2VydF9yZWNlaXZlIHs6YWN0aXZhdGlvbl9hYm9ydGVkLCB0cnVlfSwgMTAwMAogICAgYXNzZXJ0X3JlY2VpdmUgOmFjdHVhbF9jb21taXRfcm9sbGVkX2JhY2ssIDEwMDAKICAgIGFzc2VydCByLnN0YXR1cyA9PSA1MDMKICAgIGFzc2VydCByZXNwb25zZV9oZWFkZXIociwgInNldC1jb29raWUiKSA9PSBbXSBhbmQgcmVzcG9uc2VfaGVhZGVyKHIsICJsb2NhdGlvbiIpID09IFtdCiAgICBhc3NlcnQgezpvaywgc25hcHNob3R9ID0gU3RvcmVkU25hcHNob3QuZGVjb2RlKHJhdyhwLmNvb2tpZSwgYykpCiAgICBhc3NlcnQgc25hcHNob3QuYnJvd3Nlclsic3RhdHVzIl0gPT0gInByZWF1dGgiCiAgICBhc3NlcnQgaHR0cChjLCAiL2F1dGgvc2Vzc2lvbiIsIGhlYWRlcnMocC5jb29raWUpKS5zdGF0dXMgPT0gNTAzCiAgICBhc3NlcnQgcGVuZGluZy4oKSA9PSBwZW5kaW5nX2JlZm9yZQogICAgYXNzZXJ0IEdlblNlcnZlci5jYWxsKGMucHJvdmlkZXIsIDpjb3VudCkgPT0gcHJvdmlkZXJfYmVmb3JlCiAgICByZXRyeSA9IGh0dHAoYywgIi9hdXRoL2NhbGxiYWNrPyIgPD4gbC5xdWVyeSwgbC5oZWFkZXJzKQogICAgYXNzZXJ0IHJldHJ5LnN0YXR1cyA9PSAzMDMKICAgIGFzc2VydCByZXNwb25zZV9oZWFkZXIocmV0cnksICJsb2NhdGlvbiIpID09IFsiL3dvcmtzcGFjZSJdCiAgICBhY3RpdmVfY29va2llID0gcmVzcG9uc2VfY29va2llKHJldHJ5KQoKICAgIGFzc2VydCBKYXNvbi5kZWNvZGUhKGh0dHAoYywgIi9hdXRoL3Nlc3Npb24iLCBoZWFkZXJzKGFjdGl2ZV9jb29raWUpKS5ib2R5KVsic3RhdGUiXSA9PQogICAgICAgICAgICAgImF1dGhlbnRpY2F0ZWQiCgogICAgYXNzZXJ0IEdlblNlcnZlci5jYWxsKGMucHJvdmlkZXIsIDpjb3VudCkgPT0gcHJvdmlkZXJfYmVmb3JlICsgMQogICAgcmVwbGF5ID0gaHR0cChjLCAiL2F1dGgvY2FsbGJhY2s/IiA8PiBsLnF1ZXJ5LCBsLmhlYWRlcnMpCiAgICBhc3NlcnQgcmVwbGF5LnN0YXR1cyA9PSA1MDMgYW5kIHJlc3BvbnNlX2hlYWRlcihyZXBsYXksICJzZXQtY29va2llIikgPT0gW10KICAgIGFzc2VydCBHZW5TZXJ2ZXIuY2FsbChjLnByb3ZpZGVyLCA6Y291bnQpID09IHByb3ZpZGVyX2JlZm9yZSArIDEKCiAgICBJTy5wdXRzKAogICAgICAiUjY4Nl9DT01NSVQgY2FsbGJhY2tfY2xhaW1fY29tbWl0X3JvbGxlZF9iYWNrPXRydWUgY29va2llX3dpdGhoZWxkPXRydWUgcHJlYXV0aF9yb3dfcmV0YWluZWQ9dHJ1ZSBwZW5kaW5nX3JldmlzaW9uX3JldGFpbmVkPXRydWUgemVyb19leGNoYW5nZV9iZWZvcmVfcmV0cnk9dHJ1ZSByZXRyeV9jb21taXR0ZWRfb25jZT10cnVlIGZ1cnRoZXJfcmVwbGF5X2Nsb3NlZD10cnVlIgogICAgKQoKICAgIGxlYXNlc19jbGVhbigpCiAgZW5kCgogIHRlc3QgImJhZCBzaWduZWQgbm9uY2UgYW5kIGRpc2FibGVkIG93bmVyIG5ldmVyIHB1Ymxpc2ggY2FsbGJhY2sgY29va2llcyIsIGMgZG8KICAgIHAgPSBib290c3RyYXBfaHR0cChjKQogICAgbCA9IGJlZ2luX2h0dHAoYywgcCkKICAgIEdlblNlcnZlci5jYWxsKGMucHJvdmlkZXIsIHs6bW9kZSwgOm5vbmNlfSkKICAgIHIgPSBodHRwKGMsICIvYXV0aC9jYWxsYmFjaz8iIDw+IGwucXVlcnksIGwuaGVhZGVycykKICAgIGFzc2VydCByLnN0YXR1cyA9PSA1MDMgYW5kIHJlc3BvbnNlX2hlYWRlcihyLCAic2V0LWNvb2tpZSIpID09IFtdCiAgICBzdG9wX3N1cGVydmlzZWQoUnVudGltZU93bmVyKQogICAgYXNzZXJ0IGh0dHAoYywgIi9hdXRoL3Nlc3Npb24iLCBbXSkuc3RhdHVzID09IDUwMwogICAgYXNzZXJ0IGh0dHAoYywgIi9hdXRoL2NhbGxiYWNrPyIgPD4gbC5xdWVyeSwgbC5oZWFkZXJzKS5zdGF0dXMgPT0gNTAzCiAgICBJTy5wdXRzKCJSNjg2X0ZBSUxVUkUgbm9uY2VfcmVmdXNlZD10cnVlIG93bmVyX2Fic2VuY2Vfbm9fY29va2llPXRydWUiKQogIGVuZAoKICBkZWZwIGluZGVwZW5kZW50X3N0YXRlKGNvb2tpZSkgZG8KICAgICV7cm93czogcm93c30gPQogICAgICBGLnEhKAogICAgICAgIEFkbWluLAogICAgICAgICIiIgogICAgICAgIFNFTEVDVCBiLnN0YXR1cyxiLmVwb2NoLGIucmV2aXNpb24sCiAgICAgICAgICAoU0VMRUNUIGNvdW50KCopIEZST00gcHVibGljLm1peGVyX2Jyb3dzZXJfc2Vzc2lvbnMgV0hFUkUgc3RhdHVzPSdhY3RpdmUnKSwKICAgICAgICAgIChTRUxFQ1QgY291bnQoKikgRlJPTSBwdWJsaWMubWl4ZXJfYXV0aHpfZmFtaWxpZXMpLAogICAgICAgICAgKFNFTEVDVCBjb3VudCgqKSBGUk9NIHB1YmxpYy5taXhlcl9hdXRoel9jcmVkZW50aWFscykKICAgICAgICBGUk9NIHB1YmxpYy5taXhlcl9icm93c2VyX3Nlc3Npb25zIGIgV0hFUkUgYi5jb29raWVfZGlnZXN0PSQxCiAgICAgICAgIiIiLAogICAgICAgIFs6Y3J5cHRvLmhhc2goOnNoYTI1NiwgY29va2llKV0KICAgICAgKQoKICAgIHJvd3MKICBlbmQKCiAgdGVzdCAiZmluYWwgYWN0aXZhdGlvbiBDT01NSVQgYmFycmllciB3aXRoaG9sZHMgYnl0ZXMgdW50aWwgaW5kZXBlbmRlbnRseSB2aXNpYmxlIiwgYyBkbwogICAgcCA9IGJvb3RzdHJhcF9odHRwKGMpCiAgICBsID0gYmVnaW5faHR0cChjLCBwKQogICAgOm9rID0gR2VuU2VydmVyLmNhbGwoYy5jb21taXRfcHJveHksIHs6YXJtX2FjdGl2YXRpb24sIDpiYXJyaWVyLCBzZWxmKCl9KQogICAgcGFyZW50ID0gc2VsZigpCgogICAgdGFzayA9CiAgICAgIFRhc2suYXN5bmMoZm4gLT4KICAgICAgICBodHRwKE1hcC5wdXQoYywgOndpcmVfb2JzZXJ2ZXIsIHBhcmVudCksICIvYXV0aC9jYWxsYmFjaz8iIDw+IGwucXVlcnksIGwuaGVhZGVycykKICAgICAgZW5kKQoKICAgIGFzc2VydF9yZWNlaXZlIHs6ZmluYWxfYWN0aXZhdGlvbl9jb21taXQsIGJhY2tlbmQsIDpiYXJyaWVyfSwKICAgICAgICAgICAgICAgICAgIDIwMDAsCiAgICAgICAgICAgICAgICAgICAicGhhc2UtYXdhcmUgZmluYWwgYWN0aXZhdGlvbiBDT01NSVQgbm90IG9ic2VydmVkIgoKICAgIGFzc2VydF9yZWNlaXZlIHs6YWN0aXZhdGlvbl9iYXJyaWVyLCBwcm94eV93b3JrZXIsIF5iYWNrZW5kfSwgMTAwMAoKICAgIFtbInByZWF1dGgiLCBfLCBfLCBhY3RpdmVfYmVmb3JlLCBmYW1pbGllc19iZWZvcmUsIGNyZWRlbnRpYWxzX2JlZm9yZV1dID0KICAgICAgaW5kZXBlbmRlbnRfc3RhdGUocC5jb29raWUpCgogICAgJXtyb3dzOiBbWyJicm93c2VyX2xpZmVjeWNsZSIsICJicm93c2VyX2xvZ2luX3N0b3JhZ2UiLCBmYWxzZSwgZmFsc2VdXX0gPQogICAgICBGLnEhKAogICAgICAgIEFkbWluLAogICAgICAgICJTRUxFQ1QgYS51c2VuYW1lLGEuZGF0bmFtZSxyLnJvbHN1cGVyLHIucm9sYnlwYXNzcmxzIEZST00gcGdfY2F0YWxvZy5wZ19zdGF0X2FjdGl2aXR5IGEgSk9JTiBwZ19jYXRhbG9nLnBnX3JvbGVzIHIgT04gci5yb2xuYW1lPWEudXNlbmFtZSBXSEVSRSBhLnBpZD0kMSIsCiAgICAgICAgW2JhY2tlbmRdCiAgICAgICkKCiAgICByZWZ1dGVfcmVjZWl2ZSB7Omh0dHBfYnl0ZXMsIF99LCAxMDAKICAgIHNlbmQocHJveHlfd29ya2VyLCA6cmVsZWFzZV9jb21taXQpCiAgICBhc3NlcnRfcmVjZWl2ZSB7OmNvbW1pdHRlZF9iYXJyaWVyLCByZWFkZXJ9LCAxMDAwCgogICAgJXtyb3dzOiBbW2FjdGl2ZV9hZnRlciwgZmFtaWxpZXNfYWZ0ZXIsIGNyZWRlbnRpYWxzX2FmdGVyXV19ID0KICAgICAgRi5xISgKICAgICAgICBBZG1pbiwKICAgICAgICAiU0VMRUNUIChTRUxFQ1QgY291bnQoKikgRlJPTSBwdWJsaWMubWl4ZXJfYnJvd3Nlcl9zZXNzaW9ucyBXSEVSRSBzdGF0dXM9J2FjdGl2ZScpLChTRUxFQ1QgY291bnQoKikgRlJPTSBwdWJsaWMubWl4ZXJfYXV0aHpfZmFtaWxpZXMpLChTRUxFQ1QgY291bnQoKikgRlJPTSBwdWJsaWMubWl4ZXJfYXV0aHpfY3JlZGVudGlhbHMpIgogICAgICApCgogICAgYXNzZXJ0IGFjdGl2ZV9hZnRlciA9PSBhY3RpdmVfYmVmb3JlICsgMQogICAgYXNzZXJ0IGZhbWlsaWVzX2FmdGVyID09IGZhbWlsaWVzX2JlZm9yZSArIDEgYW5kIGNyZWRlbnRpYWxzX2FmdGVyID09IGNyZWRlbnRpYWxzX2JlZm9yZSArIDEKICAgIGFzc2VydCBpbmRlcGVuZGVudF9zdGF0ZShwLmNvb2tpZSkgPT0gW10KICAgIHJlZnV0ZV9yZWNlaXZlIHs6aHR0cF9ieXRlcywgX30sIDEwMAogICAgc2VuZChyZWFkZXIsIDpyZWxlYXNlX2FjaykKICAgIHIgPSBUYXNrLmF3YWl0KHRhc2ssIDIwMDApCiAgICBhc3NlcnQgci5zdGF0dXMgPT0gMzAzCiAgICBjb29raWUgPSByZXNwb25zZV9jb29raWUocikKICAgIGFzc2VydCByZXNwb25zZV9oZWFkZXIociwgImxvY2F0aW9uIikgPT0gWyIvd29ya3NwYWNlIl0KCiAgICBhc3NlcnQgSmFzb24uZGVjb2RlIShodHRwKGMsICIvYXV0aC9zZXNzaW9uIiwgaGVhZGVycyhjb29raWUpKS5ib2R5KVsic3RhdGUiXSA9PQogICAgICAgICAgICAgImF1dGhlbnRpY2F0ZWQiCgogICAgRmlsZS53cml0ZSEoCiAgICAgIFN5c3RlbS5mZXRjaF9lbnYhKCJSOTMyX0JBUlJJRVJfRVZJREVOQ0UiKSwKICAgICAgSmFzb24uZW5jb2RlISglewogICAgICAgIHBoYXNlOgogICAgICAgICAgIm1peGVyX2Jyb3dzZXJfYWN0aXZhdGUgRXhlY3V0ZSArIFNFTEVDVCAxIENvbW1hbmRDb21wbGV0ZSB0aGVuIHNhbWUtY29ubmVjdGlvbiBDT01NSVQiLAogICAgICAgIGJhY2tlbmQ6IGJhY2tlbmQsCiAgICAgICAgcm9sZTogImJyb3dzZXJfbGlmZWN5Y2xlIiwKICAgICAgICBzdXBlcnVzZXI6IGZhbHNlLAogICAgICAgIGJ5cGFzc3JsczogZmFsc2UsCiAgICAgICAgbm9fYnl0ZXNfYmVmb3JlX2NvbW1pdDogdHJ1ZSwKICAgICAgICBub19ieXRlc19iZWZvcmVfYWNrOiB0cnVlLAogICAgICAgIGluZGVwZW5kZW50bHlfdmlzaWJsZV9iZWZvcmVfYWNrOiB0cnVlLAogICAgICAgIHRydXRoZnVsX2Nvb2tpZV9hbmRfcmVhZF9hZnRlcl9hY2s6IHRydWUKICAgICAgfSkKICAgICkKCiAgICBsZWFzZXNfY2xlYW4oKQogIGVuZAoKICB0ZXN0ICJmaW5hbCBhY3RpdmF0aW9uIGFjdHVhbCBDT01NSVQgcm9sbGJhY2sgbXVzdCBuZXZlciBwdWJsaXNoIGFjdGl2YXRpb24iLCBjIGRvCiAgICBwID0gYm9vdHN0cmFwX2h0dHAoYykKICAgIGwgPSBiZWdpbl9odHRwKGMsIHApCiAgICBiZWZvcmUgPSBpbmRlcGVuZGVudF9zdGF0ZShwLmNvb2tpZSkKICAgIDpvayA9IEdlblNlcnZlci5jYWxsKGMuY29tbWl0X3Byb3h5LCB7OmFybV9hY3RpdmF0aW9uLCA6YWJvcnQsIHNlbGYoKX0pCiAgICByID0gaHR0cChjLCAiL2F1dGgvY2FsbGJhY2s/IiA8PiBsLnF1ZXJ5LCBsLmhlYWRlcnMpCiAgICBhc3NlcnRfcmVjZWl2ZSB7OmZpbmFsX2FjdGl2YXRpb25fY29tbWl0LCBiYWNrZW5kLCA6YWJvcnR9LCAxMDAwCiAgICBhc3NlcnRfcmVjZWl2ZSB7OmFjdGl2YXRpb25fYWJvcnRlZCwgdHJ1ZX0sIDEwMDAKICAgIGFzc2VydF9yZWNlaXZlIDphY3R1YWxfY29tbWl0X3JvbGxlZF9iYWNrLCAxMDAwCiAgICBhZnRlcl9zdGF0ZSA9IGluZGVwZW5kZW50X3N0YXRlKHAuY29va2llKQoKICAgICV7cm93czogaWRlbnRpdHl9ID0KICAgICAgRi5xISgKICAgICAgICBBZG1pbiwKICAgICAgICAiU0VMRUNUIGEudXNlbmFtZSxhLmRhdG5hbWUsci5yb2xzdXBlcixyLnJvbGJ5cGFzc3JscyBGUk9NIHBnX2NhdGFsb2cucGdfc3RhdF9hY3Rpdml0eSBhIEpPSU4gcGdfY2F0YWxvZy5wZ19yb2xlcyByIE9OIHIucm9sbmFtZT1hLnVzZW5hbWUgV0hFUkUgYS5waWQ9JDEiLAogICAgICAgIFtiYWNrZW5kXQogICAgICApCgogICAgY29va2llcyA9IHJlc3BvbnNlX2hlYWRlcihyLCAic2V0LWNvb2tpZSIpCgogICAgcmVhZCA9CiAgICAgIGlmIGNvb2tpZXMgPT0gW10sCiAgICAgICAgZG86IG5pbCwKICAgICAgICBlbHNlOiBodHRwKGMsICIvYXV0aC9zZXNzaW9uIiwgaGVhZGVycyhyZXNwb25zZV9jb29raWUocikpKS5zdGF0dXMKCiAgICBldmlkZW5jZSA9ICV7CiAgICAgIHBoYXNlOgogICAgICAgICJtaXhlcl9icm93c2VyX2FjdGl2YXRlIEV4ZWN1dGUgKyBTRUxFQ1QgMSBDb21tYW5kQ29tcGxldGUgdGhlbiBzYW1lLWNvbm5lY3Rpb24gQ09NTUlUIiwKICAgICAgYmFja2VuZDogYmFja2VuZCwKICAgICAgaWRlbnRpdHk6IGlkZW50aXR5LAogICAgICBpbmplY3RlZF9yZWFkeV9mb3JfcXVlcnk6ICJFIiwKICAgICAgYWN0dWFsX2NvbW1pdF9jb21tYW5kX2NvbXBsZXRlOiAiUk9MTEJBQ0siLAogICAgICBpbmRlcGVuZGVudF9iZWZvcmU6IGJlZm9yZSwKICAgICAgaW5kZXBlbmRlbnRfYWZ0ZXI6IGFmdGVyX3N0YXRlLAogICAgICBodHRwX3N0YXR1czogci5zdGF0dXMsCiAgICAgIGFjdGl2ZV9jb29raWVfaGVhZGVyOiBjb29raWVzICE9IFtdLAogICAgICB3b3Jrc3BhY2VfcmVkaXJlY3Q6IHJlc3BvbnNlX2hlYWRlcihyLCAibG9jYXRpb24iKSA9PSBbIi93b3Jrc3BhY2UiXSwKICAgICAgcHVibGlzaGVkX2Nvb2tpZV9zZXNzaW9uX3N0YXR1czogcmVhZAogICAgfQoKICAgIEZpbGUud3JpdGUhKFN5c3RlbS5mZXRjaF9lbnYhKCJSOTMyX0ZBSUxVUkVfRVZJREVOQ0UiKSwgSmFzb24uZW5jb2RlIShldmlkZW5jZSkpCiAgICBJTy5wdXRzKCJSOTMyX0ZJTkFMX0NPTU1JVCAiIDw+IEphc29uLmVuY29kZSEoZXZpZGVuY2UpKQogICAgYXNzZXJ0IGFmdGVyX3N0YXRlID09IGJlZm9yZQogICAgYXNzZXJ0IHIuc3RhdHVzID09IDUwMwogICAgYXNzZXJ0IGNvb2tpZXMgPT0gW10gYW5kIHJlc3BvbnNlX2hlYWRlcihyLCAibG9jYXRpb24iKSA9PSBbXQogICAgbGVhc2VzX2NsZWFuKCkKICBlbmQKCiAgZGVmcCBhc3NlcnRfcG9vbF9pZGxlIGRvCiAgICAle3Jvd3M6IFtbMF1dfSA9CiAgICAgIEYucSEoQWRtaW4sICIiIgogICAgICBTRUxFQ1QgY291bnQoKikgRlJPTSBwZ19jYXRhbG9nLnBnX3N0YXRfYWN0aXZpdHkKICAgICAgV0hFUkUgdXNlbmFtZT0nYnJvd3Nlcl9saWZlY3ljbGUnIEFORCBzdGF0ZSBMSUtFICdpZGxlIGluIHRyYW5zYWN0aW9uJScKICAgICAgIiIiKQoKICAgIGFzc2VydCAle3Jvd3M6IFtbMV1dfSA9IEYucSEoTGlmZWN5Y2xlUmVwbywgIlNFTEVDVCAxIikKICAgIHJlZnV0ZSBMaWZlY3ljbGVSZXBvLmluX3RyYW5zYWN0aW9uPygpCiAgICByZWZ1dGUgTGlmZWN5Y2xlUmVwby5jaGVja2VkX291dD8oKQogIGVuZAoKICB0ZXN0ICJjb25maXJtZWQgcmVjZWlwdCByZWplY3RzIG1pc3NpbmcgZHVwbGljYXRlIG1pc21hdGNoZWQgYW5kIGZhaWxlZCB0YWdzIiBkbwogICAgc3RvcmUgPSBNaXhlckhvc3RlZC5Ccm93c2VyQXV0aC5TdG9yZQogICAgZXZlbnQgPSBbOm1peGVyX2hvc3RlZCwgOmJyb3dzZXJfYXV0aCwgOnN0b3JlLCA6dHJhbnNhY3Rpb25dCiAgICBrZXkgPSB7c3RvcmUsIDpyZWNlaXB0fQogICAgcmVmZXJlbmNlID0gbWFrZV9yZWYoKQoKICAgIG1ldGFkYXRhID0gZm4gcXVlcnksIGNvbW1hbmQsIGJhY2tlbmQgLT4KICAgICAgJXsKICAgICAgICB0eXBlOiA6ZWN0b19zcWxfcXVlcnksCiAgICAgICAgcmVwbzogTGlmZWN5Y2xlUmVwbywKICAgICAgICBvcHRpb25zOiBbc3RvcmVfdHJhbnNhY3Rpb246IHtzZWxmKCksIHJlZmVyZW5jZX1dLAogICAgICAgIHF1ZXJ5OiBxdWVyeSwKICAgICAgICByZXN1bHQ6IHs6b2ssICVQb3N0Z3JleC5SZXN1bHR7Y29tbWFuZDogY29tbWFuZCwgY29ubmVjdGlvbl9pZDogYmFja2VuZH19CiAgICAgIH0KICAgIGVuZAoKICAgIG9ic2VydmUgPSBmbiB2YWx1ZSAtPiBzdG9yZS50cmFuc2FjdGlvbl9ldmVudChldmVudCwgJXt9LCB2YWx1ZSwgbmlsKSBlbmQKICAgIHJlc2V0ID0gZm4gLT4gUHJvY2Vzcy5wdXQoa2V5LCB7c2VsZigpLCByZWZlcmVuY2UsIDphd2FpdF9iZWdpbn0pIGVuZAoKICAgIHRyeSBkbwogICAgICByZXNldC4oKQogICAgICBvYnNlcnZlLihtZXRhZGF0YS4oImNvbW1pdCIsIDpjb21taXQsIDEpKQogICAgICBhc3NlcnQgZWxlbShQcm9jZXNzLmdldChrZXkpLCAyKSA9PSA6dW5rbm93bgogICAgICByZXNldC4oKQogICAgICBvYnNlcnZlLihtZXRhZGF0YS4oImJlZ2luIiwgOmJlZ2luLCAxKSkKICAgICAgb2JzZXJ2ZS4obWV0YWRhdGEuKCJjb21taXQiLCA6Y29tbWl0LCAyKSkKICAgICAgYXNzZXJ0IGVsZW0oUHJvY2Vzcy5nZXQoa2V5KSwgMikgPT0gOnVua25vd24KICAgICAgcmVzZXQuKCkKICAgICAgb2JzZXJ2ZS4obWV0YWRhdGEuKCJiZWdpbiIsIDpiZWdpbiwgMSkpCiAgICAgIG9ic2VydmUuKG1ldGFkYXRhLigiY29tbWl0IiwgOmNvbW1pdCwgMSkpCiAgICAgIGFzc2VydCBlbGVtKFByb2Nlc3MuZ2V0KGtleSksIDIpID09IDpjb21taXR0ZWQKICAgICAgb2JzZXJ2ZS4obWV0YWRhdGEuKCJjb21taXQiLCA6Y29tbWl0LCAxKSkKICAgICAgYXNzZXJ0IGVsZW0oUHJvY2Vzcy5nZXQoa2V5KSwgMikgPT0gOnVua25vd24KICAgICAgcmVzZXQuKCkKICAgICAgb2JzZXJ2ZS4obWV0YWRhdGEuKCJiZWdpbiIsIDpiZWdpbiwgMSkpCiAgICAgIG9ic2VydmUuKG1ldGFkYXRhLigiY29tbWl0IiwgOnJvbGxiYWNrLCAxKSkKICAgICAgYXNzZXJ0IGVsZW0oUHJvY2Vzcy5nZXQoa2V5KSwgMikgPT0gOnJvbGxlZF9iYWNrCiAgICAgIHJlc2V0LigpCiAgICAgIG9ic2VydmUuKG1ldGFkYXRhLigiYmVnaW4iLCA6YmVnaW4sIDEpKQoKICAgICAgb2JzZXJ2ZS4oCiAgICAgICAgTWFwLnB1dCgKICAgICAgICAgIG1ldGFkYXRhLigiY29tbWl0IiwgOmNvbW1pdCwgMSksCiAgICAgICAgICA6cmVzdWx0LAogICAgICAgICAgezplcnJvciwgJURCQ29ubmVjdGlvbi5Db25uZWN0aW9uRXJyb3J7bWVzc2FnZTogImZpeHR1cmUifX0KICAgICAgICApCiAgICAgICkKCiAgICAgIGFzc2VydCBlbGVtKFByb2Nlc3MuZ2V0KGtleSksIDIpID09IDp1bmtub3duCgogICAgICBmb3Igb3B0aW9ucyA8LSBbCiAgICAgICAgICAgIFtzdG9yZV90cmFuc2FjdGlvbjoge3NlbGYoKSwgbWFrZV9yZWYoKX1dLAogICAgICAgICAgICBbc3RvcmVfdHJhbnNhY3Rpb246IHtQcm9jZXNzLndoZXJlaXMoUnVudGltZU93bmVyKSwgcmVmZXJlbmNlfV0sCiAgICAgICAgICAgIFtdCiAgICAgICAgICBdIGRvCiAgICAgICAgcmVzZXQuKCkKICAgICAgICBvYnNlcnZlLihtZXRhZGF0YS4oImJlZ2luIiwgOmJlZ2luLCAxKSkKICAgICAgICBvYnNlcnZlLihNYXAucHV0KG1ldGFkYXRhLigiY29tbWl0IiwgOmNvbW1pdCwgMSksIDpvcHRpb25zLCBvcHRpb25zKSkKICAgICAgICBhc3NlcnQgZWxlbShQcm9jZXNzLmdldChrZXkpLCAyKSA9PSA6dW5rbm93bgogICAgICBlbmQKICAgIGFmdGVyCiAgICAgIFByb2Nlc3MuZGVsZXRlKGtleSkKICAgIGVuZAoKICAgIGFzc2VydCBQcm9jZXNzLmdldChrZXkpID09IG5pbAogIGVuZAoKICB0ZXN0ICJtaXNzaW5nIGFjdHVhbCBTdG9yZSByZWNlaXB0IHdpdGhob2xkcyBIVFRQIGNvb2tpZSBhbmQgaGFuZGxlciByZWdpc3RyYXRpb24gaXMgYm91bmRlZCIsCiAgICAgICBjIGRvCiAgICBzdG9yZSA9IE1peGVySG9zdGVkLkJyb3dzZXJBdXRoLlN0b3JlCiAgICBldmVudCA9IFs6bWl4ZXJfaG9zdGVkLCA6YnJvd3Nlcl9hdXRoLCA6c3RvcmUsIDp0cmFuc2FjdGlvbl0KICAgIGhhbmRsZXIgPSB7c3RvcmUsIDp0cmFuc2FjdGlvbl9yZWNlaXB0fQogICAgZmF1bHQgPSB7X19NT0RVTEVfXywgOm1pc3NpbmdfcmVjZWlwdH0KICAgIG9yaWdpbmFsX3N0YXR1cyA9IFJ1bnRpbWVPd25lci5zdGF0dXMoKQogICAgOm9rID0gOnRlbGVtZXRyeS5hdHRhY2goZmF1bHQsIGV2ZW50LCAmUjk0Mi5SZWNlaXB0RmF1bHQuaGFuZGxlLzQsIDptaXNzaW5nKQoKICAgIHRyeSBkbwogICAgICByID0gaHR0cChjLCAiL2F1dGgvc2Vzc2lvbiIsIFtdKQogICAgICBhc3NlcnQgci5zdGF0dXMgPT0gNTAzCiAgICAgIGFzc2VydCByZXNwb25zZV9oZWFkZXIociwgInNldC1jb29raWUiKSA9PSBbXSBhbmQgcmVzcG9uc2VfaGVhZGVyKHIsICJsb2NhdGlvbiIpID09IFtdCiAgICBhZnRlcgogICAgICA6dGVsZW1ldHJ5LmRldGFjaChmYXVsdCkKICAgIGVuZAoKICAgIGFzc2VydCAle3BoYXNlOiA6dW5hdmFpbGFibGUsIGdlbmVyYXRpb246IGdlbmVyYXRpb259ID0gUnVudGltZU93bmVyLnN0YXR1cygpCiAgICBhc3NlcnQgZ2VuZXJhdGlvbiA9PSBvcmlnaW5hbF9zdGF0dXMuZ2VuZXJhdGlvbiArIDEKICAgIHIgPSBodHRwKGMsICIvYXV0aC9zZXNzaW9uIiwgW10pCiAgICBhc3NlcnQgci5zdGF0dXMgPT0gNTAzCiAgICBhc3NlcnQgcmVzcG9uc2VfaGVhZGVyKHIsICJzZXQtY29va2llIikgPT0gW10gYW5kIHJlc3BvbnNlX2hlYWRlcihyLCAibG9jYXRpb24iKSA9PSBbXQogICAgIyBFeHBsaWNpdGx5IHJlc3RvcmUgb25seSB0aGUgaGFuZGxlciByZW1vdmVkIGJ5IHRoZSBmaXh0dXJlOyB0aGUgb3duZXIgc3RheXMgdW5hdmFpbGFibGUuCiAgICBhc3NlcnQgOm9rID0KICAgICAgICAgICAgIDp0ZWxlbWV0cnkuYXR0YWNoKAogICAgICAgICAgICAgICBoYW5kbGVyLAogICAgICAgICAgICAgICBldmVudCwKICAgICAgICAgICAgICAgJk1peGVySG9zdGVkLkJyb3dzZXJBdXRoLlN0b3JlLnRyYW5zYWN0aW9uX2V2ZW50LzQsCiAgICAgICAgICAgICAgIG5pbAogICAgICAgICAgICAgKQoKICAgIGFzc2VydCBSdW50aW1lT3duZXIuc3RhdHVzKCkgPT0gJXtwaGFzZTogOnVuYXZhaWxhYmxlLCBnZW5lcmF0aW9uOiBnZW5lcmF0aW9ufQogICAgbWF0Y2hpbmcgPSBFbnVtLmZpbHRlcig6dGVsZW1ldHJ5Lmxpc3RfaGFuZGxlcnMoZXZlbnQpLCAmKCYxLmlkID09IGhhbmRsZXIpKQogICAgYXNzZXJ0IFsle2NvbmZpZzogbmlsLCBmdW5jdGlvbjogZnVufV0gPSBtYXRjaGluZwogICAgYXNzZXJ0IGZ1biA9PSAoJk1peGVySG9zdGVkLkJyb3dzZXJBdXRoLlN0b3JlLnRyYW5zYWN0aW9uX2V2ZW50LzQpCiAgICBhc3NlcnRfcG9vbF9pZGxlKCkKICAgIGxlYXNlc19jbGVhbigpCiAgZW5kCgogIHRlc3QgInBpbm5lZCB0cmFuc2FjdGlvbiBleHBsaWNpdCByb2xsYmFjayBTUUwgZXhjZXB0aW9uIGFuZCBuZXN0ZWQgYWRtaXNzaW9uIHJlbGVhc2UgY2hlY2tvdXQiLAogICAgICAgYyBkbwogICAgc3RvcmUgPSBNaXhlckhvc3RlZC5Ccm93c2VyQXV0aC5TdG9yZQoKICAgIGFzc2VydCB7OmVycm9yLCA6Zml4dHVyZX0gPQogICAgICAgICAgICAgTGlmZWN5Y2xlUmVwby50cmFuc2FjdGlvbihmbiAtPiBMaWZlY3ljbGVSZXBvLnJvbGxiYWNrKDpmaXh0dXJlKSBlbmQsIGxvZzogZmFsc2UpCgogICAgYXNzZXJ0X3JhaXNlIFBvc3RncmV4LkVycm9yLCBmbiAtPgogICAgICBMaWZlY3ljbGVSZXBvLnRyYW5zYWN0aW9uKGZuIC0+IEYucSEoTGlmZWN5Y2xlUmVwbywgIlNFTEVDVCAxLzAiKSBlbmQsIGxvZzogZmFsc2UpCiAgICBlbmQKCiAgICBhc3NlcnRfcG9vbF9pZGxlKCkKICAgIHBhcmVudCA9IHNlbGYoKQogICAgbWFya2VyID0gbWFrZV9yZWYoKQoKICAgIDpzeXMucmVwbGFjZV9zdGF0ZShSdW50aW1lT3duZXIsIGZuIHN0YXRlIC0+CiAgICAgIHJlc3VsdCA9CiAgICAgICAgTGlmZWN5Y2xlUmVwby50cmFuc2FjdGlvbigKICAgICAgICAgIGZuIC0+CiAgICAgICAgICAgIHN0b3JlLmFkbWl0KGMucnVudGltZSwgU3lzdGVtLm1vbm90b25pY190aW1lKDptaWxsaXNlY29uZCkgKyA1MDAwKQogICAgICAgICAgZW5kLAogICAgICAgICAgbG9nOiBmYWxzZQogICAgICAgICkKCiAgICAgIHNlbmQocGFyZW50LCB7bWFya2VyLCByZXN1bHQsIFByb2Nlc3MuZ2V0KHtzdG9yZSwgOnJlY2VpcHR9KX0pCiAgICAgIHN0YXRlCiAgICBlbmQpCgogICAgYXNzZXJ0X3JlY2VpdmUge15tYXJrZXIsCiAgICAgICAgICAgICAgICAgICAgezpvaywKICAgICAgICAgICAgICAgICAgICAgezplcnJvciwgJU1peGVySG9zdGVkLkJyb3dzZXJBdXRoLlN0b3JlLkZhaWx1cmV7b3V0Y29tZTogOm5vdF9zdGFydGVkfX19LAogICAgICAgICAgICAgICAgICAgIG5pbH0KCiAgICAjIFRoZSBvcmRpbmFyeSBkZWZhdWx0IGlzIHN0aWxsIHByZWF1dGhlbnRpY2F0aW9uOyBpdCBjYW5ub3QgcmVhY2ggd29ya3NwYWNlLgogICAgcCA9IGJvb3RzdHJhcF9odHRwKGMpCgogICAgYXNzZXJ0IEphc29uLmRlY29kZSEoaHR0cChjLCAiL2F1dGgvc2Vzc2lvbiIsIGhlYWRlcnMocC5jb29raWUpKS5ib2R5KVsic3RhdGUiXSA9PQogICAgICAgICAgICAgInVuYXV0aGVudGljYXRlZCIKCiAgICBhc3NlcnRfcG9vbF9pZGxlKCkKICAgIGxlYXNlc19jbGVhbigpCiAgZW5kCgogIHRlc3QgImFjdHVhbCB0cmFuc3BvcnQgbG9zcyBiZWZvcmUgZmluYWwgQ09NTUlUIHdpdGhob2xkcyBhY3RpdmF0aW9uIGFuZCBsZWF2ZXMgbm8gbGl2ZSB0cmFuc2FjdGlvbiIsCiAgICAgICBjIGRvCiAgICBwID0gYm9vdHN0cmFwX2h0dHAoYykKICAgIGwgPSBiZWdpbl9odHRwKGMsIHApCiAgICBiZWZvcmUgPSBpbmRlcGVuZGVudF9zdGF0ZShwLmNvb2tpZSkKICAgIDpvayA9IEdlblNlcnZlci5jYWxsKGMuY29tbWl0X3Byb3h5LCB7OmFybV9hY3RpdmF0aW9uLCA6YmFycmllciwgc2VsZigpfSkKICAgIHRhc2sgPSBUYXNrLmFzeW5jKGZuIC0+IGh0dHAoYywgIi9hdXRoL2NhbGxiYWNrPyIgPD4gbC5xdWVyeSwgbC5oZWFkZXJzKSBlbmQpCiAgICBhc3NlcnRfcmVjZWl2ZSB7OmZpbmFsX2FjdGl2YXRpb25fY29tbWl0LCBiYWNrZW5kLCA6YmFycmllcn0sIDIwMDAKICAgIGFzc2VydF9yZWNlaXZlIHs6YWN0aXZhdGlvbl9iYXJyaWVyLCB3b3JrZXIsIF5iYWNrZW5kfSwgMTAwMAoKICAgIGFzc2VydCAle3Jvd3M6IFtbdHJ1ZV1dfSA9CiAgICAgICAgICAgICBGLnEhKEFkbWluLCAiU0VMRUNUIHBnX2NhdGFsb2cucGdfdGVybWluYXRlX2JhY2tlbmQoJDEpIiwgW2JhY2tlbmRdKQoKICAgIHNlbmQod29ya2VyLCA6cmVsZWFzZV9jb21taXQpCiAgICByID0gVGFzay5hd2FpdCh0YXNrLCAzMDAwKQogICAgYXNzZXJ0IHIuc3RhdHVzID09IDUwMwogICAgYXNzZXJ0IHJlc3BvbnNlX2hlYWRlcihyLCAic2V0LWNvb2tpZSIpID09IFtdIGFuZCByZXNwb25zZV9oZWFkZXIociwgImxvY2F0aW9uIikgPT0gW10KICAgIGFzc2VydCBpbmRlcGVuZGVudF9zdGF0ZShwLmNvb2tpZSkgPT0gYmVmb3JlCiAgICBhc3NlcnRfcG9vbF9pZGxlKCkKICAgIGxlYXNlc19jbGVhbigpCgogICAgSU8ucHV0cygKICAgICAgIlI5NDJfVFJBTlNQT1JUIGFjdHVhbF90ZXJtaW5hdGVkX2ZpbmFsX2JhY2tlbmQ9dHJ1ZSBub19jb29raWU9dHJ1ZSByb3dzX3VuY2hhbmdlZD10cnVlIHBvb2xfcmV1c2FibGU9dHJ1ZSIKICAgICkKICBlbmQKZW5kCg==","hosted/test/mixer_hosted/identity/startup_config_test.exs":"ZGVmbW9kdWxlIE1peGVySG9zdGVkLklkZW50aXR5LlN0YXJ0dXBDb25maWdUZXN0IGRvCiAgdXNlIEV4VW5pdC5DYXNlLCBhc3luYzogdHJ1ZQogIGFsaWFzIE1peGVySG9zdGVkLklkZW50aXR5LntTdGFydHVwQ29uZmlnLCBTdGFydHVwRml4dHVyZX0KCiAgc2V0dXBfYWxsIGRvCiAgICB7Om9rLCByb290czogU3RhcnR1cEZpeHR1cmUuc3RhbmRhcmRfcm9vdHMoKX0KICBlbmQKCiAgZGVmcCByZWplY3QocmF3LCByb290cywgY2F0ZWdvcnkgXFwgImNvbmZpZ3VyYXRpb24iKSBkbwogICAgYXNzZXJ0X3JhaXNlIEFyZ3VtZW50RXJyb3IsICJpbnZhbGlkIGlkZW50aXR5IHN0YXJ0dXA6ICIgPD4gY2F0ZWdvcnksIGZuIC0+CiAgICAgIFN0YXJ0dXBDb25maWcubG9hZCEoCiAgICAgICAgJXsiTUlYRVJfSURFTlRJVFlfTU9ERSIgPT4gImNvbmZpZ3VyZWQiLCAiTUlYRVJfSURFTlRJVFlfQ09ORklHIiA9PiByYXd9LAogICAgICAgIDphcGksCiAgICAgICAgcm9vdHMKICAgICAgKQogICAgZW5kCiAgZW5kCgogIHRlc3QgIklTMDEgZXhwbGljaXQgZGlzYWJsZWQgZGVmYXVsdCwgcm9sZSBzZXBhcmF0aW9uIGFuZCBzdHJheSBjb25maWd1cmF0aW9uIiwgJXtyb290czogcm9vdHN9IGRvCiAgICBmb3Igcm9sZSA8LSBbOmFwaSwgOnByb2Nlc3Nvcl0sIGVudiA8LSBbJXt9LCAleyJNSVhFUl9JREVOVElUWV9NT0RFIiA9PiAiZGlzYWJsZWQifV0gZG8KICAgICAgYXNzZXJ0ICVTdGFydHVwQ29uZmlne21vZGU6IDpkaXNhYmxlZCwgb3duZXJfb3B0aW9uczogW119ID0KICAgICAgICAgICAgICAgU3RhcnR1cENvbmZpZy5sb2FkIShlbnYsIHJvbGUsIFtdKQogICAgZW5kCgogICAgZm9yIHJvbGUgPC0gWzphcGksIDpwcm9jZXNzb3JdLCBtb2RlIDwtIFtuaWwsICJkaXNhYmxlZCJdIGRvCiAgICAgIGVudiA9ICV7Ik1JWEVSX0lERU5USVRZX0NPTkZJRyIgPT4gInNlbnNpdGl2ZS1wYXlsb2FkIn0KICAgICAgZW52ID0gaWYgbW9kZSwgZG86IE1hcC5wdXQoZW52LCAiTUlYRVJfSURFTlRJVFlfTU9ERSIsIG1vZGUpLCBlbHNlOiBlbnYKCiAgICAgIGFzc2VydF9yYWlzZSBBcmd1bWVudEVycm9yLCAiaW52YWxpZCBpZGVudGl0eSBzdGFydHVwOiB1bmV4cGVjdGVkX2NvbmZpZ3VyYXRpb24iLCBmbiAtPgogICAgICAgIFN0YXJ0dXBDb25maWcubG9hZCEoZW52LCByb2xlLCByb290cykKICAgICAgZW5kCiAgICBlbmQKCiAgICBmb3IgbW9kZSA8LSBbbmlsLCAiIiwgIkNvbmZpZ3VyZWQiLCA6Y29uZmlndXJlZCwgMV0gZG8KICAgICAgYXNzZXJ0X3JhaXNlIEFyZ3VtZW50RXJyb3IsICJpbnZhbGlkIGlkZW50aXR5IHN0YXJ0dXA6IG1vZGUiLCBmbiAtPgogICAgICAgIFN0YXJ0dXBDb25maWcubG9hZCEoJXsiTUlYRVJfSURFTlRJVFlfTU9ERSIgPT4gbW9kZX0sIDphcGksIHJvb3RzKQogICAgICBlbmQKICAgIGVuZAoKICAgIGFzc2VydF9yYWlzZSBBcmd1bWVudEVycm9yLCAiaW52YWxpZCBpZGVudGl0eSBzdGFydHVwOiByb2xlIiwgZm4gLT4KICAgICAgU3RhcnR1cENvbmZpZy5sb2FkISgleyJNSVhFUl9JREVOVElUWV9NT0RFIiA9PiAiY29uZmlndXJlZCJ9LCA6cHJvY2Vzc29yLCByb290cykKICAgIGVuZAoKICAgIHNldHRpbmdzID0gTWl4ZXJIb3N0ZWQuUnVudGltZUNvbmZpZy5sb2FkIShTdGFydHVwRml4dHVyZS5mb3VuZGF0aW9uX2VudigpKQogICAgYXNzZXJ0IHNldHRpbmdzLmlkZW50aXR5X3N0YXJ0dXAubW9kZSA9PSA6ZGlzYWJsZWQKCiAgICBmb3Igcm9sZSA8LSBbOmFwaSwgOnByb2Nlc3Nvcl0gZG8KICAgICAgcmVmdXRlIEVudW0uYW55PyhNaXhlckhvc3RlZC5BcHBsaWNhdGlvbi5jaGlsZHJlbihyb2xlLCBzZXR0aW5ncy5vYmFuKSwgZm4KICAgICAgICAgICAgICAge01peGVySG9zdGVkLklkZW50aXR5LktleU93bmVyU3VwZXJ2aXNvciwgX30gLT4gdHJ1ZQogICAgICAgICAgICAgICBfIC0+IGZhbHNlCiAgICAgICAgICAgICBlbmQpCiAgICBlbmQKICBlbmQKCiAgdGVzdCAiSVMwMiBleGFjdCBjb252ZXJzaW9uIGJvdGggaWRlbnRpdHkgY2xhc3NlcywgYm91bmRhcmllcyBhbmQgcmVkYWN0ZWQgSW5zcGVjdCIsICV7CiAgICByb290czogcm9vdHMKICB9IGRvCiAgICBmb3IgY291bnQgPC0gWzEsIDhdLAogICAgICAgIGNsYXNzIDwtIFsiaHVtYW4iLCAic2VydmljZSJdLAogICAgICAgIGVuYWJsZWQgPC0gW3RydWUsIGZhbHNlXSwKICAgICAgICByZXNvbHZlcnMgPC0gW1siMTI3LjAuMC4xIl0sIFsiOC44LjguOCIsICIyMDAxOjQ4NjA6NDg2MDo6ODg4OCIsICI6OjEiXV0gZG8KICAgICAgZW50cmllcyA9CiAgICAgICAgZm9yIG4gPC0gMS4uY291bnQgZG8KICAgICAgICAgIFN0YXJ0dXBGaXh0dXJlLmVudHJ5KCkKICAgICAgICAgIHw+IHB1dF9pbihbInByb2ZpbGUiLCAicHJvZmlsZV9pZCJdLCAic2Vuc2l0aXZlLXByb2ZpbGUtI3tufSIpCiAgICAgICAgICB8PiBwdXRfaW4oWyJwcm9maWxlIiwgImlkZW50aXR5X2NsYXNzIl0sIGNsYXNzKQogICAgICAgICAgfD4gcHV0X2luKFsicHJvZmlsZSIsICJlbmFibGVkIl0sIGVuYWJsZWQpCiAgICAgICAgZW5kCgogICAgICBvYmplY3QgPQogICAgICAgIFN0YXJ0dXBGaXh0dXJlLmVudmVsb3BlKCkKICAgICAgICB8PiBNYXAubWVyZ2UoJXsKICAgICAgICAgICJnZW5lcmF0aW9uIiA9PiAyXzE0N180ODNfNjQ3LAogICAgICAgICAgImJpbmRpbmciID0+ICJzZW5zaXRpdmUtcHJvZmlsZS0xIiwKICAgICAgICAgICJwcm9maWxlcyIgPT4gZW50cmllcywKICAgICAgICAgICJyZXNvbHZlcnMiID0+IHJlc29sdmVycwogICAgICAgIH0pCgogICAgICBzZXR0aW5ncyA9IFN0YXJ0dXBGaXh0dXJlLmNvbmZpZ3VyYXRpb24ob2JqZWN0LCByb290cykKICAgICAgYXNzZXJ0IHNldHRpbmdzLm1vZGUgPT0gOmNvbmZpZ3VyZWQKICAgICAgYXNzZXJ0IHNldHRpbmdzLm93bmVyX29wdGlvbnNbOmdlbmVyYXRpb25dID09IDJfMTQ3XzQ4M182NDcKICAgICAgYXNzZXJ0IGxlbmd0aChzZXR0aW5ncy5vd25lcl9vcHRpb25zWzptYW5pZmVzdF0pID09IGNvdW50CgogICAgICBhc3NlcnQgaGQoc2V0dGluZ3Mub3duZXJfb3B0aW9uc1s6bWFuaWZlc3RdKS5wcm9maWxlLmlkZW50aXR5X2NsYXNzID09CiAgICAgICAgICAgICAgIGlmKGNsYXNzID09ICJodW1hbiIsIGRvOiA6aHVtYW4sIGVsc2U6IDpzZXJ2aWNlKQoKICAgICAgYXNzZXJ0IGhkKHNldHRpbmdzLm93bmVyX29wdGlvbnNbOm1hbmlmZXN0XSkucHJvZmlsZS5lbmFibGVkID09IGVuYWJsZWQKICAgICAgYXNzZXJ0IEVudW0uYWxsPyhzZXR0aW5ncy5vd25lcl9vcHRpb25zWzpyZXNvbHZlcnNdLCAmKGVsZW0oJjEsIDEpID09IDUzKSkKICAgICAgcmVmdXRlIGluc3BlY3Qoc2V0dGluZ3MpID1+ICJzZW5zaXRpdmUiCiAgICAgIHJlZnV0ZSBpbnNwZWN0KHNldHRpbmdzKSA9fiAiY2Ffcm9vdHMiCiAgICBlbmQKCiAgICByYXcgPSBKYXNvbi5lbmNvZGUhKFN0YXJ0dXBGaXh0dXJlLmVudmVsb3BlKCkpCgogICAgYXNzZXJ0IFN0YXJ0dXBDb25maWcubG9hZCEoCiAgICAgICAgICAgICAlewogICAgICAgICAgICAgICAiTUlYRVJfSURFTlRJVFlfTU9ERSIgPT4gImNvbmZpZ3VyZWQiLAogICAgICAgICAgICAgICAiTUlYRVJfSURFTlRJVFlfQ09ORklHIiA9PiByYXcgPD4gU3RyaW5nLmR1cGxpY2F0ZSgiICIsIDY1XzUzNiAtIGJ5dGVfc2l6ZShyYXcpKQogICAgICAgICAgICAgfSwKICAgICAgICAgICAgIDphcGksCiAgICAgICAgICAgICByb290cwogICAgICAgICAgICkubW9kZSA9PSA6Y29uZmlndXJlZAoKICAgIHJlamVjdChyYXcgPD4gU3RyaW5nLmR1cGxpY2F0ZSgiICIsIDY1XzUzNyAtIGJ5dGVfc2l6ZShyYXcpKSwgcm9vdHMpCiAgZW5kCgogIHRlc3QgIklTMDIgUnVudGltZUNvbmZpZyBiaW5kcyBjb25maWd1cmVkIHNldHRpbmdzIGZyb20gaXRzIHNpbmdsZSBPVFAgQ0Egc291cmNlIiBkbwogICAgZW52ID0KICAgICAgTWFwLm1lcmdlKFN0YXJ0dXBGaXh0dXJlLmZvdW5kYXRpb25fZW52KCksICV7CiAgICAgICAgIk1JWEVSX0lERU5USVRZX01PREUiID0+ICJjb25maWd1cmVkIiwKICAgICAgICAiTUlYRVJfSURFTlRJVFlfQ09ORklHIiA9PiBKYXNvbi5lbmNvZGUhKFN0YXJ0dXBGaXh0dXJlLmVudmVsb3BlKCkpCiAgICAgIH0pCgogICAgc2V0dGluZ3MgPSBNaXhlckhvc3RlZC5SdW50aW1lQ29uZmlnLmxvYWQhKGVudikKICAgIGFzc2VydCBzZXR0aW5ncy5pZGVudGl0eV9zdGFydHVwLm1vZGUgPT0gOmNvbmZpZ3VyZWQKICAgIGFzc2VydCBzZXR0aW5ncy5yZXBvWzpzc2xdWzpjYWNlcnRzXSA9PSA6cHVibGljX2tleS5jYWNlcnRzX2dldCgpCiAgICBhc3NlcnQgc2V0dGluZ3MuaWRlbnRpdHlfc3RhcnR1cC5vd25lcl9vcHRpb25zWzpjYV9yb290c10gPT0gU3RhcnR1cEZpeHR1cmUuc3RhbmRhcmRfcm9vdHMoKQogICAgYXNzZXJ0IEVudW0uYWxsPyhzZXR0aW5ncy5pZGVudGl0eV9zdGFydHVwLm93bmVyX29wdGlvbnNbOmNhX3Jvb3RzXSwgJmlzX2JpbmFyeS8xKQogICAgcmVmdXRlIGluc3BlY3Qoc2V0dGluZ3MpID1+ICJzdGFydHVwLWZpeHR1cmUiCiAgICByZWZ1dGUgaW5zcGVjdChzZXR0aW5ncykgPX4gInN5bnRoZXRpYyIKICBlbmQKCiAgdGVzdCAiSVMwMiBtYWxmb3JtZWQsIGR1cGxpY2F0ZSBhbmQgZXNjYXBlZCBkdXBsaWNhdGUgbWVtYmVycyBmYWlsIGNsb3NlZCIsICV7cm9vdHM6IHJvb3RzfSBkbwogICAgcmF3ID0gSmFzb24uZW5jb2RlIShTdGFydHVwRml4dHVyZS5lbnZlbG9wZSgpKQoKICAgIGZvciB2YWx1ZSA8LSBbCiAgICAgICAgICBuaWwsCiAgICAgICAgICAxLAogICAgICAgICAgIiIsCiAgICAgICAgICAiW10iLAogICAgICAgICAgIm51bGwiLAogICAgICAgICAgInsiLAogICAgICAgICAgPDwyNTU+PiwKICAgICAgICAgIFN0cmluZy5kdXBsaWNhdGUoIlsiLCAxOCkgPD4KICAgICAgICAgICAgIjAiIDw+CiAgICAgICAgICAgIFN0cmluZy5kdXBsaWNhdGUoIl0iLCAxOCksCiAgICAgICAgICBTdHJpbmcucmVwbGFjZShyYXcsICJcInZlcnNpb25cIjoxIiwgIlwidmVyc2lvblwiOjEsXCJ2ZXJzaW9uXCI6MSIpLAogICAgICAgICAgU3RyaW5nLnJlcGxhY2UocmF3LCAiXCJ2ZXJzaW9uXCI6MSIsICJcInZlcnNpb25cIjoxLFwidmVyc1xcdTAwNjlvblwiOjEiKSwKICAgICAgICAgIFN0cmluZy5yZXBsYWNlKHJhdywgIlwiZW5hYmxlZFwiOnRydWUiLCAiXCJlbmFibGVkXCI6dHJ1ZSxcImVuYWJsXFx1MDA2NWRcIjp0cnVlIikKICAgICAgICBdIGRvCiAgICAgIHJlamVjdCh2YWx1ZSwgcm9vdHMpCiAgICBlbmQKICBlbmQKCiAgdGVzdCAiSVMwMiBldmVyeSBlbnZlbG9wZS9wcm9maWxlL2VuZHBvaW50IG1lbWJlciBpcyBjb21wbGV0ZSBhbmQgY2xvc2VkIiwgJXtyb290czogcm9vdHN9IGRvCiAgICBvYmplY3QgPSBTdGFydHVwRml4dHVyZS5lbnZlbG9wZSgpCiAgICBlbnRyeSA9IFN0YXJ0dXBGaXh0dXJlLmVudHJ5KCkKICAgIHJlamVjdChKYXNvbi5lbmNvZGUhKE1hcC5wdXQob2JqZWN0LCAic2Vuc2l0aXZlLWV4dHJhIiwgInNlbnNpdGl2ZS12YWx1ZSIpKSwgcm9vdHMpCgogICAgZm9yIGtleSA8LSBNYXAua2V5cyhvYmplY3QpLCBkbzogcmVqZWN0KEphc29uLmVuY29kZSEoTWFwLmRlbGV0ZShvYmplY3QsIGtleSkpLCByb290cykKCiAgICBmb3IgcGF0aCA8LSBbCiAgICAgICAgICBbInByb2ZpbGVzIiwgQWNjZXNzLmF0KDApXSwKICAgICAgICAgIFsicHJvZmlsZXMiLCBBY2Nlc3MuYXQoMCksICJwcm9maWxlIl0sCiAgICAgICAgICBbInByb2ZpbGVzIiwgQWNjZXNzLmF0KDApLCAiandrc19lbmRwb2ludCJdCiAgICAgICAgXSBkbwogICAgICB2YWx1ZSA9IGdldF9pbihvYmplY3QsIHBhdGgpCiAgICAgIHJlamVjdChKYXNvbi5lbmNvZGUhKHB1dF9pbihvYmplY3QsIHBhdGgsIE1hcC5wdXQodmFsdWUsICJzZW5zaXRpdmUtZXh0cmEiLCB0cnVlKSkpLCByb290cykKCiAgICAgIGZvciBrZXkgPC0gTWFwLmtleXModmFsdWUpLAogICAgICAgICAgZG86IHJlamVjdChKYXNvbi5lbmNvZGUhKHB1dF9pbihvYmplY3QsIHBhdGgsIE1hcC5kZWxldGUodmFsdWUsIGtleSkpKSwgcm9vdHMpCiAgICBlbmQKCiAgICBiYWQgPSBbCiAgICAgIE1hcC5wdXQob2JqZWN0LCAidmVyc2lvbiIsIDEuMCksCiAgICAgIE1hcC5wdXQob2JqZWN0LCAidmVyc2lvbiIsIDIpLAogICAgICBNYXAucHV0KG9iamVjdCwgImdlbmVyYXRpb24iLCAxLjApLAogICAgICBNYXAucHV0KG9iamVjdCwgImdlbmVyYXRpb24iLCAwKSwKICAgICAgTWFwLnB1dChvYmplY3QsICJnZW5lcmF0aW9uIiwgMl8xNDdfNDgzXzY0OCksCiAgICAgIE1hcC5wdXQob2JqZWN0LCAiYmluZGluZyIsICJhYnNlbnQiKSwKICAgICAgTWFwLnB1dChvYmplY3QsICJiaW5kaW5nIiwgMSksCiAgICAgIE1hcC5wdXQob2JqZWN0LCAicHJvZmlsZXMiLCBbXSksCiAgICAgIE1hcC5wdXQob2JqZWN0LCAicHJvZmlsZXMiLCBbZW50cnksIGVudHJ5XSksCiAgICAgIE1hcC5wdXQob2JqZWN0LCAicHJvZmlsZXMiLCBMaXN0LmR1cGxpY2F0ZShlbnRyeSwgOSkpLAogICAgICBNYXAucHV0KG9iamVjdCwgInByb2ZpbGVzIiwgWyV7fV0pLAogICAgICBNYXAucHV0KG9iamVjdCwgInByb2ZpbGVzIiwgImJhZCIpLAogICAgICBwdXRfaW4ob2JqZWN0LCBbInByb2ZpbGVzIiwgQWNjZXNzLmF0KDApLCAidHJhbnNwb3J0Il0sICJmaXh0dXJlIiksCiAgICAgIHB1dF9pbihvYmplY3QsIFsicHJvZmlsZXMiLCBBY2Nlc3MuYXQoMCksICJwcm9maWxlIiwgImlkZW50aXR5X2NsYXNzIl0sICJhcmJpdHJhcnktYXRvbSIpLAogICAgICBwdXRfaW4ob2JqZWN0LCBbInByb2ZpbGVzIiwgQWNjZXNzLmF0KDApLCAicHJvZmlsZSIsICJlbmFibGVkIl0sICJ0cnVlIiksCiAgICAgIHB1dF9pbihvYmplY3QsIFsicHJvZmlsZXMiLCBBY2Nlc3MuYXQoMCksICJwcm9maWxlIiwgInByb2ZpbGVfdmVyc2lvbiJdLCAxLjApLAogICAgICBwdXRfaW4oCiAgICAgICAgb2JqZWN0LAogICAgICAgIFsicHJvZmlsZXMiLCBBY2Nlc3MuYXQoMCksICJwcm9maWxlIiwgImF1ZGllbmNlIl0sCiAgICAgICAgU3RyaW5nLmR1cGxpY2F0ZSgiYSIsIDI1NykKICAgICAgKSwKICAgICAgcHV0X2luKG9iamVjdCwgWyJwcm9maWxlcyIsIEFjY2Vzcy5hdCgwKSwgImp3a3NfZW5kcG9pbnQiLCAiaG9zdCJdLCAiMTI3LjAuMC4xIiksCiAgICAgIHB1dF9pbihvYmplY3QsIFsicHJvZmlsZXMiLCBBY2Nlc3MuYXQoMCksICJqd2tzX2VuZHBvaW50IiwgInBvcnQiXSwgNDQzLjApLAogICAgICBwdXRfaW4ob2JqZWN0LCBbInByb2ZpbGVzIiwgQWNjZXNzLmF0KDApLCAiandrc19lbmRwb2ludCIsICJwb3J0Il0sIDg0NDMpLAogICAgICBwdXRfaW4ob2JqZWN0LCBbInByb2ZpbGVzIiwgQWNjZXNzLmF0KDApLCAiandrc19lbmRwb2ludCIsICJwYXRoIl0sICIva2V5cz9zZWNyZXQiKSwKICAgICAgcHV0X2luKG9iamVjdCwgWyJwcm9maWxlcyIsIEFjY2Vzcy5hdCgwKSwgImp3a3NfZW5kcG9pbnQiLCAicGF0aCJdLCAiL2EvLi4va2V5cyIpCiAgICBdCgogICAgZm9yIHZhbHVlIDwtIGJhZCwgZG86IHJlamVjdChKYXNvbi5lbmNvZGUhKHZhbHVlKSwgcm9vdHMpCgogICAgZm9yIHJlc29sdmVycyA8LSBbCiAgICAgICAgICBbXSwKICAgICAgICAgIFsiOC44LjguOCIsICI4LjguOC44Il0sCiAgICAgICAgICBbIjEuMS4xLjEiLCAiOC44LjguOCIsICI6OjEiLCAiOjoyIl0sCiAgICAgICAgICBbIjguOC44Ljg6NTMiXSwKICAgICAgICAgIFsiZG5zLmV4YW1wbGUiXSwKICAgICAgICAgIFsiMTI3LjEiXSwKICAgICAgICAgIFsiMDEuMi4zLjQiXSwKICAgICAgICAgIFsiMjAwMTowZGI4OjoxIl0sCiAgICAgICAgICBbIjo6RkZGRjo4LjguOC44Il0sCiAgICAgICAgICBbMV0sCiAgICAgICAgICAiOC44LjguOCIKICAgICAgICBdIGRvCiAgICAgIHJlamVjdChKYXNvbi5lbmNvZGUhKE1hcC5wdXQob2JqZWN0LCAicmVzb2x2ZXJzIiwgcmVzb2x2ZXJzKSksIHJvb3RzKQogICAgZW5kCiAgZW5kCgogIHRlc3QgIklTMDIgbm9uZXhpc3RlbnQsIGVtcHR5IG9yIGludmFsaWQgQ0EgaW5wdXRzIGFyZSBib3VuZGVkIGNhdGVnb3JpZXMiLCAle3Jvb3RzOiByb290c30gZG8KICAgIHJhdyA9IEphc29uLmVuY29kZSEoU3RhcnR1cEZpeHR1cmUuZW52ZWxvcGUoKSkKCiAgICBmb3IgdmFsdWUgPC0gW25pbCwgW10sICJzZW5zaXRpdmUtY2VydCIsIFsic2Vuc2l0aXZlLWNlcnQiXSwgW25pbF0sIHJvb3RzICsrIFsiYmFkIl1dIGRvCiAgICAgIHJlamVjdChyYXcsIHZhbHVlLCAiY2Ffcm9vdHMiKQogICAgZW5kCiAgZW5kCmVuZAo=","hosted/test/mixer_hosted/identity/startup_lifecycle_test.exs":"ZGVmbW9kdWxlIE1peGVySG9zdGVkLklkZW50aXR5LlN0YXJ0dXBMaWZlY3ljbGVUZXN0IGRvCiAgdXNlIEV4VW5pdC5DYXNlLCBhc3luYzogZmFsc2UKCiAgYWxpYXMgTWl4ZXJIb3N0ZWQuSWRlbnRpdHkuewogICAgQ29uZmlndXJlZFZlcmlmaWVyLAogICAgS2V5T3duZXIsCiAgICBLZXlPd25lclN1cGVydmlzb3IsCiAgICBTdGFydHVwQ29uZmlnLAogICAgU3RhcnR1cEZpeHR1cmUKICB9CgogIHNldHVwX2FsbCBkbwogICAgU3RhcnR1cEZpeHR1cmUucHJlcGFyZV9kYXRhYmFzZSgpCiAgICA6b2sKICBlbmQKCiAgc2V0dXAgZG8KICAgIHByaW9yID0gQXBwbGljYXRpb24uZ2V0X2FsbF9lbnYoOm1peGVyX2hvc3RlZCkKCiAgICBvbl9leGl0KGZuIC0+CiAgICAgIEFwcGxpY2F0aW9uLnN0b3AoOm1peGVyX2hvc3RlZCkKCiAgICAgIGZvciB7a2V5LCBffSA8LSBBcHBsaWNhdGlvbi5nZXRfYWxsX2Vudig6bWl4ZXJfaG9zdGVkKSwKICAgICAgICAgIGRvOiBBcHBsaWNhdGlvbi5kZWxldGVfZW52KDptaXhlcl9ob3N0ZWQsIGtleSkKCiAgICAgIGZvciB7a2V5LCB2YWx1ZX0gPC0gcHJpb3IsIGRvOiBBcHBsaWNhdGlvbi5wdXRfZW52KDptaXhlcl9ob3N0ZWQsIGtleSwgdmFsdWUpCiAgICBlbmQpCgogICAgOm9rCiAgZW5kCgogIGRlZnAgc3RhcnQoaWRlbnRpdHkpIGRvCiAgICBTdGFydHVwRml4dHVyZS5hcHBfc2V0dGluZ3MoaWRlbnRpdHkpCiAgICBhc3NlcnQgezpvaywgX30gPSBBcHBsaWNhdGlvbi5lbnN1cmVfYWxsX3N0YXJ0ZWQoOm1peGVyX2hvc3RlZCkKICBlbmQKCiAgZGVmcCBsaXZlbmVzcyBkbwogICAgezpvaywge18sIHBvcnR9fSA9IE1peGVySG9zdGVkV2ViLkVuZHBvaW50LnNlcnZlcl9pbmZvKDpodHRwKQogICAgdXJsID0gfmMiaHR0cDovLzEyNy4wLjAuMToiICsrIEludGVnZXIudG9fY2hhcmxpc3QocG9ydCkgKysgfmMiL2hlYWx0aC9saXZlIgogICAgYXNzZXJ0IHs6b2ssIHt7XywgMjAwLCBffSwgXywgYm9keX19ID0gOmh0dHBjLnJlcXVlc3QoOmdldCwge3VybCwgW119LCBbdGltZW91dDogMl8wMDBdLCBbXSkKICAgIGFzc2VydCBKYXNvbi5kZWNvZGUhKGJvZHkpID09ICV7InN0YXR1cyIgPT4gImFsaXZlIn0KICBlbmQKCiAgZGVmcCBldmVudHVhbGx5KGZ1biwgdHJpZXMgXFwgMTAwKQogIGRlZnAgZXZlbnR1YWxseShmdW4sIDApLCBkbzogYXNzZXJ0KGZ1bi4oKSkKCiAgZGVmcCBldmVudHVhbGx5KGZ1biwgdHJpZXMpIGRvCiAgICBpZiBmdW4uKCksCiAgICAgIGRvOiA6b2ssCiAgICAgIGVsc2U6CiAgICAgICAgKAogICAgICAgICAgUHJvY2Vzcy5zbGVlcCgxMCkKICAgICAgICAgIGV2ZW50dWFsbHkoZnVuLCB0cmllcyAtIDEpCiAgICAgICAgKQogIGVuZAoKICB0ZXN0ICJJUzAxIGFjdHVhbCBkaXNhYmxlZCBzdGFydHVwIGhhcyBlbmRwb2ludCBhbmQgbm8gaWRlbnRpdHkgb3duZXIiIGRvCiAgICBzdGFydChTdGFydHVwQ29uZmlnLmxvYWQhKCV7fSwgOmFwaSwgW10pKQogICAgYXNzZXJ0IFByb2Nlc3Mud2hlcmVpcyhLZXlPd25lcikgPT0gbmlsCgogICAgYXNzZXJ0IHs6ZXJyb3IsIDppZGVudGl0eV91bmF2YWlsYWJsZX0gPQogICAgICAgICAgICAgQ29uZmlndXJlZFZlcmlmaWVyLmF1dGhlbnRpY2F0ZSgic3ludGhldGljIiwgU3lzdGVtLnN5c3RlbV90aW1lKDpzZWNvbmQpKQoKICAgIGxpdmVuZXNzKCkKICBlbmQKCiAgdGVzdCAiSVMwMSBhY3R1YWwgZGlzYWJsZWQgcHJvY2Vzc29yIHN0YXJ0cyBubyBlbmRwb2ludCBvciBpZGVudGl0eSBvd25lciIgZG8KICAgIGRpc2FibGVkID0gU3RhcnR1cENvbmZpZy5sb2FkISgle30sIDpwcm9jZXNzb3IsIFtdKQoKICAgIHNldHRpbmdzID0KICAgICAgTWl4ZXJIb3N0ZWQuUnVudGltZUNvbmZpZy5sb2FkISgKICAgICAgICBNYXAucHV0KFN0YXJ0dXBGaXh0dXJlLmZvdW5kYXRpb25fZW52KCksICJNSVhFUl9IT1NURURfUk9MRSIsICJwcm9jZXNzb3IiKQogICAgICApCgogICAgU3RhcnR1cEZpeHR1cmUuYXBwX3NldHRpbmdzKGRpc2FibGVkKQogICAgQXBwbGljYXRpb24ucHV0X2Vudig6bWl4ZXJfaG9zdGVkLCA6cm9sZSwgOnByb2Nlc3NvcikKICAgIEFwcGxpY2F0aW9uLnB1dF9lbnYoOm1peGVyX2hvc3RlZCwgT2Jhbiwgc2V0dGluZ3Mub2JhbikKICAgIGFzc2VydCB7Om9rLCBffSA9IEFwcGxpY2F0aW9uLmVuc3VyZV9hbGxfc3RhcnRlZCg6bWl4ZXJfaG9zdGVkKQogICAgYXNzZXJ0IFByb2Nlc3Mud2hlcmVpcyhLZXlPd25lcikgPT0gbmlsCiAgICBhc3NlcnQgUHJvY2Vzcy53aGVyZWlzKE1peGVySG9zdGVkV2ViLkVuZHBvaW50KSA9PSBuaWwKCiAgICBhc3NlcnQgRW51bS5tYXAoT2Jhbi5jb25maWcoKS5xdWV1ZXMsIGZuIHtuYW1lLCBvcHRpb25zfSAtPiB7bmFtZSwgb3B0aW9uc1s6bGltaXRdfSBlbmQpID09CiAgICAgICAgICAgICBzZXR0aW5ncy5vYmFuWzpxdWV1ZXNdCiAgZW5kCgogIHRlc3QgIklTMDMgYWN0dWFsIGNvbmZpZ3VyZWQgYXBwbGljYXRpb24gb3ducyBhbiBlbXB0eSBib3VuZGVkIGNvbXBvbmVudCBiZWZvcmUgZW5kcG9pbnQiIGRvCiAgICBzZXR0aW5ncyA9CiAgICAgIFN0YXJ0dXBGaXh0dXJlLmNvbmZpZ3VyYXRpb24oU3RhcnR1cEZpeHR1cmUuZW52ZWxvcGUoKSwgU3RhcnR1cEZpeHR1cmUuc3RhbmRhcmRfcm9vdHMoKSkKCiAgICBbTWl4ZXJIb3N0ZWQuUmVwbywge09iYW4sIF99LCB7S2V5T3duZXJTdXBlcnZpc29yLCBffSwgTWl4ZXJIb3N0ZWRXZWIuRW5kcG9pbnRdID0KICAgICAgTWl4ZXJIb3N0ZWQuQXBwbGljYXRpb24uY2hpbGRyZW4oOmFwaSwgW10sIHNldHRpbmdzKQoKICAgIHN0YXJ0KHNldHRpbmdzKQogICAgb3duZXIgPSBQcm9jZXNzLndoZXJlaXMoS2V5T3duZXIpCiAgICBhc3NlcnQgaXNfcGlkKG93bmVyKQogICAgcm9vdF9jaGlsZHJlbiA9IFN1cGVydmlzb3Iud2hpY2hfY2hpbGRyZW4oTWl4ZXJIb3N0ZWQuU3VwZXJ2aXNvcikKCiAgICBhc3NlcnQge0tleU93bmVyU3VwZXJ2aXNvciwgY29tcG9uZW50LCA6c3VwZXJ2aXNvciwgX30gPQogICAgICAgICAgICAgTGlzdC5rZXlmaW5kKHJvb3RfY2hpbGRyZW4sIEtleU93bmVyU3VwZXJ2aXNvciwgMCkKCiAgICBhc3NlcnQgRW51bS5hbnk/KFN1cGVydmlzb3Iud2hpY2hfY2hpbGRyZW4oY29tcG9uZW50KSwgZm4ge18sIHBpZCwgXywgX30gLT4gcGlkID09IG93bmVyIGVuZCkKICAgIHN0YXRlID0gOnN5cy5nZXRfc3RhdGUob3duZXIpCgogICAgZm9yIGtleSA8LSBbOnNuYXBzaG90cywgOmF0dGVtcHRzLCA6ZmxpZ2h0cywgOndhaXRlcnMsIDphZG1pdHRlZCwgOm5lZ2F0aXZlc10sCiAgICAgICAgZG86IGFzc2VydChzdGF0ZVtrZXldID09ICV7fSkKCiAgICBhc3NlcnQgRHluYW1pY1N1cGVydmlzb3IuY291bnRfY2hpbGRyZW4oc3RhdGUud29ya2VycykuYWN0aXZlID09IDAKICAgIGxpdmVuZXNzKCkKCiAgICBTdGFydHVwRml4dHVyZS5ldmlkZW5jZSgic3RhcnR1cC1lbXB0eS1zdGF0ZS5qc29uIiwgJXsKICAgICAgYWN0dWFsQXBwbGljYXRpb246IHRydWUsCiAgICAgIGVuZHBvaW50TGl2ZW5lc3M6IDIwMCwKICAgICAgb3duZXJSZWdpc3RlcmVkOiB0cnVlLAogICAgICBpbml0aWFsU25hcHNob3RzOiAwLAogICAgICBpbml0aWFsQXR0ZW1wdHM6IDAsCiAgICAgIGluaXRpYWxGbGlnaHRzOiAwLAogICAgICBzdGFydHVwRmV0Y2hlczogMAogICAgfSkKICBlbmQKCiAgdGVzdCAiSVMwMyBtaXNzaW5nIHZhbGlkYXRlZCBiaW5kaW5nIGFuZCBpbnZhbGlkIHJlcXVpcmVkIG93bmVyIHByZXZlbnQgZW5kcG9pbnQgc3RhcnR1cCIgZG8KICAgIFN0YXJ0dXBGaXh0dXJlLmFwcF9zZXR0aW5ncyhTdGFydHVwQ29uZmlnLmxvYWQhKCV7fSwgOmFwaSwgW10pKQogICAgQXBwbGljYXRpb24uZGVsZXRlX2Vudig6bWl4ZXJfaG9zdGVkLCA6aWRlbnRpdHlfc3RhcnR1cCkKICAgIGFzc2VydCB7OmVycm9yLCBffSA9IEFwcGxpY2F0aW9uLmVuc3VyZV9hbGxfc3RhcnRlZCg6bWl4ZXJfaG9zdGVkKQogICAgYXNzZXJ0IFByb2Nlc3Mud2hlcmVpcyhNaXhlckhvc3RlZFdlYi5FbmRwb2ludCkgPT0gbmlsCiAgICBhc3NlcnQgUHJvY2Vzcy53aGVyZWlzKEtleU93bmVyKSA9PSBuaWwKCiAgICB2YWxpZCA9CiAgICAgIFN0YXJ0dXBGaXh0dXJlLmNvbmZpZ3VyYXRpb24oU3RhcnR1cEZpeHR1cmUuZW52ZWxvcGUoKSwgU3RhcnR1cEZpeHR1cmUuc3RhbmRhcmRfcm9vdHMoKSkKCiAgICAjIEV4aXN0aW5nIHByb2R1Y3Rpb24gY29uc3RydWN0b3IgbXVzdCByZWplY3QgdGVzdC1vbmx5IHRyYW5zcG9ydCBvcHRpb25zLgogICAgYmFkID0gJXsKICAgICAgdmFsaWQKICAgICAgfCBvd25lcl9vcHRpb25zOiB2YWxpZC5vd25lcl9vcHRpb25zICsrIFtmaXh0dXJlOiAle2lwOiB7MTI3LCAwLCAwLCAxfSwgcG9ydDogMX1dCiAgICB9CgogICAgU3RhcnR1cEZpeHR1cmUuYXBwX3NldHRpbmdzKGJhZCkKICAgIGFzc2VydCB7OmVycm9yLCBffSA9IEFwcGxpY2F0aW9uLmVuc3VyZV9hbGxfc3RhcnRlZCg6bWl4ZXJfaG9zdGVkKQogICAgYXNzZXJ0IFByb2Nlc3Mud2hlcmVpcyhNaXhlckhvc3RlZFdlYi5FbmRwb2ludCkgPT0gbmlsCiAgICBhc3NlcnQgUHJvY2Vzcy53aGVyZWlzKEtleU93bmVyKSA9PSBuaWwKICBlbmQKCiAgdGVzdCAiSVMwNCBkaXNhYmxlZCBib3VuZCBwcm9maWxlIHJlamVjdHMgdmlhIHB1YmxpYyBhZGFwdGVyIHdpdGhvdXQgYW55IGZsaWdodCIgZG8KICAgIG9iamVjdCA9CiAgICAgIHB1dF9pbihTdGFydHVwRml4dHVyZS5lbnZlbG9wZSgpLCBbInByb2ZpbGVzIiwgQWNjZXNzLmF0KDApLCAicHJvZmlsZSIsICJlbmFibGVkIl0sIGZhbHNlKQoKICAgIHN0YXJ0KFN0YXJ0dXBGaXh0dXJlLmNvbmZpZ3VyYXRpb24ob2JqZWN0LCBTdGFydHVwRml4dHVyZS5zdGFuZGFyZF9yb290cygpKSkKCiAgICBhc3NlcnQgezplcnJvciwgOnVuYXV0aGVudGljYXRlZH0gPQogICAgICAgICAgICAgQ29uZmlndXJlZFZlcmlmaWVyLmF1dGhlbnRpY2F0ZSgic3ludGhldGljIiwgU3lzdGVtLnN5c3RlbV90aW1lKDpzZWNvbmQpKQoKICAgIHN0YXRlID0gOnN5cy5nZXRfc3RhdGUoS2V5T3duZXIpCiAgICBhc3NlcnQgc3RhdGUuYXR0ZW1wdHMgPT0gJXt9CiAgICBhc3NlcnQgc3RhdGUuZmxpZ2h0cyA9PSAle30KICAgIGxpdmVuZXNzKCkKICBlbmQKCiAgdGVzdCAiSVMwNSBhY3R1YWwgb3duZXIgc3VwZXJ2aXNpb24gcmVzdGFydHMgZW1wdHkgYW5kIGFwcGxpY2F0aW9uIHNodXRkb3duIHJlbW92ZXMgYXV0aG9yaXR5IiBkbwogICAgc2V0dGluZ3MgPQogICAgICBTdGFydHVwRml4dHVyZS5jb25maWd1cmF0aW9uKFN0YXJ0dXBGaXh0dXJlLmVudmVsb3BlKCksIFN0YXJ0dXBGaXh0dXJlLnN0YW5kYXJkX3Jvb3RzKCkpCgogICAgc3RhcnQoc2V0dGluZ3MpCiAgICBvd25lciA9IFByb2Nlc3Mud2hlcmVpcyhLZXlPd25lcikKICAgIG9sZF9zdGF0ZSA9IDpzeXMuZ2V0X3N0YXRlKG93bmVyKQogICAgb2xkX3dvcmtlcnMgPSBQcm9jZXNzLndoZXJlaXMob2xkX3N0YXRlLndvcmtlcnMpCiAgICBQcm9jZXNzLmV4aXQob3duZXIsIDpraWxsKQogICAgZXZlbnR1YWxseShmbiAtPiBpc19waWQoUHJvY2Vzcy53aGVyZWlzKEtleU93bmVyKSkgYW5kIFByb2Nlc3Mud2hlcmVpcyhLZXlPd25lcikgIT0gb3duZXIgZW5kKQogICAgc3RhdGUgPSA6c3lzLmdldF9zdGF0ZShLZXlPd25lcikKICAgIHJlZnV0ZSBzdGF0ZS5lcG9jaCA9PSBvbGRfc3RhdGUuZXBvY2gKICAgIGFzc2VydCBzdGF0ZS5zbmFwc2hvdHMgPT0gJXt9CiAgICBhc3NlcnQgUHJvY2Vzcy53aGVyZWlzKHN0YXRlLndvcmtlcnMpICE9IG9sZF93b3JrZXJzCiAgICBsaXZlbmVzcygpCiAgICBhc3NlcnQgOm9rID0gQXBwbGljYXRpb24uc3RvcCg6bWl4ZXJfaG9zdGVkKQogICAgYXNzZXJ0IFByb2Nlc3Mud2hlcmVpcyhLZXlPd25lcikgPT0gbmlsCiAgICBhc3NlcnQgUHJvY2Vzcy53aGVyZWlzKHN0YXRlLndvcmtlcnMpID09IG5pbAogICAgYXNzZXJ0IFByb2Nlc3Mud2hlcmVpcyhNaXhlckhvc3RlZFdlYi5FbmRwb2ludCkgPT0gbmlsCgogICAgYXNzZXJ0IHs6ZXJyb3IsIDppZGVudGl0eV91bmF2YWlsYWJsZX0gPQogICAgICAgICAgICAgQ29uZmlndXJlZFZlcmlmaWVyLmF1dGhlbnRpY2F0ZSgic3ludGhldGljIiwgU3lzdGVtLnN5c3RlbV90aW1lKDpzZWNvbmQpKQoKICAgIHN0YXJ0KHNldHRpbmdzKQogICAgcmVmdXRlIDpzeXMuZ2V0X3N0YXRlKEtleU93bmVyKS5lcG9jaCA9PSBzdGF0ZS5lcG9jaAogICAgYXNzZXJ0IDpzeXMuZ2V0X3N0YXRlKEtleU93bmVyKS5zbmFwc2hvdHMgPT0gJXt9CgogICAgU3RhcnR1cEZpeHR1cmUuZXZpZGVuY2UoInN0YXJ0dXAtbGlmZWN5Y2xlLmpzb24iLCAlewogICAgICBhY3R1YWxBcHBsaWNhdGlvbjogdHJ1ZSwKICAgICAgb3duZXJDcmFzaFJlc3RhcnQ6IHRydWUsCiAgICAgIHdvcmtlclN1cGVydmlzb3JSZXBsYWNlZDogdHJ1ZSwKICAgICAgbmV3RXBvY2g6IHRydWUsCiAgICAgIHNodXRkb3duQXV0aG9yaXR5UmVtb3ZlZDogdHJ1ZSwKICAgICAgcmVzdGFydEVtcHR5OiB0cnVlCiAgICB9KQogIGVuZAplbmQK","hosted/test/runtime_config_test.exs":"ZGVmbW9kdWxlIE1peGVySG9zdGVkLlJ1bnRpbWVDb25maWdUZXN0IGRvCiAgdXNlIEV4VW5pdC5DYXNlLCBhc3luYzogdHJ1ZQogIGFsaWFzIE1peGVySG9zdGVkLlJ1bnRpbWVDb25maWcKCiAgZGVmcCBlbnYgZG8KICAgICV7CiAgICAgICJNSVhFUl9IT1NURURfUk9MRSIgPT4gImFwaSIsCiAgICAgICJNSVhFUl9EQVRBQkFTRV9IT1NUIiA9PiAiZXAtZml4dHVyZS51cy1lYXN0LTIuYXdzLm5lb24udGVjaCIsCiAgICAgICJNSVhFUl9EQVRBQkFTRV9OQU1FIiA9PiAibWl4ZXJfZml4dHVyZSIsCiAgICAgICJNSVhFUl9EQVRBQkFTRV9VU0VSIiA9PiAibWl4ZXJfZml4dHVyZSIsCiAgICAgICJNSVhFUl9EQVRBQkFTRV9QQVNTV09SRCIgPT4gInN5bnRoZXRpYy1kYXRhYmFzZS1zZWNyZXQiLAogICAgICAiTUlYRVJfU0VDUkVUX0tFWV9CQVNFIiA9PiBTdHJpbmcuZHVwbGljYXRlKCJzeW50aGV0aWMtc2VjcmV0LSIsIDgpCiAgICB9CiAgZW5kCgogIHRlc3QgIkFQSSBjYW5ub3QgcHJvY2VzcyBqb2JzIGFuZCB1c2VzIGJvdW5kZWQgdmVyaWZpZWQgVExTIGNvbm5lY3Rpb25zIiBkbwogICAgY29uZmlnID0gUnVudGltZUNvbmZpZy5sb2FkIShlbnYoKSkKICAgIGFzc2VydCBjb25maWcucm9sZSA9PSA6YXBpCiAgICBhc3NlcnQgY29uZmlnLm9iYW5bOnF1ZXVlc10gPT0gW10KICAgIGFzc2VydCBjb25maWcub2Jhbls6cGVlcl0gPT0gZmFsc2UKICAgIGFzc2VydCBjb25maWcub2Jhbls6c3RhZ2VyXSA9PSBbaW50ZXJ2YWw6IDppbmZpbml0eV0KICAgIGFzc2VydCBjb25maWcub2Jhbls6bm90aWZpZXJdID09IE9iYW4uTm90aWZpZXJzLlBvc3RncmVzCiAgICBhc3NlcnQgY29uZmlnLnJlcG9bOnBvb2xfc2l6ZV0gPT0gOAogICAgYXNzZXJ0IGNvbmZpZy5yZXBvWzpwb29sX2NvdW50XSA9PSAxCiAgICBhc3NlcnQgY29uZmlnLmRhdGFiYXNlX2Nvbm5lY3Rpb25fYm91bmQgPT0gOQogICAgYXNzZXJ0IGNvbmZpZy5yZXBvWzpzc2xdWzp2ZXJpZnldID09IDp2ZXJpZnlfcGVlcgogICAgYXNzZXJ0IGNvbmZpZy5yZXBvWzpzc2xdWzpjYWNlcnRzXSAhPSBbXQoKICAgIGFzc2VydCBjb25maWcucmVwb1s6c3NsXVs6c2VydmVyX25hbWVfaW5kaWNhdGlvbl0gPT0KICAgICAgICAgICAgIH5jImVwLWZpeHR1cmUudXMtZWFzdC0yLmF3cy5uZW9uLnRlY2giCgogICAgYXNzZXJ0IGlzX2Z1bmN0aW9uKGNvbmZpZy5yZXBvWzpzc2xdWzpjdXN0b21pemVfaG9zdG5hbWVfY2hlY2tdWzptYXRjaF9mdW5dLCAyKQogICAgYXNzZXJ0IGNvbmZpZy5lbmRwb2ludFs6aHR0cF1bOmlwXSA9PSB7MTI3LCAwLCAwLCAxfQogICAgcmVmdXRlIGluc3BlY3QoY29uZmlnKSA9fiAic3ludGhldGljIgoKICAgIGFzc2VydCBFbnVtLm1lbWJlcj8oCiAgICAgICAgICAgICBNaXhlckhvc3RlZC5BcHBsaWNhdGlvbi5jaGlsZHJlbig6YXBpLCBjb25maWcub2JhbiksCiAgICAgICAgICAgICBNaXhlckhvc3RlZFdlYi5FbmRwb2ludAogICAgICAgICAgICkKICBlbmQKCiAgdGVzdCAicHJvY2Vzc29yIGhhcyBzZXBhcmF0ZSBib3VuZGVkIHF1ZXVlcyBhbmQgbm8gSFRUUCBlbmRwb2ludCIgZG8KICAgIGNvbmZpZyA9IFJ1bnRpbWVDb25maWcubG9hZCEoTWFwLnB1dChlbnYoKSwgIk1JWEVSX0hPU1RFRF9ST0xFIiwgInByb2Nlc3NvciIpKQoKICAgIGFzc2VydCBLZXl3b3JkLmtleXMoY29uZmlnLm9iYW5bOnF1ZXVlc10pID09CiAgICAgICAgICAgICBbOmJ1aWxkcywgOnNpZ25pbmcsIDpzdWJtaXNzaW9ucywgOnJlbGVhc2VzLCA6dGVsZW1ldHJ5LCA6YmlsbGluZ10KCiAgICBhc3NlcnQgRW51bS5hbGw/KGNvbmZpZy5vYmFuWzpxdWV1ZXNdLCBmbiB7XywgbGltaXR9IC0+IGxpbWl0ID09IDEgZW5kKQogICAgYXNzZXJ0IGNvbmZpZy5lbmRwb2ludCA9PSBbc2VydmVyOiBmYWxzZV0KICAgIGFzc2VydCBjb25maWcub2Jhbls6cGx1Z2luc10gPT0gW10KICAgIGFzc2VydCBjb25maWcub2Jhbls6cGVlcl0gPT0gT2Jhbi5QZWVycy5EYXRhYmFzZQogICAgYXNzZXJ0IGNvbmZpZy5vYmFuWzpzdGFnZXJdID09IFtpbnRlcnZhbDogMV8wMDBdCgogICAgcmVmdXRlIEVudW0ubWVtYmVyPygKICAgICAgICAgICAgIE1peGVySG9zdGVkLkFwcGxpY2F0aW9uLmNoaWxkcmVuKDpwcm9jZXNzb3IsIGNvbmZpZy5vYmFuKSwKICAgICAgICAgICAgIE1peGVySG9zdGVkV2ViLkVuZHBvaW50CiAgICAgICAgICAgKQogIGVuZAoKICB0ZXN0ICJyZXF1aXJlZCBjb25maWd1cmF0aW9uIGZhaWxzIGNsb3NlZCB3aXRob3V0IGxlYWtpbmcgdmFsdWVzIiBkbwogICAgZm9yIGtleSA8LSBNYXAua2V5cyhlbnYoKSkgZG8KICAgICAgYXNzZXJ0X3JhaXNlIEFyZ3VtZW50RXJyb3IsICJpbnZhbGlkIG9yIG1pc3NpbmcgaG9zdGVkIHNldHRpbmc6ICIgPD4ga2V5LCBmbiAtPgogICAgICAgIFJ1bnRpbWVDb25maWcubG9hZCEoTWFwLmRlbGV0ZShlbnYoKSwga2V5KSkKICAgICAgZW5kCiAgICBlbmQKCiAgICBmb3Ige2tleSwgdmFsdWV9IDwtIFsKICAgICAgICAgIHsiTUlYRVJfSE9TVEVEX1JPTEUiLCAiYXBpLHByb2Nlc3NvciJ9LAogICAgICAgICAgeyJNSVhFUl9EQVRBQkFTRV9IT1NUIiwgImVwLWZpeHR1cmUtcG9vbGVyLnVzLWVhc3QtMi5hd3MubmVvbi50ZWNoIn0sCiAgICAgICAgICB7Ik1JWEVSX0RBVEFCQVNFX0hPU1QiLCAidXNlcjpzZWNyZXRAZGIuZXhhbXBsZSJ9LAogICAgICAgICAgeyJNSVhFUl9EQVRBQkFTRV9IT1NUIiwgImRiLmV4YW1wbGU/c3NsbW9kZT1kaXNhYmxlIn0sCiAgICAgICAgICB7Ik1JWEVSX0RBVEFCQVNFX0hPU1QiLCAiZGIuZXhhbXBsZVxuIn0sCiAgICAgICAgICB7Ik1JWEVSX0RBVEFCQVNFX0hPU1QiLCAiZGIuLmV4YW1wbGUifSwKICAgICAgICAgIHsiTUlYRVJfREFUQUJBU0VfUE9PTF9TSVpFIiwgIjIxIn0sCiAgICAgICAgICB7Ik1JWEVSX0RBVEFCQVNFX1BPT0xfU0laRSIsICIwIn0sCiAgICAgICAgICB7Ik1JWEVSX0RBVEFCQVNFX1BPT0xfU0laRSIsICI4anVuayJ9LAogICAgICAgICAgeyJNSVhFUl9IVFRQX0JJTkQiLCAiZGIuZXhhbXBsZSJ9LAogICAgICAgICAgeyJNSVhFUl9IVFRQX1BPUlQiLCAiNjU1MzYifSwKICAgICAgICAgIHsiTUlYRVJfU0VDUkVUX0tFWV9CQVNFIiwgInNob3J0LXNlY3JldCJ9CiAgICAgICAgXSBkbwogICAgICBhc3NlcnRfcmFpc2UgQXJndW1lbnRFcnJvciwgImludmFsaWQgb3IgbWlzc2luZyBob3N0ZWQgc2V0dGluZzogIiA8PiBrZXksIGZuIC0+CiAgICAgICAgUnVudGltZUNvbmZpZy5sb2FkIShNYXAucHV0KGVudigpLCBrZXksIHZhbHVlKSkKICAgICAgZW5kCiAgICBlbmQKICBlbmQKCiAgdGVzdCAicXVldWUgYm91bmRzIGNhbm5vdCBiZSB3aWRlbmVkIG9yIGludGVycHJldGVkIGFzIGFyYml0cmFyeSBhdG9tcyIgZG8KICAgIGZvciB2YWx1ZSA8LSBbIjAiLCAiOSIsICJpbmZpbml0eSIsICIxLjAiXSBkbwogICAgICBiYWQgPQogICAgICAgIGVudigpCiAgICAgICAgfD4gTWFwLnB1dCgiTUlYRVJfSE9TVEVEX1JPTEUiLCAicHJvY2Vzc29yIikKICAgICAgICB8PiBNYXAucHV0KCJNSVhFUl9RVUVVRV9CVUlMRFNfQ09OQ1VSUkVOQ1kiLCB2YWx1ZSkKCiAgICAgIGFzc2VydF9yYWlzZSBBcmd1bWVudEVycm9yLCBmbiAtPiBSdW50aW1lQ29uZmlnLmxvYWQhKGJhZCkgZW5kCiAgICBlbmQKICBlbmQKZW5kCg==","hosted/test/support/identity_startup_fixture.ex":"ZGVmbW9kdWxlIE1peGVySG9zdGVkLklkZW50aXR5LlN0YXJ0dXBGaXh0dXJlIGRvCiAgQG1vZHVsZWRvYyBmYWxzZQogIGFsaWFzIE1peGVySG9zdGVkLklkZW50aXR5LlN0YXJ0dXBDb25maWcKCiAgZGVmIHN0YW5kYXJkX3Jvb3RzIGRvCiAgICBFbnVtLm1hcCg6cHVibGljX2tleS5jYWNlcnRzX2dldCgpLCBmbgogICAgICB7OmNlcnQsIGRlciwgX30gLT4gZGVyCiAgICAgIGRlciAtPiBkZXIKICAgIGVuZCkKICBlbmQKCiAgZGVmIGVudmVsb3BlIGRvCiAgICAlewogICAgICAidmVyc2lvbiIgPT4gMSwKICAgICAgImdlbmVyYXRpb24iID0+IDEsCiAgICAgICJiaW5kaW5nIiA9PiAic3RhcnR1cC1maXh0dXJlIiwKICAgICAgInByb2ZpbGVzIiA9PiBbZW50cnkoKV0sCiAgICAgICJyZXNvbHZlcnMiID0+IFsiMTI3LjAuMC4xIl0KICAgIH0KICBlbmQKCiAgZGVmIGVudHJ5IGRvCiAgICAlewogICAgICAicHJvZmlsZSIgPT4gJXsKICAgICAgICAicHJvZmlsZV9pZCIgPT4gInN0YXJ0dXAtZml4dHVyZSIsCiAgICAgICAgInByb2ZpbGVfdmVyc2lvbiIgPT4gMSwKICAgICAgICAiaXNzdWVyIiA9PiAiaHR0cHM6Ly9pc3N1ZXIuZml4dHVyZS5pbnZhbGlkL29hdXRoIiwKICAgICAgICAiYXVkaWVuY2UiID0+ICJtaXhlci1hcGkiLAogICAgICAgICJjbGllbnRfaWQiID0+ICJyZXZpZXdlZC1jbGllbnQiLAogICAgICAgICJpZGVudGl0eV9jbGFzcyIgPT4gImh1bWFuIiwKICAgICAgICAiZW5hYmxlZCIgPT4gdHJ1ZQogICAgICB9LAogICAgICAiandrc19lbmRwb2ludCIgPT4gJXsiaG9zdCIgPT4gImp3a3MuZml4dHVyZS5pbnZhbGlkIiwgInBvcnQiID0+IDQ0MywgInBhdGgiID0+ICIva2V5cyJ9LAogICAgICAidHJhbnNwb3J0IiA9PiAiaG9zdGVkX2h0dHBzIgogICAgfQogIGVuZAoKICBkZWYgY29uZmlndXJhdGlvbihvYmplY3QsIHJvb3RzKSwKICAgIGRvOgogICAgICBTdGFydHVwQ29uZmlnLmxvYWQhKAogICAgICAgICV7CiAgICAgICAgICAiTUlYRVJfSURFTlRJVFlfTU9ERSIgPT4gImNvbmZpZ3VyZWQiLAogICAgICAgICAgIk1JWEVSX0lERU5USVRZX0NPTkZJRyIgPT4gSmFzb24uZW5jb2RlIShvYmplY3QpCiAgICAgICAgfSwKICAgICAgICA6YXBpLAogICAgICAgIHJvb3RzCiAgICAgICkKCiAgZGVmIGZvdW5kYXRpb25fZW52IGRvCiAgICAlewogICAgICAiTUlYRVJfSE9TVEVEX1JPTEUiID0+ICJhcGkiLAogICAgICAiTUlYRVJfREFUQUJBU0VfSE9TVCIgPT4gImRiLmV4YW1wbGUudGVzdCIsCiAgICAgICJNSVhFUl9EQVRBQkFTRV9OQU1FIiA9PiAibWl4ZXJfZm91bmRhdGlvbl90ZXN0IiwKICAgICAgIk1JWEVSX0RBVEFCQVNFX1VTRVIiID0+ICJtaXhlcl9maXh0dXJlIiwKICAgICAgIk1JWEVSX0RBVEFCQVNFX1BBU1NXT1JEIiA9PiAic3ludGhldGljIiwKICAgICAgIk1JWEVSX1NFQ1JFVF9LRVlfQkFTRSIgPT4gU3RyaW5nLmR1cGxpY2F0ZSgic3ludGhldGljLSIsIDgpCiAgICB9CiAgZW5kCgogIGRlZiBhcHBfc2V0dGluZ3MoaWRlbnRpdHkpIGRvCiAgICBzZXR0aW5ncyA9IE1peGVySG9zdGVkLlJ1bnRpbWVDb25maWcubG9hZCEoZm91bmRhdGlvbl9lbnYoKSkKICAgIEFwcGxpY2F0aW9uLnB1dF9lbnYoOm1peGVyX2hvc3RlZCwgOnJvbGUsIHNldHRpbmdzLnJvbGUpCiAgICBBcHBsaWNhdGlvbi5wdXRfZW52KDptaXhlcl9ob3N0ZWQsIDppZGVudGl0eV9zdGFydHVwLCBpZGVudGl0eSkKCiAgICBBcHBsaWNhdGlvbi5wdXRfZW52KDptaXhlcl9ob3N0ZWQsIE1peGVySG9zdGVkLlJlcG8sCiAgICAgIGhvc3RuYW1lOiAiMTI3LjAuMC4xIiwKICAgICAgcG9ydDogU3RyaW5nLnRvX2ludGVnZXIoU3lzdGVtLmZldGNoX2VudiEoIk1JWEVSX1RFU1RfREFUQUJBU0VfUE9SVCIpKSwKICAgICAgZGF0YWJhc2U6ICJtaXhlcl9zdGFydHVwX3Rlc3QiLAogICAgICB1c2VybmFtZTogIm1peGVyX2ZpeHR1cmUiLAogICAgICBwb29sX3NpemU6IDIsCiAgICAgIHNzbDogZmFsc2UKICAgICkKCiAgICBBcHBsaWNhdGlvbi5wdXRfZW52KDptaXhlcl9ob3N0ZWQsIE9iYW4sIHNldHRpbmdzLm9iYW4pCgogICAgZW5kcG9pbnQgPQogICAgICBBcHBsaWNhdGlvbi5nZXRfZW52KDptaXhlcl9ob3N0ZWQsIE1peGVySG9zdGVkV2ViLkVuZHBvaW50KQogICAgICB8PiBLZXl3b3JkLm1lcmdlKHNldHRpbmdzLmVuZHBvaW50KQogICAgICB8PiBLZXl3b3JkLnB1dCg6aHR0cCwgaXA6IHsxMjcsIDAsIDAsIDF9LCBwb3J0OiAwKQoKICAgIEFwcGxpY2F0aW9uLnB1dF9lbnYoOm1peGVyX2hvc3RlZCwgTWl4ZXJIb3N0ZWRXZWIuRW5kcG9pbnQsIGVuZHBvaW50KQogICAgOm9rCiAgZW5kCgogIGRlZiBwcmVwYXJlX2RhdGFiYXNlIGRvCiAgICBhcHBfc2V0dGluZ3MoU3RhcnR1cENvbmZpZy5sb2FkISgle30sIDphcGksIFtdKSkKCiAgICB7Om9rLCByZXBvfSA9CiAgICAgIE1peGVySG9zdGVkLlJlcG8uc3RhcnRfbGluayhBcHBsaWNhdGlvbi5mZXRjaF9lbnYhKDptaXhlcl9ob3N0ZWQsIE1peGVySG9zdGVkLlJlcG8pKQoKICAgIHBhdGggPSBBcHBsaWNhdGlvbi5hcHBfZGlyKDptaXhlcl9ob3N0ZWQsICJwcml2L3JlcG8vbWlncmF0aW9ucyIpCiAgICBFY3RvLk1pZ3JhdG9yLnJ1bihNaXhlckhvc3RlZC5SZXBvLCBwYXRoLCA6dXAsIGFsbDogdHJ1ZSkKICAgIFN1cGVydmlzb3Iuc3RvcChyZXBvKQogIGVuZAoKICBkZWYgdG9rZW4oa2V5KSBkbwogICAgbm93ID0gU3lzdGVtLnN5c3RlbV90aW1lKDpzZWNvbmQpCgogICAgY2xhaW1zID0gJXsKICAgICAgImlzcyIgPT4gZW50cnkoKVsicHJvZmlsZSJdWyJpc3N1ZXIiXSwKICAgICAgImF1ZCIgPT4gIm1peGVyLWFwaSIsCiAgICAgICJzdWIiID0+ICJzeW50aGV0aWMtc3RhcnR1cC1zdWJqZWN0IiwKICAgICAgImNsaWVudF9pZCIgPT4gInJldmlld2VkLWNsaWVudCIsCiAgICAgICJpYXQiID0+IG5vdyAtIDEsCiAgICAgICJleHAiID0+IG5vdyArIDEyMCwKICAgICAgImp0aSIgPT4gInN5bnRoZXRpYy1zdGFydHVwLXRva2VuIgogICAgfQoKICAgIEpPU0UuSldTLnNpZ24oa2V5LCBKYXNvbi5lbmNvZGUhKGNsYWltcyksICV7CiAgICAgICJhbGciID0+ICJSUzI1NiIsCiAgICAgICJ0eXAiID0+ICJhdCtqd3QiLAogICAgICAia2lkIiA9PiAic3RhcnR1cC1rZXkiCiAgICB9KQogICAgfD4gSk9TRS5KV1MuY29tcGFjdCgpCiAgICB8PiBlbGVtKDEpCiAgZW5kCgogIGRlZiBldmlkZW5jZShuYW1lLCB2YWx1ZSkgZG8KICAgIGNhc2UgU3lzdGVtLmdldF9lbnYoIk1JWEVSX1RFU1RfSURFTlRJVFlfRVZJREVOQ0UiKSBkbwogICAgICBuaWwgLT4gOm9rCiAgICAgIGRpciAtPiBGaWxlLndyaXRlIShQYXRoLmpvaW4oZGlyLCBuYW1lKSwgSmFzb24uZW5jb2RlISh2YWx1ZSwgcHJldHR5OiB0cnVlKSkKICAgIGVuZAogIGVuZAplbmQKCmRlZm1vZHVsZSBNaXhlckhvc3RlZC5JZGVudGl0eS5TdGFydHVwRE5TRml4dHVyZSBkbwogIEBtb2R1bGVkb2MgZmFsc2UKICB1c2UgR2VuU2VydmVyCiAgZGVmIHN0YXJ0X2xpbmsoXyksIGRvOiBHZW5TZXJ2ZXIuc3RhcnRfbGluayhfX01PRFVMRV9fLCBbXSkKCiAgZGVmIGluaXQoXykgZG8KICAgIHs6b2ssIHNvY2tldH0gPSA6Z2VuX3VkcC5vcGVuKDUzLCBbOmJpbmFyeSwgaXA6IHsxMjcsIDAsIDAsIDF9LCBhY3RpdmU6IHRydWVdKQogICAgezpvaywgJXtzb2NrZXQ6IHNvY2tldCwgcXVlcmllczogW119fQogIGVuZAoKICBkZWYgaGFuZGxlX2NhbGwoOnF1ZXJpZXMsIF8sIHMpLCBkbzogezpyZXBseSwgcy5xdWVyaWVzLCBzfQoKICBkZWYgaGFuZGxlX2luZm8oezp1ZHAsIHNvY2tldCwgaXAsIHBvcnQsIHJhd30sIHMpIGRvCiAgICB7Om9rLCBtZXNzYWdlfSA9IDppbmV0X2Rucy5kZWNvZGUocmF3KQogICAgW3F1ZXJ5XSA9IDppbmV0X2Rucy5tc2cobWVzc2FnZSwgOnFkbGlzdCkKICAgIG5hbWUgPSA6aW5ldF9kbnMuZG5zX3F1ZXJ5KHF1ZXJ5LCA6ZG9tYWluKQogICAgdHlwZSA9IDppbmV0X2Rucy5kbnNfcXVlcnkocXVlcnksIDp0eXBlKQogICAgaGVhZGVyID0gOmluZXRfZG5zLm1zZyhtZXNzYWdlLCA6aGVhZGVyKQogICAgaGVhZGVyID0gOmluZXRfZG5zLm1ha2VfaGVhZGVyKGhlYWRlciwgcXI6IHRydWUsIGFhOiBmYWxzZSwgcmE6IHRydWUpCgogICAgYW5zd2VycyA9CiAgICAgIGlmIHR5cGUgPT0gOmEsCiAgICAgICAgZG86IFs6aW5ldF9kbnMubWFrZV9ycihkb21haW46IG5hbWUsIHR5cGU6IDphLCBjbGFzczogOmluLCB0dGw6IDEyMCwgZGF0YTogezgsIDgsIDgsIDh9KV0sCiAgICAgICAgZWxzZTogW10KCiAgICByZXBseSA9IDppbmV0X2Rucy5tYWtlX21zZyhtZXNzYWdlLCBoZWFkZXI6IGhlYWRlciwgYW5saXN0OiBhbnN3ZXJzKSB8PiA6aW5ldF9kbnMuZW5jb2RlKCkKICAgIDpvayA9IDpnZW5fdWRwLnNlbmQoc29ja2V0LCBpcCwgcG9ydCwgcmVwbHkpCiAgICB7Om5vcmVwbHksICV7cyB8IHF1ZXJpZXM6IFt7bmFtZSwgdHlwZX0gfCBzLnF1ZXJpZXNdfX0KICBlbmQKCiAgZGVmIHRlcm1pbmF0ZShfLCBzKSwgZG86IDpnZW5fdWRwLmNsb3NlKHMuc29ja2V0KQplbmQK","hosted/test/mixer_hosted/browser_auth/storage_fixture.exs":"ZGVmbW9kdWxlIE1peGVySG9zdGVkLkJyb3dzZXJBdXRoLlN0b3JhZ2VGaXh0dXJlLkFkbWluIGRvCiAgdXNlIEVjdG8uUmVwbywgb3RwX2FwcDogOmJyb3dzZXJfc3RvcmFnZV9maXh0dXJlLCBhZGFwdGVyOiBFY3RvLkFkYXB0ZXJzLlBvc3RncmVzCmVuZAoKZGVmbW9kdWxlIE1peGVySG9zdGVkLkJyb3dzZXJBdXRoLlN0b3JhZ2VGaXh0dXJlLk1pZ3JhdGlvbiBkbwogIHVzZSBFY3RvLlJlcG8sIG90cF9hcHA6IDpicm93c2VyX3N0b3JhZ2VfZml4dHVyZSwgYWRhcHRlcjogRWN0by5BZGFwdGVycy5Qb3N0Z3JlcwplbmQKCmRlZm1vZHVsZSBNaXhlckhvc3RlZC5Ccm93c2VyQXV0aC5TdG9yYWdlRml4dHVyZS5PcGVyYXRvck1pZ3JhdGlvbiBkbwogIHVzZSBFY3RvLlJlcG8sIG90cF9hcHA6IDpicm93c2VyX3N0b3JhZ2VfZml4dHVyZSwgYWRhcHRlcjogRWN0by5BZGFwdGVycy5Qb3N0Z3JlcwplbmQKCmRlZm1vZHVsZSBNaXhlckhvc3RlZC5Ccm93c2VyQXV0aC5TdG9yYWdlRml4dHVyZSBkbwogIGFsaWFzIE1peGVySG9zdGVkLkJyb3dzZXJBdXRoLlN0b3JhZ2VTY2hlbWEKICBhbGlhcyBNaXhlckhvc3RlZC5Ccm93c2VyQXV0aC5TdG9yYWdlRml4dHVyZS5NaWdyYXRpb24KCiAgZGVmIGluc3RhbGwhKHJlcG8gXFwgTWlncmF0aW9uKSBkbwogICAgZm9yIHttb2R1bGUsIGZpbGV9IDwtIFsKICAgICAgICAgIHtNaXhlckhvc3RlZC5SZXBvLk1pZ3JhdGlvbnMuQWRkQ3VzdG9tZXJBdXRob3JpemF0aW9uLAogICAgICAgICAgICIyMDI2MTAyNTAwMDAwM19hZGRfY3VzdG9tZXJfYXV0aG9yaXphdGlvbi5leHMifSwKICAgICAgICAgIHtNaXhlckhvc3RlZC5SZXBvLk1pZ3JhdGlvbnMuQWRkQXV0aG9yaXphdGlvblN0YXRlUmV2aXNpb25zLAogICAgICAgICAgICIyMDI2MTAyNTAwMDAwNF9hZGRfYXV0aG9yaXphdGlvbl9zdGF0ZV9yZXZpc2lvbnMuZXhzIn0sCiAgICAgICAgICB7TWl4ZXJIb3N0ZWQuUmVwby5NaWdyYXRpb25zLkFkZEN1c3RvbWVyV29ya3NwYWNlRGlzY292ZXJ5LAogICAgICAgICAgICIyMDI2MTAyNTAwMDAwNl9hZGRfY3VzdG9tZXJfd29ya3NwYWNlX2Rpc2NvdmVyeS5leHMifSwKICAgICAgICAgIHtNaXhlckhvc3RlZC5SZXBvLk1pZ3JhdGlvbnMuQWRkQnJvd3NlclNlc3Npb25zLAogICAgICAgICAgICIyMDI2MTAyNTAwMDAwN19hZGRfYnJvd3Nlcl9zZXNzaW9ucy5leHMifQogICAgICAgIF0gZG8KICAgICAgdW5sZXNzIENvZGUuZW5zdXJlX2xvYWRlZD8obW9kdWxlKSwKICAgICAgICBkbzogQ29kZS5yZXF1aXJlX2ZpbGUoUGF0aC5leHBhbmQoIi4uLy4uLy4uL3ByaXYvcmVwby9taWdyYXRpb25zLyIgPD4gZmlsZSwgX19ESVJfXykpCgogICAgICB2ZXJzaW9uID0gU3RyaW5nLnNsaWNlKGZpbGUsIDAsIDE0KSB8PiBTdHJpbmcudG9faW50ZWdlcigpCiAgICAgIDpvayA9IEVjdG8uTWlncmF0b3IudXAocmVwbywgdmVyc2lvbiwgbW9kdWxlLCBsb2c6IGZhbHNlKQogICAgZW5kCiAgZW5kCgogIGRlZiBwcm92aXNpb24hIGRvCiAgICBjb25uID0gY29ubmVjdGlvbiEoImJyb3dzZXJfYWRtaW4iKQoKICAgIHRyeSBkbwogICAgICBFbnVtLmVhY2goCiAgICAgICAgU3RvcmFnZVNjaGVtYS5wcm92aXNpb25pbmdfc3RhdGVtZW50cygiYnJvd3Nlcl93cml0ZXIiLCAiYnJvd3Nlcl9saWZlY3ljbGUiKSwKICAgICAgICAmUG9zdGdyZXgucXVlcnkhKGNvbm4sICYxLCBbXSkKICAgICAgKQogICAgYWZ0ZXIKICAgICAgR2VuU2VydmVyLnN0b3AoY29ubikKICAgIGVuZAogIGVuZAoKICBkZWYgcSEocmVwbywgc3FsLCBwYXJhbXMgXFwgW10pLCBkbzogRWN0by5BZGFwdGVycy5TUUwucXVlcnkhKHJlcG8sIHNxbCwgcGFyYW1zLCBsb2c6IGZhbHNlKQogIGRlZiBub3csIGRvOiBTeXN0ZW0uc3lzdGVtX3RpbWUoOnNlY29uZCkKICBkZWYgcmFuZG9tKG4gXFwgMzIpLCBkbzogOmNyeXB0by5zdHJvbmdfcmFuZF9ieXRlcyhuKQogIGRlZiB0b2tlbiwgZG86IEJhc2UudXJsX2VuY29kZTY0KHJhbmRvbSgpLCBwYWRkaW5nOiBmYWxzZSkKICBkZWYgcmVxdWVzdCwgZG86IEJhc2UuZW5jb2RlMTYocmFuZG9tKDE2KSwgY2FzZTogOmxvd2VyKQogIGRlZiBjaXBoZXIsIGRvOiB7ImZpeHR1cmUtdjEiLCByYW5kb20oMTIpLCByYW5kb20oMTYpLCByYW5kb20oNDgpfQoKICBkZWYgY29ubmVjdGlvbiEocm9sZSBcXCAiYnJvd3Nlcl9saWZlY3ljbGUiKSBkbwogICAgezpvaywgY29ubn0gPQogICAgICBQb3N0Z3JleC5zdGFydF9saW5rKAogICAgICAgIGhvc3RuYW1lOiAiMTI3LjAuMC4xIiwKICAgICAgICBwb3J0OiBwb3J0KCksCiAgICAgICAgdXNlcm5hbWU6IHJvbGUsCiAgICAgICAgZGF0YWJhc2U6ICJicm93c2VyX3N0b3JhZ2UiLAogICAgICAgIHNzbDogZmFsc2UsCiAgICAgICAgYmFja29mZl90eXBlOiA6c3RvcAogICAgICApCgogICAgUHJvY2Vzcy51bmxpbmsoY29ubikKICAgIFBvc3RncmV4LnF1ZXJ5IShjb25uLCAiU0VUIHN0YXRlbWVudF90aW1lb3V0PSc1cyciLCBbXSkKICAgIFBvc3RncmV4LnF1ZXJ5IShjb25uLCAiU0VUIGxvY2tfdGltZW91dD0nNTAwbXMnIiwgW10pCiAgICBQb3N0Z3JleC5xdWVyeSEoY29ubiwgIlNFVCBpZGxlX2luX3RyYW5zYWN0aW9uX3Nlc3Npb25fdGltZW91dD0nNXMnIiwgW10pCiAgICBjb25uCiAgZW5kCgogIGRlZiBwb3J0LCBkbzogU3RyaW5nLnRvX2ludGVnZXIoU3lzdGVtLmZldGNoX2VudiEoIk1JWEVSX0JST1dTRVJfU1RPUkFHRV9QT1JUIikpCgogIGRlZiBjYWxsKGNvbm4sIG5hbWUsIGFyZ3MpIGRvCiAgICB7c3FsLCB2YWx1ZXN9ID0gcXVlcnkobmFtZSwgYXJncykKCiAgICBjYXNlIFBvc3RncmV4LnF1ZXJ5KGNvbm4sIHNxbCwgdmFsdWVzLCB0aW1lb3V0OiA1XzAwMCwgcXVldWU6IGZhbHNlKSBkbwogICAgICB7Om9rLCAle3Jvd3M6IFtbdmFsdWVdXX19IC0+IHs6b2ssIHZhbHVlfQogICAgICB7OmVycm9yLCBlcnJvcn0gLT4gezplcnJvciwgZXJyb3IucG9zdGdyZXMuY29kZX0KICAgIGVuZAogIGVuZAoKICAjIENvbXBvc2l0ZSB2YWx1ZXMgdXNlIGV4cGxpY2l0IFJPVyBjYXN0cyB3aXRoIGJvdW5kIHByaW1pdGl2ZSBwYXJhbWV0ZXJzLgogICMgVGhlIGRhdGFiYXNlIGRyaXZlciBuZXZlciBwYXJzZXMgcHJvdmlkZXIvYnJvd3NlciB0ZXh0IGludG8gU1FMLgogIGRlZiBxdWVyeShuYW1lLCBhcmdzKSBkbwogICAge2V4cHJlc3Npb25zLCB2YWx1ZXMsIF99ID0KICAgICAgRW51bS5yZWR1Y2UoYXJncywge1tdLCBbXSwgMX0sIGZuIGFyZywge2V4cHIsIHZhbHVlcywgbn0gLT4KICAgICAgICB7Y2FzdCwgcHJpbWl0aXZlfSA9CiAgICAgICAgICBjYXNlIGFyZyBkbwogICAgICAgICAgICB7OmNpcGhlciwge2tleSwgaXYsIHRhZywgY2lwaGVydGV4dH19IC0+CiAgICAgICAgICAgICAgeyJST1coJCN7bn0sJCN7biArIDF9LCQje24gKyAyfSwkI3tuICsgM30pOjpwdWJsaWMubWl4ZXJfYnJvd3Nlcl9jaXBoZXIiLAogICAgICAgICAgICAgICBba2V5LCBpdiwgdGFnLCBjaXBoZXJ0ZXh0XX0KCiAgICAgICAgICAgIHs6YXR0ZW1wdCwgYX0gLT4KICAgICAgICAgICAgICB7a2V5LCBpdiwgdGFnLCBjaXBoZXJ0ZXh0fSA9IGEuY2lwaGVyCgogICAgICAgICAgICAgIHsiUk9XKCQje259LCQje24gKyAxfSwkI3tuICsgMn0sJCN7biArIDN9LCQje24gKyA0fSwkI3tuICsgNX0sJCN7biArIDZ9LCQje24gKyA3fSxST1coJCN7biArIDh9LCQje24gKyA5fSwkI3tuICsgMTB9LCQje24gKyAxMX0pOjpwdWJsaWMubWl4ZXJfYnJvd3Nlcl9jaXBoZXIpOjpwdWJsaWMubWl4ZXJfYnJvd3Nlcl9hdHRlbXB0IiwKICAgICAgICAgICAgICAgWwogICAgICAgICAgICAgICAgIGEuc3RhdGUsCiAgICAgICAgICAgICAgICAgYS5ub25jZSwKICAgICAgICAgICAgICAgICBhLnByb2ZpbGUsCiAgICAgICAgICAgICAgICAgMSwKICAgICAgICAgICAgICAgICBhLmlzc3VlciwKICAgICAgICAgICAgICAgICBhLmNsaWVudCwKICAgICAgICAgICAgICAgICBhLnJlZGlyZWN0LAogICAgICAgICAgICAgICAgIGEuZXhwaXJlcywKICAgICAgICAgICAgICAgICBrZXksCiAgICAgICAgICAgICAgICAgaXYsCiAgICAgICAgICAgICAgICAgdGFnLAogICAgICAgICAgICAgICAgIGNpcGhlcnRleHQKICAgICAgICAgICAgICAgXX0KCiAgICAgICAgICAgIHs6dmVyaWZpZWQsIGl9IC0+CiAgICAgICAgICAgICAgeyJST1coJCN7bn0sJCN7biArIDF9LCQje24gKyAyfSwkI3tuICsgM30sJCN7biArIDR9LCQje24gKyA1fSwkI3tuICsgNn0sJCN7biArIDd9LCQje24gKyA4fSwkI3tuICsgOX0sJCN7biArIDEwfSwkI3tuICsgMTF9KTo6cHVibGljLm1peGVyX2Jyb3dzZXJfdmVyaWZpZWQiLAogICAgICAgICAgICAgICBbCiAgICAgICAgICAgICAgICAgaS5wcm9maWxlLAogICAgICAgICAgICAgICAgIDEsCiAgICAgICAgICAgICAgICAgaS5pc3N1ZXIsCiAgICAgICAgICAgICAgICAgaS5zdWJqZWN0LAogICAgICAgICAgICAgICAgIGkuY2xpZW50LAogICAgICAgICAgICAgICAgIGkuanRpLAogICAgICAgICAgICAgICAgIGkuaWF0LAogICAgICAgICAgICAgICAgIGkuZXhwLAogICAgICAgICAgICAgICAgIGkuc2NvcGVzLAogICAgICAgICAgICAgICAgIGkucHJvZmlsZV9yZXZpc2lvbiwKICAgICAgICAgICAgICAgICBpLmJpbmRpbmdfcmV2aXNpb24sCiAgICAgICAgICAgICAgICAgaS5wcmluY2lwYWxfcmV2aXNpb24KICAgICAgICAgICAgICAgXX0KCiAgICAgICAgICAgIHByaW1pdGl2ZSAtPgogICAgICAgICAgICAgIHsiJCN7bn0iLCBbcHJpbWl0aXZlXX0KICAgICAgICAgIGVuZAoKICAgICAgICB7ZXhwciArKyBbY2FzdF0sIHZhbHVlcyArKyBwcmltaXRpdmUsIG4gKyBsZW5ndGgocHJpbWl0aXZlKX0KICAgICAgZW5kKQoKICAgIHsiU0VMRUNUIHB1YmxpYy5taXhlcl9icm93c2VyXyN7bmFtZX0oI3tFbnVtLmpvaW4oZXhwcmVzc2lvbnMsICIsIil9KSIsIHZhbHVlc30KICBlbmQKCiAgZGVmIGJvb3RzdHJhcChjb25uLCBkZWFkbGluZSBcXCBub3coKSArIDI1MCkgZG8KICAgIGNvb2tpZSA9IHJhbmRvbSgpCiAgICBjb25maWcgPSByYW5kb20oKQogICAgY3NyZiA9IHJhbmRvbSgpCiAgICBpZCA9IHJhbmRvbSgxNikKCiAgICBhcmdzID0gWwogICAgICBpZCwKICAgICAgY29va2llLAogICAgICB0b2tlbigpLAogICAgICBjc3JmLAogICAgICBjb25maWcsCiAgICAgICJodW1hbnMiLAogICAgICAxLAogICAgICBkZWFkbGluZSwKICAgICAgezpjaXBoZXIsIGNpcGhlcigpfSwKICAgICAgcmVxdWVzdCgpCiAgICBdCgogICAgezpvaywgc25hcHNob3R9ID0gY2FsbChjb25uLCA6Ym9vdHN0cmFwLCBhcmdzKQogICAgJXtpZDogaWQsIGNvb2tpZTogY29va2llLCBjb25maWc6IGNvbmZpZywgY3NyZjogY3NyZiwgcmV2aXNpb246IDEsIHNuYXBzaG90OiBzbmFwc2hvdH0KICBlbmQKCiAgZGVmIGJlZ2luX2xvZ2luKGNvbm4sIGIsIGV4cGlyZXMgXFwgbm93KCkgKyAxNTApIGRvCiAgICBhID0gJXsKICAgICAgc3RhdGU6IHJhbmRvbSgpLAogICAgICBub25jZTogcmFuZG9tKCksCiAgICAgIHByb2ZpbGU6ICJodW1hbnMiLAogICAgICBpc3N1ZXI6ICJodHRwczovL2lzc3Vlci5maXh0dXJlIiwKICAgICAgY2xpZW50OiAiY29uc29sZSIsCiAgICAgIHJlZGlyZWN0OiAiaHR0cHM6Ly9jb25zb2xlLmZpeHR1cmUvYXV0aC9jYWxsYmFjayIsCiAgICAgIGV4cGlyZXM6IGV4cGlyZXMsCiAgICAgIGNpcGhlcjogY2lwaGVyKCkKICAgIH0KCiAgICB7Om9rLCBzbmFwfSA9CiAgICAgIGNhbGwoY29ubiwgOmJlZ2luLCBbCiAgICAgICAgYi5jb29raWUsCiAgICAgICAgYi5jc3JmLAogICAgICAgIGIuY29uZmlnLAogICAgICAgIGIucmV2aXNpb24sCiAgICAgICAgezphdHRlbXB0LCBhfSwKICAgICAgICB7OmNpcGhlciwgY2lwaGVyKCl9LAogICAgICAgIHJlcXVlc3QoKQogICAgICBdKQoKICAgIHsle2IgfCByZXZpc2lvbjogYi5yZXZpc2lvbiArIDEsIHNuYXBzaG90OiBzbmFwfSwgYX0KICBlbmQKCiAgZGVmIGNsYWltKGNvbm4sIGIsIGEsIGRlYWRsaW5lIFxcIG5vdygpICsgNTUpIGRvCiAgICBjbGFpbSA9IHJhbmRvbSgpCgogICAgezpvaywgc25hcHNob3R9ID0KICAgICAgY2FsbChjb25uLCA6Y2xhaW0sIFtiLmNvb2tpZSwgYS5zdGF0ZSwgYi5jb25maWcsIGIucmV2aXNpb24sIGNsYWltLCBkZWFkbGluZSwgcmVxdWVzdCgpXSkKCiAgICB7Y2xhaW0sIHNuYXBzaG90fQogIGVuZAoKICBkZWYgaWRlbnRpdHkoanRpIFxcIHRva2VuKCkpIGRvCiAgICAlewogICAgICBwcm9maWxlOiAiaHVtYW5zIiwKICAgICAgaXNzdWVyOiAiaHR0cHM6Ly9pc3N1ZXIuZml4dHVyZSIsCiAgICAgIHN1YmplY3Q6ICJzdWJqZWN0LTEiLAogICAgICBjbGllbnQ6ICJjb25zb2xlIiwKICAgICAganRpOiBqdGksCiAgICAgIGlhdDogbm93KCkgLSA1LAogICAgICBleHA6IG5vdygpICsgNjAwLAogICAgICBzY29wZXM6IFsibWl4ZXIud29ya3NwYWNlLnJlYWQiXSwKICAgICAgcHJvZmlsZV9yZXZpc2lvbjogMSwKICAgICAgYmluZGluZ19yZXZpc2lvbjogMSwKICAgICAgcHJpbmNpcGFsX3JldmlzaW9uOiAxCiAgICB9CiAgZW5kCgogIGRlZiBhY3RpdmF0ZShjb25uLCBiLCBhLCBjbGFpbSwgaSBcXCBpZGVudGl0eSgpKSBkbwogICAgbmV3X2Nvb2tpZSA9IHJhbmRvbSgpCiAgICBuZXdfY3NyZiA9IHJhbmRvbSgpCiAgICBnZW5lcmF0aW9uID0gdG9rZW4oKQogICAgZmFtaWx5ID0gImJyb3dzZXJfIiA8PiB0b2tlbigpCgogICAgYXJncyA9IFsKICAgICAgYi5jb29raWUsCiAgICAgIGEuc3RhdGUsCiAgICAgIGIuY29uZmlnLAogICAgICBjbGFpbSwKICAgICAgYi5yZXZpc2lvbiwKICAgICAgezp2ZXJpZmllZCwgaX0sCiAgICAgIG5ld19jb29raWUsCiAgICAgIG5ld19jc3JmLAogICAgICBnZW5lcmF0aW9uLAogICAgICBmYW1pbHksCiAgICAgIG5vdygpICsgNTAwLAogICAgICB7OmNpcGhlciwgY2lwaGVyKCl9LAogICAgICByZXF1ZXN0KCkKICAgIF0KCiAgICB7Y2FsbChjb25uLCA6YWN0aXZhdGUsIGFyZ3MpLAogICAgICV7YiB8IGNvb2tpZTogbmV3X2Nvb2tpZSwgY3NyZjogbmV3X2NzcmYsIHJldmlzaW9uOiBiLnJldmlzaW9uICsgMX0sIGZhbWlseSwgaSwgYXJnc30KICBlbmQKZW5kCg==","hosted/test/mixer_hosted/browser_auth/run_storage_fixture.py":"IyEvdXNyL2Jpbi9lbnYgcHl0aG9uMwoiIiJPbmUgZGlzcG9zYWJsZSBQRyBwcm9jZXNzOyBleHBsaWNpdCBvcmRpbmFyeSBzb3VyY2VzLCBubyBNaXggb3IgZnJvemVuIGxhbmVzLiIiIgppbXBvcnQgYXJncGFyc2UKaW1wb3J0IGRhdGV0aW1lCmltcG9ydCBoYXNobGliCmltcG9ydCBqc29uCmltcG9ydCBvcwppbXBvcnQgcGF0aGxpYgppbXBvcnQgc2h1dGlsCmltcG9ydCBzaWduYWwKaW1wb3J0IHNvY2tldAppbXBvcnQgc3VicHJvY2VzcwppbXBvcnQgdGVtcGZpbGUKaW1wb3J0IHV1aWQKClJPT1QgPSBwYXRobGliLlBhdGgoX19maWxlX18pLnJlc29sdmUoKS5wYXJlbnRzWzNdClJFUE8gPSBST09ULnBhcmVudApCQVNFID0gUkVQTyAvICJ2ZXJpZmljYXRpb24vaG9zdGVkLWJyb3dzZXItc2Vzc2lvbi1zdG9yYWdlIgpwYXJzZXIgPSBhcmdwYXJzZS5Bcmd1bWVudFBhcnNlcihkZXNjcmlwdGlvbj1fX2RvY19fKQpwYXJzZXIuYWRkX2FyZ3VtZW50KCItLXBnLWJpbiIsIHR5cGU9cGF0aGxpYi5QYXRoLCBkZWZhdWx0PXBhdGhsaWIuUGF0aCgiL29wdC9ob21lYnJldy9vcHQvcG9zdGdyZXNxbEAxNy9iaW4iKSkKYXJncyA9IHBhcnNlci5wYXJzZV9hcmdzKCkKUEcgPSBhcmdzLnBnX2Jpbi5yZXNvbHZlKCkKQkFTRS5ta2RpcihwYXJlbnRzPVRydWUsIGV4aXN0X29rPVRydWUpCnN0YW1wID0gZGF0ZXRpbWUuZGF0ZXRpbWUubm93KGRhdGV0aW1lLnRpbWV6b25lLnV0Yykuc3RyZnRpbWUoIiVZJW0lZFQlSCVNJVMuJWZaIikgKyAiLSIgKyB1dWlkLnV1aWQ0KCkuaGV4Wzo4XQojIEVhcmxpZXIgZGV2ZWxvcG1lbnQgdXNlZCBvdmVyd3JpdHRlbiBsYXRlc3QgbG9ncy4gUHJlc2VydmUgdGhhdCBsYXN0IHNuYXBzaG90LAojIGV4cGxpY2l0bHkgd2l0aG91dCBjbGFpbWluZyBpdCByZWNvbnN0cnVjdHMgdGhlIGVhcmxpZXIgb3ZlcndyaXR0ZW4gYXR0ZW1wdHMuCmxlZ2FjeSA9IFtwIGZvciBwIGluIEJBU0UuaXRlcmRpcigpIGlmIHAuaXNfZmlsZSgpIGFuZCAocC5zdWZmaXggPT0gIi5sb2ciIG9yIHAubmFtZSA9PSAicmVjZWlwdC5qc29uIildCmlmIGxlZ2FjeToKICAgIGRldmVsb3BtZW50ID0gQkFTRSAvICgiZGV2ZWxvcG1lbnQtc25hcHNob3QtIiArIHN0YW1wKQogICAgZGV2ZWxvcG1lbnQubWtkaXIoKQogICAgZm9yIHBhdGggaW4gbGVnYWN5OgogICAgICAgIHNodXRpbC5tb3ZlKHN0cihwYXRoKSwgZGV2ZWxvcG1lbnQgLyBwYXRoLm5hbWUpCiAgICAoZGV2ZWxvcG1lbnQgLyAiUkVBRE1FLnR4dCIpLndyaXRlX3RleHQoIkxhc3Qgb3ZlcndyaXR0ZW4gZGV2ZWxvcG1lbnQgb3V0cHV0LCBwcmVzZXJ2ZWQgd2hlbiBpbW11dGFibGUgYXR0ZW1wdCByZWNvcmRpbmcgYmVnYW4uIEVhcmxpZXIgcGVyLXJ1biBvdXRwdXRzIHdlcmUgbm90IHJldGFpbmVkIGFuZCBhcmUgbm90IHJlY29uc3RydWN0ZWQgaGVyZS5cbiIpCk9VVCA9IEJBU0UgLyAiYXR0ZW1wdHMiIC8gc3RhbXAKT1VULm1rZGlyKHBhcmVudHM9VHJ1ZSkKc291cmNlX3BhdGhzID0gWwogICAgUk9PVCAvICJsaWIvbWl4ZXJfaG9zdGVkL2Jyb3dzZXJfYXV0aC9zdG9yYWdlX3NjaGVtYS5leCIsCiAgICBST09UIC8gImxpYi9taXhlcl9ob3N0ZWQvYnJvd3Nlcl9hdXRoL3ZhdWx0LmV4IiwKICAgIFJPT1QgLyAibGliL21peGVyX2hvc3RlZC9icm93c2VyX2F1dGgvc3RvcmVkX3NuYXBzaG90LmV4IiwKICAgIFJPT1QgLyAidGVzdC9taXhlcl9ob3N0ZWQvYnJvd3Nlcl9hdXRoL3N0b3JhZ2VfZml4dHVyZS5leHMiLAogICAgUk9PVCAvICJ0ZXN0L21peGVyX2hvc3RlZC9icm93c2VyX2F1dGgvc3RvcmFnZV9zcGVjLmV4cyIsCiAgICBwYXRobGliLlBhdGgoX19maWxlX18pLnJlc29sdmUoKSwgUkVQTyAvICJkb2NzL2hvc3RlZC1icm93c2VyLXNlc3Npb24tc3RvcmFnZS5tZCIsCiAgICBST09UIC8gIm1peC5leHMiLCBST09UIC8gIm1peC5sb2NrIiwKXSArIFtST09UIC8gInByaXYvcmVwby9taWdyYXRpb25zIiAvIG5hbWUgZm9yIG5hbWUgaW4gWwogICAgIjIwMjYxMDI1MDAwMDAzX2FkZF9jdXN0b21lcl9hdXRob3JpemF0aW9uLmV4cyIsCiAgICAiMjAyNjEwMjUwMDAwMDRfYWRkX2F1dGhvcml6YXRpb25fc3RhdGVfcmV2aXNpb25zLmV4cyIsCiAgICAiMjAyNjEwMjUwMDAwMDZfYWRkX2N1c3RvbWVyX3dvcmtzcGFjZV9kaXNjb3ZlcnkuZXhzIiwKICAgICIyMDI2MTAyNTAwMDAwN19hZGRfYnJvd3Nlcl9zZXNzaW9ucy5leHMiLApdXQojIEV4cGxpY2l0IGRlcGVuZGVuY3kgcGF0aHMgZXhjbHVkZSB0aGUgY29tcGxldGUgaG9zdGVkIGFwcGxpY2F0aW9uJ3MgZXhpc3RpbmcKIyBiZWFtcy4gTm8gZnJvemVuIGFwcGxpY2F0aW9uIHNvdXJjZSBvciBiZWFtIGlzIHJlYWQsIGNvbXBpbGVkIG9yIGltcG9ydGVkLgpkZXBlbmRlbmN5X2RpcnMgPSBzb3J0ZWQocCAvICJlYmluIiBmb3IgcCBpbiAoUk9PVCAvICJfYnVpbGQvdGVzdC9saWIiKS5pdGVyZGlyKCkKICAgICAgICAgICAgICAgICAgICAgICAgIGlmIHAubmFtZSAhPSAibWl4ZXJfaG9zdGVkIiBhbmQgKHAgLyAiZWJpbiIpLmlzX2RpcigpKQpiZWFtX3BhdGhzID0gc29ydGVkKHBhdGggZm9yIGRpcmVjdG9yeSBpbiBkZXBlbmRlbmN5X2RpcnMgZm9yIHBhdGggaW4gZGlyZWN0b3J5Lmdsb2IoIiouYmVhbSIpKQppZiBub3QgYmVhbV9wYXRoczoKICAgIHJhaXNlIFJ1bnRpbWVFcnJvcigiRXhpc3RpbmcgbG9ja2VkIGRlcGVuZGVuY3kgYmVhbXMgcmVxdWlyZWQ7IHRoaXMgcnVubmVyIG5ldmVyIGJ1aWxkcyB0aGUgZnVsbCBhcHAiKQoKZGVmIGRpZ2VzdChwYXRoKToKICAgIHJldHVybiBoYXNobGliLnNoYTI1NihwYXRoLnJlYWRfYnl0ZXMoKSkuaGV4ZGlnZXN0KCkKCmRlZiBtYW5pZmVzdCgpOgogICAgcmV0dXJuIHsic291cmNlcyI6IHtzdHIocC5yZWxhdGl2ZV90byhSRVBPKSk6IGRpZ2VzdChwKSBmb3IgcCBpbiBzb3VyY2VfcGF0aHN9LAogICAgICAgICAgICAiZGVwZW5kZW5jeV9iZWFtcyI6IHtzdHIocC5yZWxhdGl2ZV90byhSRVBPKSk6IGRpZ2VzdChwKSBmb3IgcCBpbiBiZWFtX3BhdGhzfX0KCmJlZm9yZSA9IG1hbmlmZXN0KCkKKE9VVCAvICJzb3VyY2UtbWFuaWZlc3QuanNvbiIpLndyaXRlX3RleHQoanNvbi5kdW1wcyhiZWZvcmUsIGluZGVudD0yKSArICJcbiIpCnJlY29yZHMgPSBbXQpzY3JhdGNoID0gTm9uZQpzdWNjZXNzID0gRmFsc2UKdW5jaGFuZ2VkID0gRmFsc2UKc3RvcHBlZCA9IFRydWUKcmV2aXNpb24gPSBOb25lCgpkZWYgcnVuKG5hbWUsIGNvbW1hbmQsIGVudj1Ob25lLCBjaGVjaz1UcnVlLCB0aW1lb3V0PTMwKToKICAgIGNvbW1hbmQgPSBbc3RyKHZhbHVlKSBmb3IgdmFsdWUgaW4gY29tbWFuZF0KICAgIHByb2Nlc3MgPSBzdWJwcm9jZXNzLlBvcGVuKGNvbW1hbmQsIGN3ZD1SRVBPLCBlbnY9ZW52LCB0ZXh0PVRydWUsCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBzdGRvdXQ9c3VicHJvY2Vzcy5QSVBFLCBzdGRlcnI9c3VicHJvY2Vzcy5TVERPVVQsCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICBzdGFydF9uZXdfc2Vzc2lvbj1UcnVlKQogICAgdGltZWRfb3V0ID0gRmFsc2UKICAgIHRyeToKICAgICAgICBvdXRwdXQsIF8gPSBwcm9jZXNzLmNvbW11bmljYXRlKHRpbWVvdXQ9dGltZW91dCkKICAgIGV4Y2VwdCBzdWJwcm9jZXNzLlRpbWVvdXRFeHBpcmVkOgogICAgICAgIHRpbWVkX291dCA9IFRydWUKICAgICAgICBvcy5raWxscGcocHJvY2Vzcy5waWQsIHNpZ25hbC5TSUdLSUxMKQogICAgICAgIG91dHB1dCwgXyA9IHByb2Nlc3MuY29tbXVuaWNhdGUodGltZW91dD01KQogICAgKE9VVCAvIChuYW1lICsgIi5sb2ciKSkud3JpdGVfdGV4dChvdXRwdXQpCiAgICByZWNvcmRzLmFwcGVuZCh7Im5hbWUiOiBuYW1lLCAiY29tbWFuZCI6IGNvbW1hbmQsICJ0aW1lb3V0X3NlY29uZHMiOiB0aW1lb3V0LAogICAgICAgICAgICAgICAgICAgICJ0aW1lZF9vdXQiOiB0aW1lZF9vdXQsICJleGl0X2NvZGUiOiBwcm9jZXNzLnJldHVybmNvZGUsCiAgICAgICAgICAgICAgICAgICAgIm91dHB1dCI6IG5hbWUgKyAiLmxvZyJ9KQogICAgaWYgKHByb2Nlc3MucmV0dXJuY29kZSBvciB0aW1lZF9vdXQpIGFuZCBjaGVjazoKICAgICAgICBwcmludChvdXRwdXRbLTIwMDAwOl0pCiAgICAgICAgcmFpc2UgUnVudGltZUVycm9yKG5hbWUgKyAiIGZhaWxlZCIpCiAgICByZXR1cm4gcHJvY2Vzcy5yZXR1cm5jb2RlLCBvdXRwdXQKCnRyeToKICAgIF8sIHJldmlzaW9uX291dHB1dCA9IHJ1bigiZ2l0LWhlYWQiLCBbImdpdCIsICJyZXYtcGFyc2UiLCAiSEVBRCJdKQogICAgcmV2aXNpb24gPSByZXZpc2lvbl9vdXRwdXQuc3RyaXAoKQogICAgcnVuKCJwb3N0Z3Jlcy12ZXJzaW9uIiwgW1BHIC8gInBvc3RncmVzIiwgIi0tdmVyc2lvbiJdKQogICAgcnVuKCJlbGl4aXItdmVyc2lvbiIsIFsiZWxpeGlyIiwgIi0tdmVyc2lvbiJdKQogICAgc2NyYXRjaCA9IHBhdGhsaWIuUGF0aCh0ZW1wZmlsZS5ta2R0ZW1wKHByZWZpeD0ibWl4ZXItYnJvd3Nlci1zdG9yYWdlLSIpKQogICAgc29jayA9IHNvY2tldC5zb2NrZXQoKQogICAgc29jay5iaW5kKCgiMTI3LjAuMC4xIiwgMCkpCiAgICBwb3J0ID0gc29jay5nZXRzb2NrbmFtZSgpWzFdCiAgICBzb2NrLmNsb3NlKCkKICAgIHJ1bigiaW5pdGRiIiwgW1BHIC8gImluaXRkYiIsICItRCIsIHNjcmF0Y2ggLyAiZGF0YSIsICItVSIsICJicm93c2VyX2FkbWluIiwKICAgICAgICAgICAgICAgICAgICItQSIsICJ0cnVzdCIsICItLW5vLWxvY2FsZSIsICItRSIsICJVVEY4Il0pCiAgICBydW4oInBvc3RncmVzLXN0YXJ0IiwgW1BHIC8gInBnX2N0bCIsICItRCIsIHNjcmF0Y2ggLyAiZGF0YSIsICItbCIsIE9VVCAvICJwb3N0Z3Jlcy5sb2ciLAogICAgICAgICAgICAgICAgICAgICAgICAgICAiLW8iLCBmIi1oIDEyNy4wLjAuMSAtcCB7cG9ydH0gLWsgJycgLWMgdGltZXpvbmU9VVRDIiwgIi13IiwgInN0YXJ0Il0sIHRpbWVvdXQ9MTUpCiAgICBwc3FsID0gW1BHIC8gInBzcWwiLCAiLVgiLCAiLWgiLCAiMTI3LjAuMC4xIiwgIi1wIiwgc3RyKHBvcnQpLCAiLVUiLCAiYnJvd3Nlcl9hZG1pbiIsCiAgICAgICAgICAgICItZCIsICJwb3N0Z3JlcyIsICItdiIsICJPTl9FUlJPUl9TVE9QPTEiXQogICAgcnVuKCJmaXh0dXJlLXJvbGVzIiwgcHNxbCArIFsiLWMiLCAiQ1JFQVRFIFJPTEUgYnJvd3Nlcl9zY2hlbWFfb3duZXIgTk9MT0dJTiBOT1NVUEVSVVNFUiBOT0JZUEFTU1JMUyBOT0lOSEVSSVQ7IENSRUFURSBST0xFIGJyb3dzZXJfd3JpdGVyIE5PTE9HSU4gTk9TVVBFUlVTRVIgTk9CWVBBU1NSTFMgTk9JTkhFUklUOyBDUkVBVEUgUk9MRSBicm93c2VyX2xpZmVjeWNsZSBMT0dJTiBOT1NVUEVSVVNFUiBOT0JZUEFTU1JMUyBOT0lOSEVSSVQ7IENSRUFURSBST0xFIGJyb3dzZXJfb3JkaW5hcnkgTE9HSU4gTk9TVVBFUlVTRVIgTk9CWVBBU1NSTFMgTk9JTkhFUklUOyBDUkVBVEUgUk9MRSBicm93c2VyX29wZXJhdG9yIExPR0lOIE5PU1VQRVJVU0VSIE5PQllQQVNTUkxTIE5PSU5IRVJJVDsiXSkKICAgIGZvciBkYXRhYmFzZSwgb3duZXIgaW4gWygiYnJvd3Nlcl9zdG9yYWdlIiwgImJyb3dzZXJfc2NoZW1hX293bmVyIiksICgiYnJvd3Nlcl9vcGVyYXRvcl9zdG9yYWdlIiwgImJyb3dzZXJfb3BlcmF0b3IiKV06CiAgICAgICAgcnVuKGRhdGFiYXNlICsgIi1kYXRhYmFzZSIsIFtQRyAvICJjcmVhdGVkYiIsICItaCIsICIxMjcuMC4wLjEiLCAiLXAiLCBzdHIocG9ydCksCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAiLVUiLCAiYnJvd3Nlcl9hZG1pbiIsICItTyIsIG93bmVyLCBkYXRhYmFzZV0pCiAgICBlbnZpcm9ubWVudCA9IG9zLmVudmlyb24uY29weSgpCiAgICBlbnZpcm9ubWVudFsiTUlYRVJfQlJPV1NFUl9TVE9SQUdFX1BPUlQiXSA9IHN0cihwb3J0KQogICAgY29tbWFuZCA9IFsiZWxpeGlyIl0KICAgIGZvciBkaXJlY3RvcnkgaW4gZGVwZW5kZW5jeV9kaXJzOgogICAgICAgIGNvbW1hbmQgKz0gWyItcGEiLCBzdHIoZGlyZWN0b3J5KV0KICAgIGZvciBzb3VyY2UgaW4gWyJzdG9yYWdlX3NjaGVtYS5leCIsICJ2YXVsdC5leCIsICJzdG9yZWRfc25hcHNob3QuZXgiXToKICAgICAgICBjb21tYW5kICs9IFsiLXIiLCBzdHIoUk9PVCAvICJsaWIvbWl4ZXJfaG9zdGVkL2Jyb3dzZXJfYXV0aCIgLyBzb3VyY2UpXQogICAgY29tbWFuZCArPSBbIi1lIiwgJ0V4VW5pdC5zdGFydChzZWVkOiAwKTsgQ29kZS5yZXF1aXJlX2ZpbGUoImhvc3RlZC90ZXN0L21peGVyX2hvc3RlZC9icm93c2VyX2F1dGgvc3RvcmFnZV9zcGVjLmV4cyIpJ10KICAgIHJ1bigiZm9jdXNlZC1leHVuaXQiLCBjb21tYW5kLCBlbnY9ZW52aXJvbm1lbnQsIHRpbWVvdXQ9NjApCiAgICBzdWNjZXNzID0gVHJ1ZQpmaW5hbGx5OgogICAgIyBJbnNwZWN0IHRoZSBvd25lZCBQSUQgZmlsZSBldmVuIGlmIHBnX2N0bCB0aW1lZCBvdXQgb3IgZmFpbGVkIGFmdGVyIHN0YXJ0aW5nLgogICAgIyBObyB1bnJlbGF0ZWQgcHJvY2Vzcy9jb250YWluZXIvc2ltdWxhdG9yIGlzIGVudW1lcmF0ZWQsIGtpbGxlZCBvciBtb2RpZmllZC4KICAgIGlmIHNjcmF0Y2ggaXMgbm90IE5vbmUgYW5kIChzY3JhdGNoIC8gImRhdGEvcG9zdG1hc3Rlci5waWQiKS5leGlzdHMoKToKICAgICAgICBjb2RlLCBfID0gcnVuKCJwb3N0Z3Jlcy1zdG9wIiwgW1BHIC8gInBnX2N0bCIsICItRCIsIHNjcmF0Y2ggLyAiZGF0YSIsICItbSIsICJpbW1lZGlhdGUiLCAiLXciLCAic3RvcCJdLCBjaGVjaz1GYWxzZSwgdGltZW91dD0xNSkKICAgICAgICBzdG9wcGVkID0gY29kZSA9PSAwIGFuZCBub3QgKHNjcmF0Y2ggLyAiZGF0YS9wb3N0bWFzdGVyLnBpZCIpLmV4aXN0cygpCiAgICBlbGlmIHNjcmF0Y2ggaXMgbm90IE5vbmU6CiAgICAgICAgc3RvcHBlZCA9IG5vdCAoc2NyYXRjaCAvICJkYXRhL3Bvc3RtYXN0ZXIucGlkIikuZXhpc3RzKCkKICAgIGlmIHNjcmF0Y2ggaXMgbm90IE5vbmUgYW5kIHN0b3BwZWQ6CiAgICAgICAgc2h1dGlsLnJtdHJlZShzY3JhdGNoKQogICAgYWZ0ZXIgPSBtYW5pZmVzdCgpCiAgICB1bmNoYW5nZWQgPSBiZWZvcmUgPT0gYWZ0ZXIKICAgIChPVVQgLyAic291cmNlLW1hbmlmZXN0LWFmdGVyLmpzb24iKS53cml0ZV90ZXh0KGpzb24uZHVtcHMoYWZ0ZXIsIGluZGVudD0yKSArICJcbiIpCiAgICByZWNlaXB0ID0gewogICAgICAgICJzY2hlbWEiOiAyLCAidGltZV91dGMiOiBkYXRldGltZS5kYXRldGltZS5ub3coZGF0ZXRpbWUudGltZXpvbmUudXRjKS5pc29mb3JtYXQoKSwKICAgICAgICAiaGVhZCI6IHJldmlzaW9uLCAic291cmNlX21hbmlmZXN0IjogInNvdXJjZS1tYW5pZmVzdC5qc29uIiwKICAgICAgICAic291cmNlX21hbmlmZXN0X3NoYTI1NiI6IGRpZ2VzdChPVVQgLyAic291cmNlLW1hbmlmZXN0Lmpzb24iKSwKICAgICAgICAic291cmNlX3VuY2hhbmdlZCI6IHVuY2hhbmdlZCwgImNvbW1hbmRzIjogcmVjb3JkcywKICAgICAgICAiZm9jdXNlZF90ZXN0c19wYXNzZWQiOiBzdWNjZXNzIGFuZCB1bmNoYW5nZWQsCiAgICAgICAgImNsZWFudXAiOiB7Im93bmVkX3Bvc3RncmVzX3N0b3BwZWQiOiBzdG9wcGVkLCAib3duZWRfc2NyYXRjaF9yZW1vdmVkIjogc2NyYXRjaCBpcyBOb25lIG9yIG5vdCBzY3JhdGNoLmV4aXN0cygpfSwKICAgICAgICAic2NvcGUiOiAiU3ludGhldGljIGxvb3BiYWNrIFBvc3RncmVTUUw7IHNlbGVjdGVkIFN0b3JhZ2VTY2hlbWEvVmF1bHQvU3RvcmVkU25hcHNob3QgYW5kIG9yZGluYXJ5IDMvNC82LzcgbWlncmF0aW9ucyBhZ2FpbnN0IGV4aXN0aW5nIGRlcGVuZGVuY3kgYmVhbXMgb25seS4gTm8gd2hvbGUtYXBwIGNvbXBpbGUsIGZyb3plbiBsYW5lLCBicm93c2VyL25hdGl2ZS9wcm92aWRlci9wcm9kdWN0aW9uIGFjdGlvbi4iLAogICAgICAgICJwZW5kaW5nIjogWyJDdXJyZW50LXZlcmlmaWVyL09JREMvcHJvdmlkZXIgb3duZXIgam9pbiIsICJQcm9kdWN0aW9uIGxpZmVjeWNsZSBwb29sIGFuZCBjYXRhbG9nIGFkbWlzc2lvbiIsCiAgICAgICAgICAgICAgICAgICAgIk5lb24gb3duZXJzaGlwIHRyYW5zZmVyL3JvbGVzL1RMUy9rZXkgY3VzdG9keSIsICJOaW5lLW1pZ3JhdGlvbiBjb250cm9scyBpbnRlZ3JhdGVkIGJ5IHJvb3QiLAogICAgICAgICAgICAgICAgICAgICJDb21taXQvcmVzcG9uc2UgdW5jZXJ0YWludHkiLCAiUmV0ZW50aW9uIHNjaGVkdWxpbmciLCAiQnJvd3Nlci9uYXRpdmUvcGh5c2ljYWwgY2hlY2tzIHBhdXNlZCIsICJDdXN0b21lciBhbmQgR0EgcmV2aWV3Il19CiAgICAoT1VUIC8gInJlY2VpcHQuanNvbiIpLndyaXRlX3RleHQoanNvbi5kdW1wcyhyZWNlaXB0LCBpbmRlbnQ9MikgKyAiXG4iKQogICAgKEJBU0UgLyAibGF0ZXN0Lmpzb24iKS53cml0ZV90ZXh0KGpzb24uZHVtcHMoeyJtdXRhYmxlX3BvaW50ZXJfb25seSI6IFRydWUsICJhdHRlbXB0Ijogc3RyKE9VVC5yZWxhdGl2ZV90byhCQVNFKSksICJyZWNlaXB0Ijogc3RyKChPVVQgLyAicmVjZWlwdC5qc29uIikucmVsYXRpdmVfdG8oQkFTRSkpfSwgaW5kZW50PTIpICsgIlxuIikKICAgIHByaW50KHN0cihPVVQucmVsYXRpdmVfdG8oUkVQTykpKQppZiBub3Qgc3VjY2VzcyBvciBub3QgdW5jaGFuZ2VkIG9yIG5vdCBzdG9wcGVkOgogICAgcmFpc2UgU3lzdGVtRXhpdCgxKQo=","hosted/lib/mixer_hosted/identity/key_owner_supervisor.ex":"ZGVmbW9kdWxlIE1peGVySG9zdGVkLklkZW50aXR5LktleU93bmVyU3VwZXJ2aXNvciBkbwogIEBtb2R1bGVkb2MgIkV4cGxpY2l0bHkgY29uZmlndXJlZCBwcml2YXRlIGlkZW50aXR5IGNvbXBvbmVudDsgaXQgc3RhcnRzIG5vIHByb3ZpZGVyIGltcGxpY2l0bHkuIgogIHVzZSBTdXBlcnZpc29yCiAgYWxpYXMgTWl4ZXJIb3N0ZWQuSWRlbnRpdHkuS2V5T3duZXIKICBkZWYgc3RhcnRfbGluayhvcHRpb25zKSwgZG86IFN1cGVydmlzb3Iuc3RhcnRfbGluayhfX01PRFVMRV9fLCBvcHRpb25zKQoKICBpZiBNaXguZW52KCkgPT0gOnRlc3QgZG8KICAgIGRlZiBzdGFydF9maXh0dXJlKG9wdGlvbnMpLCBkbzogU3VwZXJ2aXNvci5zdGFydF9saW5rKF9fTU9EVUxFX18sIHs6Zml4dHVyZSwgb3B0aW9uc30pCiAgICBkZWYgaW5pdCh7OmZpeHR1cmUsIG9wdGlvbnN9KSwgZG86IGluaXRpYWxpemUob3B0aW9ucywgOnN0YXJ0X2ZpeHR1cmUpCiAgZW5kCgogIGRlZiBpbml0KG9wdGlvbnMpLCBkbzogaW5pdGlhbGl6ZShvcHRpb25zLCA6c3RhcnRfbGluaykKCiAgZGVmcCBpbml0aWFsaXplKG9wdGlvbnMsIG93bmVyX3N0YXJ0KSBkbwogICAgbmFtZSA9IEtleXdvcmQuZ2V0KG9wdGlvbnMsIDpuYW1lLCBLZXlPd25lcikKICAgIHdvcmtlcnMgPSBNb2R1bGUuY29uY2F0KG5hbWUsIEZldGNoU3VwZXJ2aXNvcikKICAgIG93bmVyX29wdGlvbnMgPSBLZXl3b3JkLnB1dChvcHRpb25zLCA6d29ya2VyX3N1cGVydmlzb3IsIHdvcmtlcnMpCiAgICBvd25lciA9IEtleU93bmVyLmNoaWxkX3NwZWMob3duZXJfb3B0aW9ucykKICAgIG93bmVyID0gJXtvd25lciB8IHN0YXJ0OiB7S2V5T3duZXIsIG93bmVyX3N0YXJ0LCBbb3duZXJfb3B0aW9uc119fQoKICAgIGNoaWxkcmVuID0gWwogICAgICB7RHluYW1pY1N1cGVydmlzb3IsIHN0cmF0ZWd5OiA6b25lX2Zvcl9vbmUsIG5hbWU6IHdvcmtlcnN9LAogICAgICBvd25lcgogICAgXQoKICAgIFN1cGVydmlzb3IuaW5pdChjaGlsZHJlbiwgc3RyYXRlZ3k6IDpvbmVfZm9yX2FsbCwgbWF4X3Jlc3RhcnRzOiAzLCBtYXhfc2Vjb25kczogNSkKICBlbmQKZW5kCg==","hosted/lib/mixer_hosted/browser_auth/store.ex":"ZGVmbW9kdWxlIE1peGVySG9zdGVkLkJyb3dzZXJBdXRoLlN0b3JlIGRvCiAgQG1vZHVsZWRvYyAiIiIKICBGaXhlZCBwcmVhdXRoZW50aWNhdGlvbiBzdG9yYWdlIG9wZXJhdGlvbnMgb24gdGhlIGRlZGljYXRlZCBsaWZlY3ljbGUgcG9vbC4KCiAgTm8gcmVxdWVzdC1zZWxlY3RlZCBSZXBvLCBjbG9jaywgY2FsbGJhY2ssIFNRTCBuYW1lIG9yIHByb3ZpZGVyIGlzIGFjY2VwdGVkLgogIFRoZSBpbnRlcm5hbCBvd25lciBtdXN0IHN0aWxsIGF1dGhlbnRpY2F0ZSBjaXBoZXJ0ZXh0IGFuZCBmZW5jZSBwcml2YXRlIHJlbGVhc2UKICBhZnRlciB0aGUgdHJhbnNhY3Rpb24uIEEgZGVjb2RlZCBzbmFwc2hvdCBhbG9uZSBncmFudHMgbm8gYXV0aGVudGljYXRpb24uCiAgIiIiCiAgYWxpYXMgTWl4ZXJIb3N0ZWQuQnJvd3NlckF1dGgue0FjdGl2ZUNhdGFsb2csIExpZmVjeWNsZVJlcG8sIFByZWF1dGhEcmFmdCwgUmVsYXRpb25DYXRhbG9nfQogIGFsaWFzIE1peGVySG9zdGVkLkJyb3dzZXJBdXRoLntQcm90b2NvbCwgUnVudGltZUNvbmZpZywgUnVudGltZU93bmVyLCBTdG9yZWRTbmFwc2hvdCwgVmF1bHR9CgogIGRlZm1vZHVsZSBGYWlsdXJlIGRvCiAgICBAbW9kdWxlZG9jICJDbG9zZWQgcHJpdmF0ZSBmYWlsdXJlIHdpdGhvdXQgZGF0YWJhc2UsIGlkZW50aXR5IG9yIHNlY3JldCBkZXRhaWxzLiIKICAgIEBlbmZvcmNlX2tleXMgWzpjb2RlLCA6cGhhc2UsIDpvdXRjb21lXQogICAgZGVmc3RydWN0IEBlbmZvcmNlX2tleXMKICBlbmQKCiAgQHBoYXNlIHtfX01PRFVMRV9fLCA6cGhhc2V9CiAgQG93bmVkIHtfX01PRFVMRV9fLCA6b3duZWR9CiAgQGVudGVyZWQge19fTU9EVUxFX18sIDplbnRlcmVkfQogIEByZWNlaXB0IHtfX01PRFVMRV9fLCA6cmVjZWlwdH0KICBAdHJhbnNhY3Rpb25fZXZlbnQgWzptaXhlcl9ob3N0ZWQsIDpicm93c2VyX2F1dGgsIDpzdG9yZSwgOnRyYW5zYWN0aW9uXQogIEBoYW5kbGVyIHtfX01PRFVMRV9fLCA6dHJhbnNhY3Rpb25fcmVjZWlwdH0KICBAb3JkaW5hcnlfY29udGV4dCB7TWl4ZXJIb3N0ZWQuQXV0aG9yaXphdGlvbi5UcmFuc2FjdGlvbi5Db250ZXh0LCA6YWN0aXZlfQoKICBAZG9jIGZhbHNlCiAgZGVmIGFkbWl0KCVSdW50aW1lQ29uZmlne21vZGU6IDpjb25maWd1cmVkfSA9IHJ1bnRpbWUsIGRlYWRsaW5lKSBkbwogICAgaWYgUHJvY2Vzcy53aGVyZWlzKFJ1bnRpbWVPd25lcikgPT09IHNlbGYoKSwKICAgICAgZG86IHRyYW5zYWN0KHJ1bnRpbWUsIGRlYWRsaW5lLCBuaWwsIDphZG1pdCksCiAgICAgIGVsc2U6IGZhaWx1cmUoOmFkbWlzc2lvbiwgOm5vdF9zdGFydGVkKQogIGVuZAoKICBkZWYgYWRtaXQoXywgXyksIGRvOiBmYWlsdXJlKDphZG1pc3Npb24sIDpub3Rfc3RhcnRlZCkKCiAgZGVmIGJvb3RzdHJhcCglUHJlYXV0aERyYWZ0LkJvb3RzdHJhcHt9ID0gZHJhZnQsIG1ldGFkYXRhKSBkbwogICAgd2l0aCB0cnVlIDwtIG1ldGFkYXRhPyhtZXRhZGF0YSksCiAgICAgICAgIDpvayA8LSBSdW50aW1lT3duZXIuY2hlY2twb2ludChkcmFmdC5sZWFzZSksCiAgICAgICAgIHRydWUgPC0gYm9vdHN0cmFwX2RyYWZ0PyhkcmFmdCkgZG8KICAgICAgdHJhbnNhY3QoCiAgICAgICAgZHJhZnQubGVhc2UucnVudGltZSwKICAgICAgICBkcmFmdC5sZWFzZS5kZWFkbGluZSwKICAgICAgICBkcmFmdC5sZWFzZSwKICAgICAgICB7OmJvb3RzdHJhcCwgZHJhZnQsIG1ldGFkYXRhfQogICAgICApCiAgICBlbHNlCiAgICAgIF8gLT4gZmFpbHVyZSg6YWRtaXNzaW9uLCA6bm90X3N0YXJ0ZWQpCiAgICBlbmQKICByZXNjdWUKICAgIF8gLT4gZmFpbHVyZSg6YWRtaXNzaW9uLCA6bm90X3N0YXJ0ZWQpCiAgY2F0Y2gKICAgIF8sIF8gLT4gZmFpbHVyZSg6YWRtaXNzaW9uLCA6bm90X3N0YXJ0ZWQpCiAgZW5kCgogIGRlZiBib290c3RyYXAoXywgXyksIGRvOiBmYWlsdXJlKDphZG1pc3Npb24sIDpub3Rfc3RhcnRlZCkKCiAgZGVmIGxvYWQoJVByZWF1dGhEcmFmdC5Mb2Fke2xlYXNlOiBsZWFzZSwgY29va2llX2RpZ2VzdDogZGlnZXN0fSA9IGlucHV0KSBkbwogICAgd2l0aCB0cnVlIDwtIG1hcF9zaXplKGlucHV0KSA9PSAzIGFuZCByYXc/KGRpZ2VzdCwgMzIpLAogICAgICAgICA6b2sgPC0gUnVudGltZU93bmVyLmNoZWNrcG9pbnQobGVhc2UpIGRvCiAgICAgIHRyYW5zYWN0KGxlYXNlLnJ1bnRpbWUsIGxlYXNlLmRlYWRsaW5lLCBsZWFzZSwgezpsb2FkLCBpbnB1dH0pCiAgICBlbHNlCiAgICAgIF8gLT4gZmFpbHVyZSg6YWRtaXNzaW9uLCA6bm90X3N0YXJ0ZWQpCiAgICBlbmQKICByZXNjdWUKICAgIF8gLT4gZmFpbHVyZSg6YWRtaXNzaW9uLCA6bm90X3N0YXJ0ZWQpCiAgY2F0Y2gKICAgIF8sIF8gLT4gZmFpbHVyZSg6YWRtaXNzaW9uLCA6bm90X3N0YXJ0ZWQpCiAgZW5kCgogIGRlZiBsb2FkKF8pLCBkbzogZmFpbHVyZSg6YWRtaXNzaW9uLCA6bm90X3N0YXJ0ZWQpCgogIGRlZiBkaXNjb3Zlcl9iZWdpbiglUHJlYXV0aERyYWZ0LkxvYWR7bGVhc2U6IGxlYXNlLCBjb29raWVfZGlnZXN0OiBkaWdlc3R9ID0gaW5wdXQpIGRvCiAgICB3aXRoIHRydWUgPC0gbWFwX3NpemUoaW5wdXQpID09IDMgYW5kIHJhdz8oZGlnZXN0LCAzMiksCiAgICAgICAgIDpvayA8LSBSdW50aW1lT3duZXIuY2hlY2twb2ludChsZWFzZSkgZG8KICAgICAgdHJhbnNhY3QobGVhc2UucnVudGltZSwgbGVhc2UuZGVhZGxpbmUsIGxlYXNlLCB7OmRpc2NvdmVyX2JlZ2luLCBpbnB1dH0pCiAgICBlbHNlCiAgICAgIF8gLT4gZmFpbHVyZSg6YWRtaXNzaW9uLCA6bm90X3N0YXJ0ZWQpCiAgICBlbmQKICByZXNjdWUKICAgIF8gLT4gZmFpbHVyZSg6YWRtaXNzaW9uLCA6bm90X3N0YXJ0ZWQpCiAgY2F0Y2gKICAgIF8sIF8gLT4gZmFpbHVyZSg6YWRtaXNzaW9uLCA6bm90X3N0YXJ0ZWQpCiAgZW5kCgogIGRlZiBkaXNjb3Zlcl9iZWdpbihfKSwgZG86IGZhaWx1cmUoOmFkbWlzc2lvbiwgOm5vdF9zdGFydGVkKQoKICBkZWYgYmVnaW5fbG9naW4oJVByZWF1dGhEcmFmdC5CZWdpbnt9ID0gZHJhZnQsIG1ldGFkYXRhKSBkbwogICAgd2l0aCB0cnVlIDwtIG1ldGFkYXRhPyhtZXRhZGF0YSksCiAgICAgICAgIDpvayA8LSBSdW50aW1lT3duZXIuY2hlY2twb2ludChkcmFmdC5sZWFzZSksCiAgICAgICAgIHRydWUgPC0gYmVnaW5fZHJhZnQ/KGRyYWZ0KSwKICAgICAgICAgOm9rIDwtIFJ1bnRpbWVPd25lci5jaGVja3BvaW50KGRyYWZ0LmxlYXNlKSBkbwogICAgICB0cmFuc2FjdChkcmFmdC5sZWFzZS5ydW50aW1lLCBkcmFmdC5sZWFzZS5kZWFkbGluZSwgZHJhZnQubGVhc2UsIHs6YmVnaW4sIGRyYWZ0LCBtZXRhZGF0YX0pCiAgICBlbHNlCiAgICAgIF8gLT4gZmFpbHVyZSg6YWRtaXNzaW9uLCA6bm90X3N0YXJ0ZWQpCiAgICBlbmQKICByZXNjdWUKICAgIF8gLT4gZmFpbHVyZSg6YWRtaXNzaW9uLCA6bm90X3N0YXJ0ZWQpCiAgY2F0Y2gKICAgIF8sIF8gLT4gZmFpbHVyZSg6YWRtaXNzaW9uLCA6bm90X3N0YXJ0ZWQpCiAgZW5kCgogIGRlZiBiZWdpbl9sb2dpbihfLCBfKSwgZG86IGZhaWx1cmUoOmFkbWlzc2lvbiwgOm5vdF9zdGFydGVkKQoKICBAZG9jIGZhbHNlCiAgZGVmIGxpZmVjeWNsZSglUHJlYXV0aERyYWZ0LkxlYXNle30gPSBsZWFzZSwgb3BlcmF0aW9uKSBkbwogICAgd2l0aCA6b2sgPC0gUnVudGltZU93bmVyLmNoZWNrcG9pbnQobGVhc2UpLAogICAgICAgICB0cnVlIDwtIE1peGVySG9zdGVkLkJyb3dzZXJBdXRoLkNhbGxiYWNrU3RvcmUudmFsaWQ/KGxlYXNlLCBvcGVyYXRpb24pIGRvCiAgICAgIHRyYW5zYWN0KGxlYXNlLnJ1bnRpbWUsIGxlYXNlLmRlYWRsaW5lLCBsZWFzZSwgezpsaWZlY3ljbGUsIG9wZXJhdGlvbn0pCiAgICBlbHNlCiAgICAgIF8gLT4gZmFpbHVyZSg6YWRtaXNzaW9uLCA6bm90X3N0YXJ0ZWQpCiAgICBlbmQKICByZXNjdWUKICAgIF8gLT4gZmFpbHVyZSg6YWRtaXNzaW9uLCA6bm90X3N0YXJ0ZWQpCiAgY2F0Y2gKICAgIF8sIF8gLT4gZmFpbHVyZSg6YWRtaXNzaW9uLCA6bm90X3N0YXJ0ZWQpCiAgZW5kCgogIGRlZiBsaWZlY3ljbGUoXywgXyksIGRvOiBmYWlsdXJlKDphZG1pc3Npb24sIDpub3Rfc3RhcnRlZCkKCiAgQGRvYyBmYWxzZQogIGRlZiBhY3RpdmVfcmVhZChsZWFzZSwgb3BlcmF0aW9uKSBkbwogICAgd2l0aCA6b2sgPC0gUnVudGltZU93bmVyLmNoZWNrcG9pbnQobGVhc2UpLAogICAgICAgICB0cnVlIDwtIE1peGVySG9zdGVkLkJyb3dzZXJBdXRoLkFjdGl2ZVJlYWQudmFsaWQ/KGxlYXNlLCBvcGVyYXRpb24pIGRvCiAgICAgIHRyYW5zYWN0KGxlYXNlLnJ1bnRpbWUsIGxlYXNlLmRlYWRsaW5lLCBsZWFzZSwgezphY3RpdmVfcmVhZCwgb3BlcmF0aW9ufSkKICAgIGVsc2UKICAgICAgXyAtPiBmYWlsdXJlKDphZG1pc3Npb24sIDpub3Rfc3RhcnRlZCkKICAgIGVuZAogIHJlc2N1ZQogICAgXyAtPiBmYWlsdXJlKDphZG1pc3Npb24sIDpub3Rfc3RhcnRlZCkKICBlbmQKCiAgQGRvYyBmYWxzZQogIGRlZiBmYWlsdXJlKHBoYXNlLCBvdXRjb21lKSwKICAgIGRvOiB7OmVycm9yLCAlRmFpbHVyZXtjb2RlOiA6c2Vzc2lvbl91bmF2YWlsYWJsZSwgcGhhc2U6IHBoYXNlLCBvdXRjb21lOiBvdXRjb21lfX0KCiAgZGVmcCByZWxhdGlvbl9hZG1pc3Npb24hKAogICAgICAgICAlUnVudGltZUNvbmZpZ3thZG1pc3Npb25fcHJvZmlsZTogOmJyb3dzZXJfYXV0aF92Mn0gPSBydW50aW1lLAogICAgICAgICBkZWFkbGluZQogICAgICAgKSwKICAgICAgIGRvOgogICAgICAgICBSZWxhdGlvbkNhdGFsb2cuY2hlY2tfcmVsYXRpb25fc3VyZmFjZSEoTGlmZWN5Y2xlUmVwbywgcnVudGltZS5leHBlY3RlZF9yb2xlcywgZGVhZGxpbmUpCgogIGRlZnAgcmVsYXRpb25fYWRtaXNzaW9uISgKICAgICAgICAgJVJ1bnRpbWVDb25maWd7YWRtaXNzaW9uX3Byb2ZpbGU6IDpidWlsZF9jYXRhbG9nX3YzfSA9IHJ1bnRpbWUsCiAgICAgICAgIGRlYWRsaW5lCiAgICAgICApIGRvCiAgICA6cmVsYXRpb25fc3VyZmFjZV92ZXJpZmllZCA9CiAgICAgIFJlbGF0aW9uQ2F0YWxvZy5jaGVja19idWlsZF9jYXRhbG9nX3N1cmZhY2UhKAogICAgICAgIExpZmVjeWNsZVJlcG8sCiAgICAgICAgcnVudGltZS5leHBlY3RlZF9yb2xlcywKICAgICAgICBkZWFkbGluZQogICAgICApCgogICAgOm9rID0KICAgICAgTWl4ZXJIb3N0ZWQuQnJvd3NlckF1dGguQnVpbGRDYXRhbG9nQWRtaXNzaW9uLmNoZWNrISgKICAgICAgICBMaWZlY3ljbGVSZXBvLAogICAgICAgIHJ1bnRpbWUuZXhwZWN0ZWRfcm9sZXMsCiAgICAgICAgZGVhZGxpbmUKICAgICAgKQoKICAgIDpyZWxhdGlvbl9zdXJmYWNlX3ZlcmlmaWVkCiAgZW5kCgogIGRlZnAgcmVsYXRpb25fYWRtaXNzaW9uIShfLCBfKSwgZG86IHJhaXNlKFJlbGF0aW9uQ2F0YWxvZy5VbmF2YWlsYWJsZSkKCiAgZGVmcCB0cmFuc2FjdChydW50aW1lLCBkZWFkbGluZSwgbGVhc2UsIG9wZXJhdGlvbikgZG8KICAgIHdpdGggdHJ1ZSA8LSBub3QgUHJvY2Vzcy5nZXQoQG93bmVkLCBmYWxzZSksCiAgICAgICAgIHRydWUgPC0gaXNfbmlsKFByb2Nlc3MuZ2V0KEBvcmRpbmFyeV9jb250ZXh0KSksCiAgICAgICAgIHRydWUgPC0gTGlmZWN5Y2xlUmVwby5nZXRfZHluYW1pY19yZXBvKCkgPT09IExpZmVjeWNsZVJlcG8sCiAgICAgICAgIHRydWUgPC0gTWl4ZXJIb3N0ZWQuUmVwby5nZXRfZHluYW1pY19yZXBvKCkgPT09IE1peGVySG9zdGVkLlJlcG8sCiAgICAgICAgIGZhbHNlIDwtIExpZmVjeWNsZVJlcG8uaW5fdHJhbnNhY3Rpb24/KCksCiAgICAgICAgIGZhbHNlIDwtIE1peGVySG9zdGVkLlJlcG8uaW5fdHJhbnNhY3Rpb24/KCksCiAgICAgICAgIHJlbWFpbmluZyA8LSByZW1haW5pbmchKGRlYWRsaW5lKSBkbwogICAgICBQcm9jZXNzLnB1dChAb3duZWQsIHRydWUpCiAgICAgIFByb2Nlc3MucHV0KEBwaGFzZSwgOmFkbWlzc2lvbikKICAgICAgUHJvY2Vzcy5wdXQoQGVudGVyZWQsIGZhbHNlKQoKICAgICAgdHJ5IGRvCiAgICAgICAgOm9rID0gZW5zdXJlX3JlY2VpcHRfaGFuZGxlcigpCiAgICAgICAgcmVmZXJlbmNlID0gbWFrZV9yZWYoKQogICAgICAgIFByb2Nlc3MucHV0KEByZWNlaXB0LCB7c2VsZigpLCByZWZlcmVuY2UsIDphd2FpdF9iZWdpbn0pCiAgICAgICAgUHJvY2Vzcy5wdXQoQGVudGVyZWQsIHRydWUpCgogICAgICAgIHJlc3VsdCA9CiAgICAgICAgICBMaWZlY3ljbGVSZXBvLnRyYW5zYWN0aW9uKAogICAgICAgICAgICBmbiAtPgogICAgICAgICAgICAgIHRyeSBkbwogICAgICAgICAgICAgICAgcG9saWN5IShkZWFkbGluZSkKCiAgICAgICAgICAgICAgICA6ZnVuY3Rpb25fc3VyZmFjZV92ZXJpZmllZCA9CiAgICAgICAgICAgICAgICAgIEFjdGl2ZUNhdGFsb2cuY2hlY2tfZnVuY3Rpb25fc3VyZmFjZSEoCiAgICAgICAgICAgICAgICAgICAgTGlmZWN5Y2xlUmVwbywKICAgICAgICAgICAgICAgICAgICBydW50aW1lLmV4cGVjdGVkX3JvbGVzLAogICAgICAgICAgICAgICAgICAgIGRlYWRsaW5lLAogICAgICAgICAgICAgICAgICAgIDIKICAgICAgICAgICAgICAgICAgKQoKICAgICAgICAgICAgICAgIDpyZWxhdGlvbl9zdXJmYWNlX3ZlcmlmaWVkID0gcmVsYXRpb25fYWRtaXNzaW9uIShydW50aW1lLCBkZWFkbGluZSkKCiAgICAgICAgICAgICAgICBjaGVja3BvaW50IShsZWFzZSwgZGVhZGxpbmUpCiAgICAgICAgICAgICAgICBQcm9jZXNzLnB1dChAcGhhc2UsIDplZmZlY3QpCiAgICAgICAgICAgICAgICByYXcgPSBlZmZlY3QhKG9wZXJhdGlvbiwgZGVhZGxpbmUpCiAgICAgICAgICAgICAgICBQcm9jZXNzLnB1dChAcGhhc2UsIDpkZWNvZGUpCiAgICAgICAgICAgICAgICB2YWx1ZSA9IGRlY29kZSEob3BlcmF0aW9uLCByYXcpCiAgICAgICAgICAgICAgICBjaGVja3BvaW50IShsZWFzZSwgZGVhZGxpbmUpCiAgICAgICAgICAgICAgICBQcm9jZXNzLnB1dChAcGhhc2UsIDpjb21taXQpCiAgICAgICAgICAgICAgICB2YWx1ZQogICAgICAgICAgICAgIHJlc2N1ZQogICAgICAgICAgICAgICAgXyAtPiByb2xsYmFjayEoKQogICAgICAgICAgICAgIGNhdGNoCiAgICAgICAgICAgICAgICBfLCBfIC0+IHJvbGxiYWNrISgpCiAgICAgICAgICAgICAgZW5kCiAgICAgICAgICAgIGVuZCwKICAgICAgICAgICAgdGltZW91dDogcmVtYWluaW5nLAogICAgICAgICAgICBkZWFkbGluZTogZGVhZGxpbmUsCiAgICAgICAgICAgIHF1ZXVlOiBmYWxzZSwKICAgICAgICAgICAgbG9nOiBmYWxzZSwKICAgICAgICAgICAgdGVsZW1ldHJ5X2V2ZW50OiBAdHJhbnNhY3Rpb25fZXZlbnQsCiAgICAgICAgICAgIHRlbGVtZXRyeV9vcHRpb25zOiBbc3RvcmVfdHJhbnNhY3Rpb246IHtzZWxmKCksIHJlZmVyZW5jZX1dCiAgICAgICAgICApCgogICAgICAgIGNhc2Uge3Jlc3VsdCwgcmVjZWlwdF9vdXRjb21lKCl9IGRvCiAgICAgICAgICB7ezpvaywgdmFsdWV9LCA6Y29tbWl0dGVkfSAtPgogICAgICAgICAgICAjIERCQ29ubmVjdGlvbidzIGFic29sdXRlIGRlYWRsaW5lIGFsc28gY292ZXJzIENPTU1JVC4gVGhpcyBmaW5hbAogICAgICAgICAgICAjIGNoZWNrIGNhbiB3aXRoaG9sZCBhIGtub3duIGNvbW1pdHRlZCByZXN1bHQsIG5ldmVyIHJlc3VycmVjdCBpdC4KICAgICAgICAgICAgdHJ5IGRvCiAgICAgICAgICAgICAgY2hlY2twb2ludCEobGVhc2UsIGRlYWRsaW5lKQogICAgICAgICAgICAgIHs6b2ssIHZhbHVlfQogICAgICAgICAgICByZXNjdWUKICAgICAgICAgICAgICBfIC0+IGZhaWx1cmUoOmNvbW1pdCwgOmNvbW1pdHRlZCkKICAgICAgICAgICAgY2F0Y2gKICAgICAgICAgICAgICBfLCBfIC0+IGZhaWx1cmUoOmNvbW1pdCwgOmNvbW1pdHRlZCkKICAgICAgICAgICAgZW5kCgogICAgICAgICAge3s6ZXJyb3IsICVGYWlsdXJle30gPSBlcnJvcn0sIG91dGNvbWV9IC0+CiAgICAgICAgICAgIGZhaWx1cmUoZXJyb3IucGhhc2UsIG91dGNvbWUpCgogICAgICAgICAge18sIG91dGNvbWV9IC0+CiAgICAgICAgICAgIGZhaWx1cmUoOmNvbW1pdCwgb3V0Y29tZSkKICAgICAgICBlbmQKICAgICAgcmVzY3VlCiAgICAgICAgXyAtPgogICAgICAgICAgZmFpbHVyZShQcm9jZXNzLmdldChAcGhhc2UsIDphZG1pc3Npb24pLCB1bmNlcnRhaW5fb3V0Y29tZSgpKQogICAgICBjYXRjaAogICAgICAgIF8sIF8gLT4gZmFpbHVyZShQcm9jZXNzLmdldChAcGhhc2UsIDphZG1pc3Npb24pLCB1bmNlcnRhaW5fb3V0Y29tZSgpKQogICAgICBhZnRlcgogICAgICAgIFByb2Nlc3MuZGVsZXRlKEByZWNlaXB0KQogICAgICAgIFByb2Nlc3MuZGVsZXRlKEBlbnRlcmVkKQogICAgICAgIFByb2Nlc3MuZGVsZXRlKEBwaGFzZSkKICAgICAgICBQcm9jZXNzLmRlbGV0ZShAb3duZWQpCiAgICAgIGVuZAogICAgZWxzZQogICAgICBfIC0+IGZhaWx1cmUoOmFkbWlzc2lvbiwgOm5vdF9zdGFydGVkKQogICAgZW5kCiAgcmVzY3VlCiAgICBfIC0+IGZhaWx1cmUoOmFkbWlzc2lvbiwgOm5vdF9zdGFydGVkKQogIGNhdGNoCiAgICBfLCBfIC0+IGZhaWx1cmUoOmFkbWlzc2lvbiwgOm5vdF9zdGFydGVkKQogIGVuZAoKICAjIEVjdG8gZW1pdHMgdHJhbnNhY3Rpb24tbWFuYWdlbWVudCBxdWVyeSByZXN1bHRzIHN5bmNocm9ub3VzbHkgaW4gdGhpcyBjYWxsZXIuCiAgIyBLZWVwIG9uZSBmaXhlZCBoYW5kbGVyOyBraWxsaW5nIGEgY2FsbGVyIGNhbm5vdCByZXRhaW4gaXRzIFBJRCBvciByZWZlcmVuY2UgZ2xvYmFsbHkuCiAgZGVmcCBlbnN1cmVfcmVjZWlwdF9oYW5kbGVyIGRvCiAgICBoYW5kbGVyID0gJl9fTU9EVUxFX18udHJhbnNhY3Rpb25fZXZlbnQvNAoKICAgIGNhc2UgOnRlbGVtZXRyeS5hdHRhY2goQGhhbmRsZXIsIEB0cmFuc2FjdGlvbl9ldmVudCwgaGFuZGxlciwgbmlsKSBkbwogICAgICA6b2sgLT4KICAgICAgICA6b2sKCiAgICAgIHs6ZXJyb3IsIDphbHJlYWR5X2V4aXN0c30gLT4KICAgICAgICB0cnVlID0KICAgICAgICAgIEVudW0uYW55Pyg6dGVsZW1ldHJ5Lmxpc3RfaGFuZGxlcnMoQHRyYW5zYWN0aW9uX2V2ZW50KSwgZm4gZW50cnkgLT4KICAgICAgICAgICAgZW50cnkuaWQgPT09IEBoYW5kbGVyIGFuZCBlbnRyeS5mdW5jdGlvbiA9PT0gaGFuZGxlciBhbmQgZW50cnkuY29uZmlnID09PSBuaWwKICAgICAgICAgIGVuZCkKCiAgICAgICAgOm9rCiAgICBlbmQKICBlbmQKCiAgQGRvYyBmYWxzZQogIGRlZiB0cmFuc2FjdGlvbl9ldmVudChAdHJhbnNhY3Rpb25fZXZlbnQsIF8sIG1ldGFkYXRhLCBuaWwpIGRvCiAgICBjYXNlIFByb2Nlc3MuZ2V0KEByZWNlaXB0KSBkbwogICAgICB7Y2FsbGVyLCByZWZlcmVuY2UsIHN0YXRlfSB3aGVuIGNhbGxlciA9PSBzZWxmKCkgLT4KICAgICAgICBuZXh0ID0KICAgICAgICAgIGNhc2UgbWV0YWRhdGEgZG8KICAgICAgICAgICAgJXsKICAgICAgICAgICAgICB0eXBlOiA6ZWN0b19zcWxfcXVlcnksCiAgICAgICAgICAgICAgcmVwbzogTGlmZWN5Y2xlUmVwbywKICAgICAgICAgICAgICBvcHRpb25zOiBbc3RvcmVfdHJhbnNhY3Rpb246IHteY2FsbGVyLCBecmVmZXJlbmNlfV0sCiAgICAgICAgICAgICAgcXVlcnk6IHF1ZXJ5LAogICAgICAgICAgICAgIHJlc3VsdDogcmVzdWx0CiAgICAgICAgICAgIH0gLT4KICAgICAgICAgICAgICBhZHZhbmNlX3JlY2VpcHQoc3RhdGUsIHF1ZXJ5LCByZXN1bHQpCgogICAgICAgICAgICBfIC0+CiAgICAgICAgICAgICAgOnVua25vd24KICAgICAgICAgIGVuZAoKICAgICAgICBQcm9jZXNzLnB1dChAcmVjZWlwdCwge2NhbGxlciwgcmVmZXJlbmNlLCBuZXh0fSkKCiAgICAgIF8gLT4KICAgICAgICA6b2sKICAgIGVuZAoKICAgIDpvawogIGVuZAoKICBkZWZwIGFkdmFuY2VfcmVjZWlwdCgKICAgICAgICAgOmF3YWl0X2JlZ2luLAogICAgICAgICAiYmVnaW4iLAogICAgICAgICB7Om9rLCAlUG9zdGdyZXguUmVzdWx0e2NvbW1hbmQ6IDpiZWdpbiwgY29ubmVjdGlvbl9pZDogaWR9fQogICAgICAgKQogICAgICAgd2hlbiBpc19pbnRlZ2VyKGlkKSBhbmQgaWQgPiAwLCBkbzogezpiZWd1biwgaWR9CgogIGRlZnAgYWR2YW5jZV9yZWNlaXB0KAogICAgICAgICB7OmJlZ3VuLCBpZH0sCiAgICAgICAgICJjb21taXQiLAogICAgICAgICB7Om9rLCAlUG9zdGdyZXguUmVzdWx0e2NvbW1hbmQ6IDpjb21taXQsIGNvbm5lY3Rpb25faWQ6IGlkfX0KICAgICAgICksCiAgICAgICBkbzogOmNvbW1pdHRlZAoKICBkZWZwIGFkdmFuY2VfcmVjZWlwdCgKICAgICAgICAgezpiZWd1biwgaWR9LAogICAgICAgICBxdWVyeSwKICAgICAgICAgezpvaywgJVBvc3RncmV4LlJlc3VsdHtjb21tYW5kOiA6cm9sbGJhY2ssIGNvbm5lY3Rpb25faWQ6IGlkfX0KICAgICAgICkKICAgICAgIHdoZW4gcXVlcnkgaW4gWyJjb21taXQiLCAicm9sbGJhY2siXSwgZG86IDpyb2xsZWRfYmFjawoKICBkZWZwIGFkdmFuY2VfcmVjZWlwdChfLCBfLCBfKSwgZG86IDp1bmtub3duCgogIGRlZnAgcmVjZWlwdF9vdXRjb21lIGRvCiAgICBjYXNlIFByb2Nlc3MuZ2V0KEByZWNlaXB0KSBkbwogICAgICB7XywgXywgb3V0Y29tZX0gd2hlbiBvdXRjb21lIGluIFs6Y29tbWl0dGVkLCA6cm9sbGVkX2JhY2tdIC0+IG91dGNvbWUKICAgICAgXyAtPiA6dW5rbm93bgogICAgZW5kCiAgZW5kCgogIGRlZnAgdW5jZXJ0YWluX291dGNvbWUsCiAgICBkbzogaWYoUHJvY2Vzcy5nZXQoQGVudGVyZWQsIGZhbHNlKSwgZG86IHJlY2VpcHRfb3V0Y29tZSgpLCBlbHNlOiA6bm90X3N0YXJ0ZWQpCgogIGRlZnAgcm9sbGJhY2shIGRvCiAgICB7OmVycm9yLCBlcnJvcn0gPSBmYWlsdXJlKFByb2Nlc3MuZ2V0KEBwaGFzZSwgOmFkbWlzc2lvbiksIDpyb2xsZWRfYmFjaykKICAgIExpZmVjeWNsZVJlcG8ucm9sbGJhY2soZXJyb3IpCiAgZW5kCgogIGRlZnAgcG9saWN5IShkZWFkbGluZSkgZG8KICAgIHF1ZXJ5ISgiU0VUIFRSQU5TQUNUSU9OIElTT0xBVElPTiBMRVZFTCBSRUFEIENPTU1JVFRFRCIsIFtdLCBkZWFkbGluZSkKCiAgICAle3Jvd3M6IFtbInBnX2NhdGFsb2ciLCAib2ZmIiwgIjVzIiwgIjUwMG1zIiwgIjVzIiwgImhleCJdXSwgbnVtX3Jvd3M6IDF9ID0KICAgICAgcXVlcnkhKAogICAgICAgICIiIgogICAgICAgIFNFTEVDVCBwZ19jYXRhbG9nLnNldF9jb25maWcoJ3NlYXJjaF9wYXRoJywncGdfY2F0YWxvZycsdHJ1ZSksCiAgICAgICAgICBwZ19jYXRhbG9nLnNldF9jb25maWcoJ2ppdCcsJ29mZicsdHJ1ZSksCiAgICAgICAgICBwZ19jYXRhbG9nLnNldF9jb25maWcoJ3N0YXRlbWVudF90aW1lb3V0JywnNXMnLHRydWUpLAogICAgICAgICAgcGdfY2F0YWxvZy5zZXRfY29uZmlnKCdsb2NrX3RpbWVvdXQnLCc1MDBtcycsdHJ1ZSksCiAgICAgICAgICBwZ19jYXRhbG9nLnNldF9jb25maWcoJ2lkbGVfaW5fdHJhbnNhY3Rpb25fc2Vzc2lvbl90aW1lb3V0JywnNXMnLHRydWUpLAogICAgICAgICAgcGdfY2F0YWxvZy5zZXRfY29uZmlnKCdieXRlYV9vdXRwdXQnLCdoZXgnLHRydWUpCiAgICAgICAgIiIiLAogICAgICAgIFtdLAogICAgICAgIGRlYWRsaW5lCiAgICAgICkKICBlbmQKCiAgZGVmcCBxdWVyeSEoc3FsLCBwYXJhbXMsIGRlYWRsaW5lKSBkbwogICAgcmVzdWx0ID0KICAgICAgRWN0by5BZGFwdGVycy5TUUwucXVlcnkhKExpZmVjeWNsZVJlcG8sIHNxbCwgcGFyYW1zLAogICAgICAgIHRpbWVvdXQ6IHJlbWFpbmluZyEoZGVhZGxpbmUpLAogICAgICAgIGRlYWRsaW5lOiBkZWFkbGluZSwKICAgICAgICBxdWV1ZTogZmFsc2UsCiAgICAgICAgbG9nOiBmYWxzZSwKICAgICAgICB0ZWxlbWV0cnlfZXZlbnQ6IG5pbAogICAgICApCgogICAgcmVtYWluaW5nIShkZWFkbGluZSkKICAgIHJlc3VsdAogIGVuZAoKICBkZWZwIGVmZmVjdCEoezphY3RpdmVfcmVhZCwgb3BlcmF0aW9ufSwgZGVhZGxpbmUpLAogICAgZG86IE1peGVySG9zdGVkLkJyb3dzZXJBdXRoLkFjdGl2ZVJlYWQuZWZmZWN0IShvcGVyYXRpb24sIGRlYWRsaW5lKQoKICBkZWZwIGVmZmVjdCEoezpsaWZlY3ljbGUsIG9wZXJhdGlvbn0sIGRlYWRsaW5lKSwKICAgIGRvOiBNaXhlckhvc3RlZC5Ccm93c2VyQXV0aC5DYWxsYmFja1N0b3JlLmVmZmVjdCEob3BlcmF0aW9uLCBkZWFkbGluZSkKCiAgZGVmcCBlZmZlY3QhKDphZG1pdCwgX2RlYWRsaW5lKSwgZG86IDphZG1pdHRlZAoKICBkZWZwIGVmZmVjdCEoezpib290c3RyYXAsIGQsIG1ldGFkYXRhfSwgZGVhZGxpbmUpIGRvCiAgICBjID0gZC5jb250ZXh0CiAgICBzID0gZC5zZWFsZWQKCiAgICBzbmFwc2hvdCEoCiAgICAgIHF1ZXJ5ISgKICAgICAgICAiIiIKICAgICAgICBTRUxFQ1QgcHVibGljLm1peGVyX2Jyb3dzZXJfYm9vdHN0cmFwKCQxOjpieXRlYSwkMjo6Ynl0ZWEsJDM6OnRleHQsJDQ6OmJ5dGVhLAogICAgICAgICAgJDU6OmJ5dGVhLCQ2Ojp0ZXh0LCQ3OjppbnRlZ2VyLCQ4OjpiaWdpbnQsCiAgICAgICAgICBST1coJDk6OnRleHQsJDEwOjpieXRlYSwkMTE6OmJ5dGVhLCQxMjo6Ynl0ZWEpOjpwdWJsaWMubWl4ZXJfYnJvd3Nlcl9jaXBoZXIsCiAgICAgICAgICAkMTM6OnRleHQpIEFTIHNuYXBzaG90CiAgICAgICAgIiIiLAogICAgICAgIFsKICAgICAgICAgIGMuYnJvd3Nlcl9pZCwKICAgICAgICAgIGMuY29va2llX2RpZ2VzdCwKICAgICAgICAgIGMuZ2VuZXJhdGlvbiwKICAgICAgICAgIGMuY3NyZl9kaWdlc3QsCiAgICAgICAgICBjLmNvbmZpZ19kaWdlc3QsCiAgICAgICAgICBjLnByb2ZpbGVfaWQsCiAgICAgICAgICBjLnByb2ZpbGVfdmVyc2lvbiwKICAgICAgICAgIGQuZXhwaXJlc19hdCwKICAgICAgICAgIHMua2V5X2lkLAogICAgICAgICAgcy5pdiwKICAgICAgICAgIHMudGFnLAogICAgICAgICAgcy5jaXBoZXJ0ZXh0LAogICAgICAgICAgbWV0YWRhdGEucmVxdWVzdF9pZAogICAgICAgIF0sCiAgICAgICAgZGVhZGxpbmUKICAgICAgKQogICAgKQogIGVuZAoKICBkZWZwIGVmZmVjdCEoe29wZXJhdGlvbiwgaW5wdXR9LCBkZWFkbGluZSkgd2hlbiBvcGVyYXRpb24gaW4gWzpsb2FkLCA6ZGlzY292ZXJfYmVnaW5dIGRvCiAgICBzbmFwc2hvdCEoCiAgICAgIHF1ZXJ5ISgKICAgICAgICAiIiIKICAgICAgICBTRUxFQ1QgcHVibGljLm1peGVyX2Jyb3dzZXJfbG9hZCgkMTo6Ynl0ZWEsJDI6OmJ5dGVhKSBBUyBzbmFwc2hvdAogICAgICAgICIiIiwKICAgICAgICBbaW5wdXQuY29va2llX2RpZ2VzdCwgaW5wdXQubGVhc2UucnVudGltZS5jb25maWd1cmF0aW9uX2RpZ2VzdF0sCiAgICAgICAgZGVhZGxpbmUKICAgICAgKQogICAgKQogIGVuZAoKICBkZWZwIGVmZmVjdCEoezpiZWdpbiwgZCwgbWV0YWRhdGF9LCBkZWFkbGluZSkgZG8KICAgIGMgPSBkLmNvbnRleHQKICAgIGEgPSBkLmF0dGVtcHRfY29udGV4dAogICAgcyA9IGQuc2VhbGVkCiAgICB2ID0gZC5hdHRlbXB0X3NlYWxlZAoKICAgIHNuYXBzaG90ISgKICAgICAgcXVlcnkhKAogICAgICAgICIiIgogICAgICAgIFNFTEVDVCBwdWJsaWMubWl4ZXJfYnJvd3Nlcl9iZWdpbigkMTo6Ynl0ZWEsJDI6OmJ5dGVhLCQzOjpieXRlYSwkNDo6YmlnaW50LAogICAgICAgICAgUk9XKCQ1OjpieXRlYSwkNjo6Ynl0ZWEsJDc6OnRleHQsJDg6OmludGVnZXIsJDk6OnRleHQsJDEwOjp0ZXh0LCQxMTo6dGV4dCwkMTI6OmJpZ2ludCwKICAgICAgICAgICAgUk9XKCQxMzo6dGV4dCwkMTQ6OmJ5dGVhLCQxNTo6Ynl0ZWEsJDE2OjpieXRlYSk6OnB1YmxpYy5taXhlcl9icm93c2VyX2NpcGhlcik6OnB1YmxpYy5taXhlcl9icm93c2VyX2F0dGVtcHQsCiAgICAgICAgICBST1coJDE3Ojp0ZXh0LCQxODo6Ynl0ZWEsJDE5OjpieXRlYSwkMjA6OmJ5dGVhKTo6cHVibGljLm1peGVyX2Jyb3dzZXJfY2lwaGVyLCQyMTo6dGV4dCkgQVMgc25hcHNob3QKICAgICAgICAiIiIsCiAgICAgICAgWwogICAgICAgICAgYy5jb29raWVfZGlnZXN0LAogICAgICAgICAgYy5jc3JmX2RpZ2VzdCwKICAgICAgICAgIGMuY29uZmlnX2RpZ2VzdCwKICAgICAgICAgIGQuc291cmNlLmJyb3dzZXJbInJldmlzaW9uIl0sCiAgICAgICAgICBhLnN0YXRlX2RpZ2VzdCwKICAgICAgICAgIDpjcnlwdG8uaGFzaCg6c2hhMjU2LCBkLm5vbmNlKSwKICAgICAgICAgIGEucHJvZmlsZV9pZCwKICAgICAgICAgIGEucHJvZmlsZV92ZXJzaW9uLAogICAgICAgICAgYS5pc3N1ZXIsCiAgICAgICAgICBhLmNsaWVudF9pZCwKICAgICAgICAgIGEucmVkaXJlY3RfdXJpLAogICAgICAgICAgYS5leHBpcmVzX2F0LAogICAgICAgICAgdi5rZXlfaWQsCiAgICAgICAgICB2Lml2LAogICAgICAgICAgdi50YWcsCiAgICAgICAgICB2LmNpcGhlcnRleHQsCiAgICAgICAgICBzLmtleV9pZCwKICAgICAgICAgIHMuaXYsCiAgICAgICAgICBzLnRhZywKICAgICAgICAgIHMuY2lwaGVydGV4dCwKICAgICAgICAgIG1ldGFkYXRhLnJlcXVlc3RfaWQKICAgICAgICBdLAogICAgICAgIGRlYWRsaW5lCiAgICAgICkKICAgICkKICBlbmQKCiAgZGVmcCBzbmFwc2hvdCEoJVBvc3RncmV4LlJlc3VsdHsKICAgICAgICAgY29tbWFuZDogOnNlbGVjdCwKICAgICAgICAgY29sdW1uczogWyJzbmFwc2hvdCJdLAogICAgICAgICByb3dzOiBbW3Jhd11dLAogICAgICAgICBudW1fcm93czogMSwKICAgICAgICAgbWVzc2FnZXM6IFtdCiAgICAgICB9KSwKICAgICAgIGRvOiByYXcKCiAgZGVmcCBkZWNvZGUhKHs6YWN0aXZlX3JlYWQsIG9wZXJhdGlvbn0sIHJhdyksCiAgICBkbzogTWl4ZXJIb3N0ZWQuQnJvd3NlckF1dGguQWN0aXZlUmVhZC5kZWNvZGUhKG9wZXJhdGlvbiwgcmF3KQoKICBkZWZwIGRlY29kZSEoezpsaWZlY3ljbGUsIG9wZXJhdGlvbn0sIHJhdyksCiAgICBkbzogTWl4ZXJIb3N0ZWQuQnJvd3NlckF1dGguQ2FsbGJhY2tTdG9yZS5kZWNvZGUhKG9wZXJhdGlvbiwgcmF3KQoKICBkZWZwIGRlY29kZSEoOmFkbWl0LCA6YWRtaXR0ZWQpLCBkbzogOmFkbWl0dGVkCiAgZGVmcCBkZWNvZGUhKHs6bG9hZCwgX30sIG5pbCksIGRvOiBuaWwKICBkZWZwIGRlY29kZSEoezpkaXNjb3Zlcl9iZWdpbiwgX30sIG5pbCksIGRvOiBuaWwKCiAgZGVmcCBkZWNvZGUhKHs6Ym9vdHN0cmFwLCBkLCBffSwgcmF3KSBkbwogICAgezpvaywgJVN0b3JlZFNuYXBzaG90e30gPSBzfSA9IFN0b3JlZFNuYXBzaG90LmRlY29kZShyYXcpCiAgICBiID0gcy5icm93c2VyCiAgICB0cnVlID0gcy5hdHRlbXB0ID09PSBuaWwgYW5kIHMuYXR0ZW1wdF9lbnZlbG9wZSA9PT0gbmlsCiAgICB0cnVlID0gcy5zZXNzaW9uX2VudmVsb3BlLmNvbnRleHQgPT09IGQuY29udGV4dCBhbmQgcy5zZXNzaW9uX2VudmVsb3BlLnNlYWxlZCA9PT0gZC5zZWFsZWQKICAgIHRydWUgPSBiWyJzdGF0dXMiXSA9PT0gInByZWF1dGgiIGFuZCBiWyJlcG9jaCJdID09PSAxIGFuZCBiWyJyZXZpc2lvbiJdID09PSAxCiAgICB0cnVlID0gYlsiYXVkaXRfc2VxdWVuY2UiXSA9PT0gMSBhbmQgYlsiaW5pdGlhbF9jb25maWdfZGlnZXN0Il0gPT09IGQuY29udGV4dC5jb25maWdfZGlnZXN0CiAgICB0cnVlID0gYlsiY3JlYXRlZF9hdCJdID09PSBiWyJsYXN0X3NlZW5fYXQiXSBhbmQgYlsiY3JlYXRlZF9hdCJdID49IGQubGVhc2Uuc3RhcnRlZF9hdAogICAgdHJ1ZSA9IGJbImFic29sdXRlX2V4cGlyZXNfYXQiXSA9PT0gZC5leHBpcmVzX2F0IGFuZCBiWyJpZGxlX2V4cGlyZXNfYXQiXSA9PT0gZC5leHBpcmVzX2F0CiAgICBzCiAgZW5kCgogIGRlZnAgZGVjb2RlISh7OmxvYWQsIGlucHV0fSwgcmF3KSBkbwogICAgezpvaywgJVN0b3JlZFNuYXBzaG90e30gPSBzfSA9IFN0b3JlZFNuYXBzaG90LmRlY29kZShyYXcpCiAgICBwcmVhdXRoX3NvdXJjZSEocywgaW5wdXQpCiAgICAjIE9yZGluYXJ5IHByZWF1dGggbG9hZCByZW1haW5zIGRlbGliZXJhdGVseSBuYXJyb3dlciB0aGFuIGJlZ2luIGRpc2NvdmVyeS4KICAgIHRydWUgPSBzLmF0dGVtcHQgPT09IG5pbCBhbmQgcy5hdHRlbXB0X2VudmVsb3BlID09PSBuaWwKICAgIHMKICBlbmQKCiAgZGVmcCBkZWNvZGUhKHs6ZGlzY292ZXJfYmVnaW4sIGlucHV0fSwgcmF3KSBkbwogICAgezpvaywgJVN0b3JlZFNuYXBzaG90e30gPSBzfSA9IFN0b3JlZFNuYXBzaG90LmRlY29kZShyYXcpCiAgICBwcmVhdXRoX3NvdXJjZSEocywgaW5wdXQpCiAgICBwZW5kaW5nX3NvdXJjZSEocywgaW5wdXQubGVhc2UucnVudGltZS5icm93c2VyX2NvbmZpZykKICAgIHMKICBlbmQKCiAgZGVmcCBkZWNvZGUhKHs6YmVnaW4sIGQsIF99LCByYXcpIGRvCiAgICB7Om9rLCAlU3RvcmVkU25hcHNob3R7fSA9IHN9ID0gU3RvcmVkU25hcHNob3QuZGVjb2RlKHJhdykKICAgIGIgPSBkLnNvdXJjZS5icm93c2VyCiAgICAjIENsYWltL3Byb3ZpZGVyIHJlamVjdGlvbiBjYW4gY2hhbmdlIGF1ZGl0X3NlcXVlbmNlIHdpdGhvdXQgcmV2aXNpb24uIENBUwogICAgIyBhbG9uZSBjYW5ub3QgYWRtaXQgdGhhdCByYWNlOiBjb21wYXJlIGV2ZXJ5IHByb2R1Y2VkIGJyb3dzZXIgZmllbGQgaGVyZS4KICAgIHRydWUgPQogICAgICBzLmJyb3dzZXIgPT09ICV7CiAgICAgICAgYgogICAgICAgIHwgImVwb2NoIiA9PiBiWyJlcG9jaCJdICsgMSwKICAgICAgICAgICJyZXZpc2lvbiIgPT4gYlsicmV2aXNpb24iXSArIDEsCiAgICAgICAgICAiYXVkaXRfc2VxdWVuY2UiID0+IGJbImF1ZGl0X3NlcXVlbmNlIl0gKyAxCiAgICAgIH0KCiAgICB0cnVlID0gcy5zZXNzaW9uX2VudmVsb3BlLmNvbnRleHQgPT09IGQuY29udGV4dCBhbmQgcy5zZXNzaW9uX2VudmVsb3BlLnNlYWxlZCA9PT0gZC5zZWFsZWQKCiAgICB0cnVlID0KICAgICAgcy5hdHRlbXB0X2VudmVsb3BlLmNvbnRleHQgPT09IGQuYXR0ZW1wdF9jb250ZXh0IGFuZAogICAgICAgIHMuYXR0ZW1wdF9lbnZlbG9wZS5zZWFsZWQgPT09IGQuYXR0ZW1wdF9zZWFsZWQKCiAgICB0cnVlID0KICAgICAgcy5hdHRlbXB0WyJjcmVhdGVkX2F0Il0gPj0gZC5sZWFzZS5zdGFydGVkX2F0IGFuZAogICAgICAgIHMuYXR0ZW1wdFsiY3JlYXRlZF9hdCJdIDw9IFN5c3RlbS5zeXN0ZW1fdGltZSg6c2Vjb25kKQoKICAgIHRydWUgPQogICAgICBzLmF0dGVtcHQgPT09CiAgICAgICAgYXR0ZW1wdF9maWVsZHMoCiAgICAgICAgICBkLmF0dGVtcHRfY29udGV4dCwKICAgICAgICAgIGQuYXR0ZW1wdF9zZWFsZWQsCiAgICAgICAgICA6Y3J5cHRvLmhhc2goOnNoYTI1NiwgZC5ub25jZSksCiAgICAgICAgICBzLmF0dGVtcHRbImNyZWF0ZWRfYXQiXQogICAgICAgICkKCiAgICB0cnVlID0gU3lzdGVtLnN5c3RlbV90aW1lKDpzZWNvbmQpIDwgZC5hdHRlbXB0X2NvbnRleHQuZXhwaXJlc19hdAogICAgcwogIGVuZAoKICBkZWZwIHByZWF1dGhfc291cmNlISglU3RvcmVkU25hcHNob3R7fSA9IHMsIGlucHV0KSBkbwogICAgYiA9IHMuYnJvd3NlcgogICAgY29uZmlnID0gaW5wdXQubGVhc2UucnVudGltZS5icm93c2VyX2NvbmZpZwogICAgZSA9IHMuc2Vzc2lvbl9lbnZlbG9wZQogICAgdHJ1ZSA9IG1hcF9zaXplKHMpID09IDUKICAgIHRydWUgPSBiWyJzdGF0dXMiXSA9PT0gInByZWF1dGgiCiAgICB0cnVlID0gYlsiY29va2llX2RpZ2VzdCJdID09PSBpbnB1dC5jb29raWVfZGlnZXN0CiAgICB0cnVlID0gYlsiY29uZmlnX2RpZ2VzdCJdID09PSBpbnB1dC5sZWFzZS5ydW50aW1lLmNvbmZpZ3VyYXRpb25fZGlnZXN0CiAgICB0cnVlID0gYlsiaW5pdGlhbF9jb25maWdfZGlnZXN0Il0gPT09IGlucHV0LmxlYXNlLnJ1bnRpbWUuY29uZmlndXJhdGlvbl9kaWdlc3QKICAgIHRydWUgPSBiWyJleHBlY3RlZF9wcm9maWxlX2lkIl0gPT09IGNvbmZpZy5wcm9maWxlX2lkCiAgICB0cnVlID0gYlsiZXhwZWN0ZWRfcHJvZmlsZV92ZXJzaW9uIl0gPT09IGNvbmZpZy5wcm9maWxlX3ZlcnNpb24KCiAgICB0cnVlID0KICAgICAgZS5jb250ZXh0ID09PSAlewogICAgICAgIHB1cnBvc2U6IDpwcmVhdXRoLAogICAgICAgIGJyb3dzZXJfaWQ6IGJbImlkIl0sCiAgICAgICAgY29va2llX2RpZ2VzdDogYlsiY29va2llX2RpZ2VzdCJdLAogICAgICAgIGNzcmZfZGlnZXN0OiBiWyJjc3JmX2RpZ2VzdCJdLAogICAgICAgIGVwb2NoOiBiWyJlcG9jaCJdLAogICAgICAgIHJldmlzaW9uOiBiWyJyZXZpc2lvbiJdLAogICAgICAgIGdlbmVyYXRpb246IGJbImdlbmVyYXRpb24iXSwKICAgICAgICB2YXVsdF9nZW5lcmF0aW9uOiBlLmNvbnRleHQudmF1bHRfZ2VuZXJhdGlvbiwKICAgICAgICBjb25maWdfZGlnZXN0OiBiWyJjb25maWdfZGlnZXN0Il0sCiAgICAgICAgcHJvZmlsZV9pZDogY29uZmlnLnByb2ZpbGVfaWQsCiAgICAgICAgcHJvZmlsZV92ZXJzaW9uOiBjb25maWcucHJvZmlsZV92ZXJzaW9uLAogICAgICAgIHByaW5jaXBhbF9pZDogbmlsLAogICAgICAgIGZhbWlseV9pZDogbmlsLAogICAgICAgIGNyZWRlbnRpYWxfcmVmOiBuaWwsCiAgICAgICAgY3JlZGVudGlhbF9yZXZpc2lvbjogbmlsCiAgICAgIH0KCiAgICB0cnVlID0KICAgICAgRW51bS5hbGw/KAogICAgICAgIH53KHByb2ZpbGVfaWQgcHJvZmlsZV92ZXJzaW9uIHByaW5jaXBhbF9pZCBmYW1pbHlfaWQgY3JlZGVudGlhbF9yZWYgY3JlZGVudGlhbF9yZXZpc2lvbiksCiAgICAgICAgJmlzX25pbChiWyYxXSkKICAgICAgKQoKICAgIDpvawogIGVuZAoKICBkZWZwIHBlbmRpbmdfc291cmNlISglU3RvcmVkU25hcHNob3R7YXR0ZW1wdDogbmlsLCBhdHRlbXB0X2VudmVsb3BlOiBuaWx9LCBfKSwgZG86IDpvawoKICBkZWZwIHBlbmRpbmdfc291cmNlISglU3RvcmVkU25hcHNob3R7fSA9IHMsIGNvbmZpZykgZG8KICAgIGEgPSBzLmF0dGVtcHQKICAgIGIgPSBzLmJyb3dzZXIKICAgIGUgPSBzLmF0dGVtcHRfZW52ZWxvcGUKCiAgICBjID0gJXsKICAgICAgcHVycG9zZTogOmF0dGVtcHQsCiAgICAgIHN0YXRlX2RpZ2VzdDogYVsic3RhdGVfZGlnZXN0Il0sCiAgICAgIGJyb3dzZXJfaWQ6IGJbImlkIl0sCiAgICAgIGNvb2tpZV9kaWdlc3Q6IGJbImNvb2tpZV9kaWdlc3QiXSwKICAgICAgZXBvY2g6IGJbImVwb2NoIl0sCiAgICAgIHJldmlzaW9uOiBiWyJyZXZpc2lvbiJdLAogICAgICBnZW5lcmF0aW9uOiBiWyJnZW5lcmF0aW9uIl0sCiAgICAgIGNvbmZpZ19kaWdlc3Q6IGJbImNvbmZpZ19kaWdlc3QiXSwKICAgICAgcHJvZmlsZV9pZDogY29uZmlnLnByb2ZpbGVfaWQsCiAgICAgIHByb2ZpbGVfdmVyc2lvbjogY29uZmlnLnByb2ZpbGVfdmVyc2lvbiwKICAgICAgaXNzdWVyOiBjb25maWcuaXNzdWVyLAogICAgICBjbGllbnRfaWQ6IGNvbmZpZy5jbGllbnRfaWQsCiAgICAgIHJlZGlyZWN0X3VyaTogY29uZmlnLnJlZGlyZWN0X3VyaSwKICAgICAgZXhwaXJlc19hdDogYVsiZXhwaXJlc19hdCJdCiAgICB9CgogICAgdHJ1ZSA9IGUuY29udGV4dCA9PT0gYwogICAgdHJ1ZSA9IHJhdz8oYVsic3RhdGVfZGlnZXN0Il0sIDMyKSBhbmQgcmF3PyhhWyJub25jZV9kaWdlc3QiXSwgMzIpCiAgICB0cnVlID0gYVsiY3JlYXRlZF9hdCJdID49IGJbImNyZWF0ZWRfYXQiXSBhbmQgYVsiY3JlYXRlZF9hdCJdIDw9IFN5c3RlbS5zeXN0ZW1fdGltZSg6c2Vjb25kKQogICAgdHJ1ZSA9IGFbImV4cGlyZXNfYXQiXSA+IGFbImNyZWF0ZWRfYXQiXSBhbmQgYVsiZXhwaXJlc19hdCJdIDw9IGFbImNyZWF0ZWRfYXQiXSArIDMwMAogICAgdHJ1ZSA9IGFbImV4cGlyZXNfYXQiXSA8PSBtaW4oYlsiYWJzb2x1dGVfZXhwaXJlc19hdCJdLCBiWyJpZGxlX2V4cGlyZXNfYXQiXSkKICAgIHRydWUgPSBhID09PSBhdHRlbXB0X2ZpZWxkcyhjLCBlLnNlYWxlZCwgYVsibm9uY2VfZGlnZXN0Il0sIGFbImNyZWF0ZWRfYXQiXSkKICAgIDpvawogIGVuZAoKICBkZWZwIGF0dGVtcHRfZmllbGRzKGMsIHNlYWxlZCwgbm9uY2VfZGlnZXN0LCBjcmVhdGVkX2F0KSBkbwogICAgJXsKICAgICAgInN0YXRlX2RpZ2VzdCIgPT4gYy5zdGF0ZV9kaWdlc3QsCiAgICAgICJicm93c2VyX2lkIiA9PiBjLmJyb3dzZXJfaWQsCiAgICAgICJicm93c2VyX2Vwb2NoIiA9PiBjLmVwb2NoLAogICAgICAiYnJvd3Nlcl9yZXZpc2lvbiIgPT4gYy5yZXZpc2lvbiwKICAgICAgImNvb2tpZV9kaWdlc3QiID0+IGMuY29va2llX2RpZ2VzdCwKICAgICAgImdlbmVyYXRpb24iID0+IGMuZ2VuZXJhdGlvbiwKICAgICAgImNvbmZpZ19kaWdlc3QiID0+IGMuY29uZmlnX2RpZ2VzdCwKICAgICAgInByb2ZpbGVfaWQiID0+IGMucHJvZmlsZV9pZCwKICAgICAgInByb2ZpbGVfdmVyc2lvbiIgPT4gYy5wcm9maWxlX3ZlcnNpb24sCiAgICAgICJpc3N1ZXIiID0+IGMuaXNzdWVyLAogICAgICAiY2xpZW50X2lkIiA9PiBjLmNsaWVudF9pZCwKICAgICAgInJlZGlyZWN0X3VyaSIgPT4gYy5yZWRpcmVjdF91cmksCiAgICAgICJyZXR1cm5fcm91dGUiID0+ICJ3b3Jrc3BhY2UiLAogICAgICAibm9uY2VfZGlnZXN0IiA9PiBub25jZV9kaWdlc3QsCiAgICAgICJjcmVhdGVkX2F0IiA9PiBjcmVhdGVkX2F0LAogICAgICAiZXhwaXJlc19hdCIgPT4gYy5leHBpcmVzX2F0LAogICAgICAic3RhdHVzIiA9PiAicGVuZGluZyIsCiAgICAgICJjbGFpbV9kaWdlc3QiID0+IG5pbCwKICAgICAgImNsYWltZWRfYXQiID0+IG5pbCwKICAgICAgImNsYWltX2V4cGlyZXNfYXQiID0+IG5pbCwKICAgICAgImNvbXBsZXRpb25fcmVhc29uIiA9PiBuaWwsCiAgICAgICJjaXBoZXJ0ZXh0X3ZlcnNpb24iID0+IDEsCiAgICAgICJrZXlfaWQiID0+IHNlYWxlZC5rZXlfaWQsCiAgICAgICJpdiIgPT4gYnl0ZWFfaGV4KHNlYWxlZC5pdiksCiAgICAgICJ0YWciID0+IGJ5dGVhX2hleChzZWFsZWQudGFnKSwKICAgICAgImNpcGhlcnRleHQiID0+IGJ5dGVhX2hleChzZWFsZWQuY2lwaGVydGV4dCkKICAgIH0KICBlbmQKCiAgZGVmcCBiZWdpbl9kcmFmdD8oJVByZWF1dGhEcmFmdC5CZWdpbnt9ID0gZCkgZG8KICAgIHJ1bnRpbWUgPSBkLmxlYXNlLnJ1bnRpbWUKICAgIGNvbmZpZyA9IHJ1bnRpbWUuYnJvd3Nlcl9jb25maWcKICAgIHNvdXJjZSA9IGQuc291cmNlCiAgICBpbnB1dCA9ICVQcmVhdXRoRHJhZnQuTG9hZHtsZWFzZTogZC5sZWFzZSwgY29va2llX2RpZ2VzdDogZC5jb250ZXh0LmNvb2tpZV9kaWdlc3R9CiAgICA6b2sgPSBwcmVhdXRoX3NvdXJjZSEoc291cmNlLCBpbnB1dCkKICAgIDpvayA9IHBlbmRpbmdfc291cmNlIShzb3VyY2UsIGNvbmZpZykKICAgIGMgPSBzb3VyY2Uuc2Vzc2lvbl9lbnZlbG9wZS5jb250ZXh0CgogICAgZXhwZWN0ZWRfY29udGV4dCA9ICV7CiAgICAgIGMKICAgICAgfCBlcG9jaDogYy5lcG9jaCArIDEsCiAgICAgICAgcmV2aXNpb246IGMucmV2aXNpb24gKyAxLAogICAgICAgIHZhdWx0X2dlbmVyYXRpb246IGMudmF1bHRfZ2VuZXJhdGlvbiArIDEKICAgIH0KCiAgICBleHBpcmVzID0KICAgICAgbWluKAogICAgICAgIGQubGVhc2Uuc3RhcnRlZF9hdCArIDMwMCwKICAgICAgICBtaW4oc291cmNlLmJyb3dzZXJbImlkbGVfZXhwaXJlc19hdCJdLCBzb3VyY2UuYnJvd3NlclsiYWJzb2x1dGVfZXhwaXJlc19hdCJdKQogICAgICApCgogICAgZXhwZWN0ZWRfYXR0ZW1wdCA9ICV7CiAgICAgIHB1cnBvc2U6IDphdHRlbXB0LAogICAgICBzdGF0ZV9kaWdlc3Q6IDpjcnlwdG8uaGFzaCg6c2hhMjU2LCBkLnN0YXRlKSwKICAgICAgYnJvd3Nlcl9pZDogYy5icm93c2VyX2lkLAogICAgICBjb29raWVfZGlnZXN0OiBjLmNvb2tpZV9kaWdlc3QsCiAgICAgIGVwb2NoOiBjLmVwb2NoICsgMSwKICAgICAgcmV2aXNpb246IGMucmV2aXNpb24gKyAxLAogICAgICBnZW5lcmF0aW9uOiBjLmdlbmVyYXRpb24sCiAgICAgIGNvbmZpZ19kaWdlc3Q6IHJ1bnRpbWUuY29uZmlndXJhdGlvbl9kaWdlc3QsCiAgICAgIHByb2ZpbGVfaWQ6IGNvbmZpZy5wcm9maWxlX2lkLAogICAgICBwcm9maWxlX3ZlcnNpb246IGNvbmZpZy5wcm9maWxlX3ZlcnNpb24sCiAgICAgIGlzc3VlcjogY29uZmlnLmlzc3VlciwKICAgICAgY2xpZW50X2lkOiBjb25maWcuY2xpZW50X2lkLAogICAgICByZWRpcmVjdF91cmk6IGNvbmZpZy5yZWRpcmVjdF91cmksCiAgICAgIGV4cGlyZXNfYXQ6IGV4cGlyZXMKICAgIH0KCiAgICB3aXRoIHRydWUgPC0KICAgICAgICAgICBtYXBfc2l6ZShkKSA9PSAxMiBhbmQgZC5jb250ZXh0ID09PSBleHBlY3RlZF9jb250ZXh0IGFuZAogICAgICAgICAgICAgZC5hdHRlbXB0X2NvbnRleHQgPT09IGV4cGVjdGVkX2F0dGVtcHQsCiAgICAgICAgIHRydWUgPC0gRW51bS5hbGw/KFtkLnN0YXRlLCBkLm5vbmNlLCBkLnZlcmlmaWVyLCBkLmNzcmZdLCAmUHJvdG9jb2wudG9rZW4/LzEpLAogICAgICAgICB0cnVlIDwtIGxlbmd0aChFbnVtLnVuaXEoW2Quc3RhdGUsIGQubm9uY2UsIGQudmVyaWZpZXJdKSkgPT0gMywKICAgICAgICAgdHJ1ZSA8LSBTeXN0ZW0uc3lzdGVtX3RpbWUoOnNlY29uZCkgPCBleHBpcmVzLAogICAgICAgICB7Om9rLCB1cmx9IDwtCiAgICAgICAgICAgUHJvdG9jb2wuYXV0aG9yaXphdGlvbl91cmwoY29uZmlnLCAlewogICAgICAgICAgICAgc3RhdGU6IGQuc3RhdGUsCiAgICAgICAgICAgICBub25jZTogZC5ub25jZSwKICAgICAgICAgICAgIHZlcmlmaWVyOiBkLnZlcmlmaWVyCiAgICAgICAgICAgfSksCiAgICAgICAgIHRydWUgPC0gZC51cmwgPT09IHVybCBhbmQgYnl0ZV9zaXplKHVybCkgPD0gODE5MiwKICAgICAgICAgezpvaywgb2xkfSA8LSBWYXVsdC5vcGVuKHJ1bnRpbWUuY3VzdG9keS5rZXksIGMsIHNvdXJjZS5zZXNzaW9uX2VudmVsb3BlLnNlYWxlZCksCiAgICAgICAgIHRydWUgPC0gb2xkID09PSAlVmF1bHQuUHJlYXV0aHtjc3JmOiBkLmNzcmZ9LAogICAgICAgICB7Om9rLCBuZXd9IDwtIFZhdWx0Lm9wZW4ocnVudGltZS5jdXN0b2R5LmtleSwgZC5jb250ZXh0LCBkLnNlYWxlZCksCiAgICAgICAgIHRydWUgPC0gbmV3ID09PSBvbGQsCiAgICAgICAgIHs6b2ssIHZlcmlmaWVyfSA8LSBWYXVsdC5vcGVuKHJ1bnRpbWUuY3VzdG9keS5rZXksIGQuYXR0ZW1wdF9jb250ZXh0LCBkLmF0dGVtcHRfc2VhbGVkKSwKICAgICAgICAgdHJ1ZSA8LSB2ZXJpZmllciA9PT0gJVZhdWx0LlZlcmlmaWVye3ZlcmlmaWVyOiBkLnZlcmlmaWVyfSwKICAgICAgICAgdHJ1ZSA8LSBhdXRoZW50aWNhdGVkX3BlbmRpbmc/KHNvdXJjZSwgcnVudGltZS5jdXN0b2R5LmtleSkgZG8KICAgICAgdHJ1ZQogICAgZWxzZQogICAgICBfIC0+IGZhbHNlCiAgICBlbmQKICBlbmQKCiAgZGVmcCBhdXRoZW50aWNhdGVkX3BlbmRpbmc/KCVTdG9yZWRTbmFwc2hvdHthdHRlbXB0OiBuaWwsIGF0dGVtcHRfZW52ZWxvcGU6IG5pbH0sIF8pLCBkbzogdHJ1ZQoKICBkZWZwIGF1dGhlbnRpY2F0ZWRfcGVuZGluZz8oJVN0b3JlZFNuYXBzaG90e2F0dGVtcHRfZW52ZWxvcGU6IGV9LCBrZXkpLAogICAgZG86IG1hdGNoPyh7Om9rLCAlVmF1bHQuVmVyaWZpZXJ7fX0sIFZhdWx0Lm9wZW4oa2V5LCBlLmNvbnRleHQsIGUuc2VhbGVkKSkKCiAgZGVmcCBib290c3RyYXBfZHJhZnQ/KCVQcmVhdXRoRHJhZnQuQm9vdHN0cmFwe30gPSBkKSBkbwogICAgYyA9IGQuY29udGV4dAogICAgcnVudGltZSA9IGQubGVhc2UucnVudGltZQogICAgY29uZmlnID0gcnVudGltZS5icm93c2VyX2NvbmZpZwoKICAgIG1hcF9zaXplKGQpID09IDcgYW5kIGlzX2ludGVnZXIoZC5leHBpcmVzX2F0KSBhbmQgZC5leHBpcmVzX2F0ID09IGQubGVhc2Uuc3RhcnRlZF9hdCArIDMwMCBhbmQKICAgICAgYy5wdXJwb3NlID09PSA6cHJlYXV0aCBhbmQgYy5lcG9jaCA9PT0gMSBhbmQgYy5yZXZpc2lvbiA9PT0gMSBhbmQgYy52YXVsdF9nZW5lcmF0aW9uID09PSAxIGFuZAogICAgICBjLmNvb2tpZV9kaWdlc3QgPT09IDpjcnlwdG8uaGFzaCg6c2hhMjU2LCBkLmNvb2tpZSkgYW5kCiAgICAgIGMuY3NyZl9kaWdlc3QgPT09IDpjcnlwdG8uaGFzaCg6c2hhMjU2LCBkLmNzcmYpIGFuZAogICAgICBjLmNvbmZpZ19kaWdlc3QgPT09IHJ1bnRpbWUuY29uZmlndXJhdGlvbl9kaWdlc3QgYW5kIGMucHJvZmlsZV9pZCA9PT0gY29uZmlnLnByb2ZpbGVfaWQgYW5kCiAgICAgIGMucHJvZmlsZV92ZXJzaW9uID09PSBjb25maWcucHJvZmlsZV92ZXJzaW9uIGFuZAogICAgICBtYXRjaD8oezpvaywgX30sIFZhdWx0LmFzc29jaWF0ZWRfZGF0YShkLnNlYWxlZC5rZXlfaWQsIGMpKSBhbmQKICAgICAgbWF0Y2g/KHs6b2ssICVWYXVsdC5QcmVhdXRoe319LCBWYXVsdC5vcGVuKHJ1bnRpbWUuY3VzdG9keS5rZXksIGMsIGQuc2VhbGVkKSkKICBlbmQKCiAgZGVmcCBjaGVja3BvaW50IShuaWwsIGRlYWRsaW5lKSwgZG86IHJlbWFpbmluZyEoZGVhZGxpbmUpCgogIGRlZnAgY2hlY2twb2ludCEobGVhc2UsIGRlYWRsaW5lKSBkbwogICAgdHJ1ZSA9IGxlYXNlLmRlYWRsaW5lID09PSBkZWFkbGluZQogICAgOm9rID0gUnVudGltZU93bmVyLmNoZWNrcG9pbnQobGVhc2UpCiAgICByZW1haW5pbmchKGRlYWRsaW5lKQogIGVuZAoKICBkZWZwIHJlbWFpbmluZyEoZGVhZGxpbmUpIGRvCiAgICByZW1haW5pbmcgPSBkZWFkbGluZSAtIFN5c3RlbS5tb25vdG9uaWNfdGltZSg6bWlsbGlzZWNvbmQpCiAgICB0cnVlID0gaXNfaW50ZWdlcihkZWFkbGluZSkgYW5kIHJlbWFpbmluZyA+IDAgYW5kIHJlbWFpbmluZyA8PSA1XzAwMAogICAgcmVtYWluaW5nCiAgZW5kCgogIGRlZnAgbWV0YWRhdGE/KCV7cmVxdWVzdF9pZDogaWR9ID0gbWV0YWRhdGEpCiAgICAgICB3aGVuIG1hcF9zaXplKG1ldGFkYXRhKSA9PSAxIGFuZCBpc19iaW5hcnkoaWQpIGFuZCBieXRlX3NpemUoaWQpID09IDMyLAogICAgICAgZG86IEVudW0uYWxsPyg6YmluYXJ5LmJpbl90b19saXN0KGlkKSwgJigmMSBpbiA/MC4uPzkgb3IgJjEgaW4gP2EuLj9mKSkKCiAgZGVmcCBtZXRhZGF0YT8oXyksIGRvOiBmYWxzZQogIGRlZnAgcmF3Pyh2YWx1ZSwgc2l6ZSksIGRvOiBpc19iaW5hcnkodmFsdWUpIGFuZCBieXRlX3NpemUodmFsdWUpID09IHNpemUKICBkZWZwIGJ5dGVhX2hleCh2YWx1ZSksIGRvOiAiXFx4IiA8PiBCYXNlLmVuY29kZTE2KHZhbHVlLCBjYXNlOiA6bG93ZXIpCmVuZAo="}
    expected={"hosted/config/runtime.exs":{"bytes":549,"sha256":"73cd8edac21bb64c3fba3cd81bb461f2cee651b9f799bd42bfac3e5ffeca6e9f"},"hosted/lib/mixer_hosted_web/browser_http.ex":{"bytes":7099,"sha256":"4065474f1c12c364dd71f73cfdd1855a29bea2d94f5e32b2346141bd2ea622b7"},"hosted/lib/mixer_hosted_web/browser_login_http.ex":{"bytes":4161,"sha256":"1dd605f112835aecdad1f43d6ebd5315beb7b35403cd0aff4d1ad17ba75ae839"},"hosted/lib/mixer_hosted_web/endpoint.ex":{"bytes":160,"sha256":"7702c86f462af84fb6ac157d700d1a22352f2eaf117e31565f672dd533313d08"},"hosted/lib/mixer_hosted/application.ex":{"bytes":1278,"sha256":"bbf02752b982e1437564c266772cd4e5dd7190670a575dd6676dda7fc692803f"},"hosted/test/foundation_integration_test.exs":{"bytes":6296,"sha256":"852de2acd4dbf623925d5fb7eddc14856e4cd0dc0ed09ca87703e6b1f2294a1b"},"hosted/test/mixer_hosted/browser_auth/private_login_http_test.exs":{"bytes":61834,"sha256":"97889c149ddc69458b46f2d4e99a64b1ce37f4770e049515349b25d82fdc62f6"},"hosted/test/mixer_hosted/identity/startup_config_test.exs":{"bytes":8279,"sha256":"bb9fc59f47c2c4bb15c42608ff52cd3dbe88ed71e73957bda3c4775b96214c3a"},"hosted/test/mixer_hosted/identity/startup_lifecycle_test.exs":{"bytes":6531,"sha256":"e88301c119b04528879b0b52e896c73075cd2a390bc17ef9b20a2ddf68430ba2"},"hosted/test/runtime_config_test.exs":{"bytes":3661,"sha256":"bf12eaec3ac8da5b7aec297c16bd3d3e89f62182c3fd00980b60a7c04e3a6daf"},"hosted/test/support/identity_startup_fixture.ex":{"bytes":4539,"sha256":"075f77531b83d43567c214777ee458cb630f15e62fbd1f009c46100ccacdd761"},"hosted/test/mixer_hosted/browser_auth/storage_fixture.exs":{"bytes":7108,"sha256":"9417342d3d5708d21b216383da8cb4bef381e3572036853e6f099ccf08235a06"},"hosted/test/mixer_hosted/browser_auth/run_storage_fixture.py":{"bytes":8627,"sha256":"bfd5edfa4f4e362e76686fb7de89def23ca79eefe1b1c58f74749f550c9bf92c"},"hosted/lib/mixer_hosted/identity/key_owner_supervisor.ex":{"bytes":1072,"sha256":"cdb7b901a8e521361e1578bf0b47ea521a31c61c681c27d1f164925081238ba2"},"hosted/lib/mixer_hosted/browser_auth/store.ex":{"bytes":24830,"sha256":"a310b0a8ec8fb28fe78f8d69b3758399d88d096a7bd2a97fefbaaca091c188bb"}}
    for p,encoded in historical.items():
        body=base64.b64decode(encoded)
        observed={'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest()}
        if observed!=expected[p] or collector.PROVIDER_HTTPS_MANIFEST[p]!=expected[p]:raise RuntimeError('independent v14 predecessor pin '+p)
        source[p]=body
    legacy_provider = base64.b64decode('ZGVmbW9kdWxlIE1peGVySG9zdGVkLkJyb3dzZXJBdXRoLlByb3ZpZGVyT3duZXIgZG8KICBAbW9kdWxlZG9jICJSYXcgcHJvdmlkZXIgYm91bmRhcnkuIFByb2R1Y3Rpb24gdHJhbnNwb3J0IGlzIGRlbGliZXJhdGVseSB1bmNvbmZpZ3VyZWQgYW5kIGZhaWxzIGNsb3NlZC4iCiAgdXNlIEdlblNlcnZlcgogIGFsaWFzIE1peGVySG9zdGVkLkJyb3dzZXJBdXRoLkNvbmZpZ3VyYXRpb25EaWdlc3QKICBhbGlhcyBNaXhlckhvc3RlZC5JZGVudGl0eS5UcnVzdFNuYXBzaG90CgogIGRlZiBleGNoYW5nZShjb25maWcsIGNvZGUsIHZlcmlmaWVyLCBkZWFkbGluZSkgZG8KICAgIEdlblNlcnZlci5jYWxsKF9fTU9EVUxFX18sIHs6ZXhjaGFuZ2UsIGNvbmZpZywgY29kZSwgdmVyaWZpZXIsIGRlYWRsaW5lfSwgcmVtYWluaW5nKGRlYWRsaW5lKSkKICBjYXRjaAogICAgOmV4aXQsIF8gLT4gezplcnJvciwgOnByb3ZpZGVyX3VuYXZhaWxhYmxlfQogIGVuZAoKICBkZWYgZmluaXNoKHRpY2tldCwgY29uZmlnLCBkZWFkbGluZSkgZG8KICAgIEdlblNlcnZlci5jYWxsKF9fTU9EVUxFX18sIHs6ZmluaXNoLCB0aWNrZXQsIGNvbmZpZ30sIHJlbWFpbmluZyhkZWFkbGluZSkpCiAgY2F0Y2gKICAgIDpleGl0LCBfIC0+IHs6ZXJyb3IsIDpwcm92aWRlcl91bmF2YWlsYWJsZX0KICBlbmQKCiAgZGVmIHN0YXJ0X2xpbmsoOnVuY29uZmlndXJlZCksCiAgICBkbzogR2VuU2VydmVyLnN0YXJ0X2xpbmsoX19NT0RVTEVfXywgOnVuY29uZmlndXJlZCwgbmFtZTogX19NT0RVTEVfXykKCiAgaWYgTWl4LmVudigpID09IDp0ZXN0IGRvCiAgICBAZG9jIGZhbHNlCiAgICBkZWYgc3RhcnRfZml4dHVyZShjb25maWcsIHNuYXBzaG90LCB0cmFuc3BvcnQpLAogICAgICBkbzoKICAgICAgICBHZW5TZXJ2ZXIuc3RhcnRfbGluayhfX01PRFVMRV9fLCB7OmZpeHR1cmUsIGNvbmZpZywgc25hcHNob3QsIHRyYW5zcG9ydH0sCiAgICAgICAgICBuYW1lOiBfX01PRFVMRV9fCiAgICAgICAgKQogIGVuZAoKICBkZWYgaW5pdCg6dW5jb25maWd1cmVkKSwgZG86IHs6b2ssIDp1bmNvbmZpZ3VyZWR9CgogIGlmIE1peC5lbnYoKSA9PSA6dGVzdCBkbwogICAgZGVmIGluaXQoezpmaXh0dXJlLCBjb25maWcsIHNuYXBzaG90LCB0cmFuc3BvcnR9KSB3aGVuIGlzX3BpZCh0cmFuc3BvcnQpIGRvCiAgICAgIHs6b2ssIGRpZ2VzdH0gPSBDb25maWd1cmF0aW9uRGlnZXN0LmRpZ2VzdChjb25maWcpCgogICAgICB7Om9rLAogICAgICAgJXsKICAgICAgICAgY29uZmlnOiBjb25maWcsCiAgICAgICAgIGRpZ2VzdDogZGlnZXN0LAogICAgICAgICBzbmFwc2hvdDogc25hcHNob3QsCiAgICAgICAgIHRyYW5zcG9ydDogdHJhbnNwb3J0LAogICAgICAgICBnZW5lcmF0aW9uOiBtYWtlX3JlZigpCiAgICAgICB9fQogICAgZW5kCiAgZW5kCgogIGRlZiBoYW5kbGVfY2FsbCh7OmV4Y2hhbmdlLCBjb25maWcsIGNvZGUsIHZlcmlmaWVyLCBkZWFkbGluZX0sIF9mcm9tLCAle2NvbmZpZzogY29uZmlnfSA9IHMpIGRvCiAgICBpZiBmcmVzaD8ocykgYW5kIFN5c3RlbS5tb25vdG9uaWNfdGltZSg6bWlsbGlzZWNvbmQpIDwgZGVhZGxpbmUgZG8KICAgICAgcmVxdWVzdCA9ICV7CiAgICAgICAgaXNzdWVyOiBjb25maWcuaXNzdWVyLAogICAgICAgIGNsaWVudF9pZDogY29uZmlnLmNsaWVudF9pZCwKICAgICAgICByZWRpcmVjdF91cmk6IGNvbmZpZy5yZWRpcmVjdF91cmksCiAgICAgICAgdG9rZW5fZW5kcG9pbnQ6IGNvbmZpZy50b2tlbl9lbmRwb2ludCwKICAgICAgICBjbGllbnRfYXV0aF9tZXRob2Q6IGNvbmZpZy5jbGllbnRfYXV0aF9tZXRob2QsCiAgICAgICAgY2xpZW50X2NyZWRlbnRpYWxfcmVmOiBjb25maWcuY2xpZW50X2NyZWRlbnRpYWxfcmVmLAogICAgICAgIGNvZGU6IGNvZGUsCiAgICAgICAgY29kZV92ZXJpZmllcjogdmVyaWZpZXIsCiAgICAgICAgZ3JhbnRfdHlwZTogImF1dGhvcml6YXRpb25fY29kZSIKICAgICAgfQoKICAgICAgcmVzdWx0ID0gR2VuU2VydmVyLmNhbGwocy50cmFuc3BvcnQsIHs6ZXhjaGFuZ2UsIHJlcXVlc3R9LCByZW1haW5pbmcoZGVhZGxpbmUpKQoKICAgICAgY2FzZSByZXN1bHQgZG8KICAgICAgICB7Om9rLCByYXd9IHdoZW4gaXNfYmluYXJ5KHJhdykgYW5kIGJ5dGVfc2l6ZShyYXcpIDw9IDE2Mzg0IC0+CiAgICAgICAgICBpZiBmcmVzaD8ocykgYW5kIFN5c3RlbS5tb25vdG9uaWNfdGltZSg6bWlsbGlzZWNvbmQpIDwgZGVhZGxpbmUsCiAgICAgICAgICAgIGRvOiB7OnJlcGx5LCB7Om9rLCByYXcsIHMuc25hcHNob3QsIHtzZWxmKCksIHMuZ2VuZXJhdGlvbiwgcy5kaWdlc3R9fSwgc30sCiAgICAgICAgICAgIGVsc2U6IHs6cmVwbHksIHs6ZXJyb3IsIDpwcm92aWRlcl91bmF2YWlsYWJsZX0sIHN9CgogICAgICAgIF8gLT4KICAgICAgICAgIHs6cmVwbHksIHs6ZXJyb3IsIDpwcm92aWRlcl91bmF2YWlsYWJsZX0sIHN9CiAgICAgIGVuZAogICAgZWxzZQogICAgICB7OnJlcGx5LCB7OmVycm9yLCA6cHJvdmlkZXJfdW5hdmFpbGFibGV9LCBzfQogICAgZW5kCiAgZW5kCgogIGRlZiBoYW5kbGVfY2FsbCh7OmZpbmlzaCwge3BpZCwgZ2VuZXJhdGlvbiwgZGlnZXN0fSwgY29uZmlnfSwgX2Zyb20sICV7Y29uZmlnOiBjb25maWd9ID0gcykgZG8KICAgIHZhbGlkID0gcGlkID09PSBzZWxmKCkgYW5kIGdlbmVyYXRpb24gPT09IHMuZ2VuZXJhdGlvbiBhbmQgZGlnZXN0ID09PSBzLmRpZ2VzdCBhbmQgZnJlc2g/KHMpCiAgICB7OnJlcGx5LCBpZih2YWxpZCwgZG86IDpvaywgZWxzZTogezplcnJvciwgOnByb3ZpZGVyX3VuYXZhaWxhYmxlfSksIHN9CiAgZW5kCgogIGRlZiBoYW5kbGVfY2FsbChfLCBfLCBzKSwgZG86IHs6cmVwbHksIHs6ZXJyb3IsIDpwcm92aWRlcl91bmNvbmZpZ3VyZWR9LCBzfQoKICBkZWYgZm9ybWF0X3N0YXR1cyhzdGF0dXMpLAogICAgZG86CiAgICAgIE1hcC5uZXcoc3RhdHVzLCBmbiB7aywgdn0gLT4KICAgICAgICBpZiBrIGluIFs6c3RhdGUsIDptZXNzYWdlLCA6cmVhc29uLCA6bG9nXSwgZG86IHtrLCA6cmVkYWN0ZWR9LCBlbHNlOiB7aywgdn0KICAgICAgZW5kKQoKICBkZWZwIGZyZXNoPyhzKSwgZG86IFRydXN0U25hcHNob3Quc3RhdHVzKHMuc25hcHNob3QsIFN5c3RlbS5zeXN0ZW1fdGltZSg6c2Vjb25kKSkgPT09IDpmcmVzaAogIGRlZnAgcmVtYWluaW5nKGQpLCBkbzogbWF4KDEsIG1pbig1MDAwLCBkIC0gU3lzdGVtLm1vbm90b25pY190aW1lKDptaWxsaXNlY29uZCkpKQplbmQK')
    if {'bytes':len(legacy_provider),'sha256':hashlib.sha256(legacy_provider).hexdigest()} != collector.CATALOG_JOIN_MANIFEST['hosted/lib/mixer_hosted/browser_auth/provider_owner.ex']: raise RuntimeError('historical ProviderOwner pin')
    source['hosted/lib/mixer_hosted/browser_auth/provider_owner.ex'] = legacy_provider
    return source

class CurrentCLISelectionControls(unittest.TestCase):
    def test_actual_main_preflight_uses_independently_pinned_active_selection(self):
        import contextlib
        import io
        root = COLLECTOR_PATH.resolve().parents[2]
        raw = (root / collector.CONFIGURED_STARTUP_SOURCE_BASE / "selection.json").read_bytes()
        self.assertEqual(collector.CONFIGURED_STARTUP_SELECTION_SHA256, hashlib.sha256(raw).hexdigest())
        expected = json.loads(raw)["selected"]
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(0, collector.main(["--check-source"]))
        observed = json.loads(output.getvalue())
        self.assertEqual(expected["source_count"], observed["source_count"])
        self.assertEqual(expected["source_digest_sha256"], observed["source_digest_sha256"])
        self.assertEqual(collector.CONFIGURED_STARTUP_SELECTION_SHA256, observed["selection_sha256"])
        self.assertFalse(observed["runtime_or_GA_accepted"])


class WorkflowSparseSourceControls(unittest.TestCase):
    # Deliberately limited projection, not a general Git wildmatch interpreter.
    # Only positive rooted files/directories and this one-component family work.
    FAMILY = "/verification/identity-network-current-source-v*/**"
    PIN = "7af785eb990044eb7528cb8e5cca2db9baff8fc6fde06aa981775e7d8ec49470"
    DIGEST = "776dd25ade6103b33dada33cca0d84a312470d7119c376026f2699212edd490f"

    def patterns(self, workflow, job):
        lines = workflow.splitlines(keepends=True)
        marker = "  " + job + ":\n"
        self.assertEqual(1, lines.count(marker))
        start = lines.index(marker) + 1
        end = next((i for i in range(start, len(lines))
                    if lines[i].startswith("  ") and not lines[i].startswith("   ")
                    and lines[i].strip()), len(lines))
        block = "".join(lines[start:end])
        marker = "          sparse-checkout: |\n"
        self.assertEqual(1, block.count(marker))
        self.assertIn("          sparse-checkout-cone-mode: false\n", block)
        result = []
        for line in block.split(marker, 1)[1].splitlines():
            if not line.startswith("            "):
                break
            result.append(line[12:])
        self.assertTrue(result)
        return result

    def materialize(self, root, sparse, patterns):
        import shutil
        for pattern in patterns:
            # Qualified collector-input projection: these two Go-only inputs
            # are unavailable in the identity job and never read by the collector.
            if pattern in ("/services/", "/contracts/release-v2.json"):
                continue
            if pattern == self.FAMILY:
                # glob's '*' matches within one directory component here.
                sources = sorted((root / "verification").glob("identity-network-current-source-v*"))
                self.assertTrue(sources)
                self.assertTrue(all(p.is_dir() and not p.is_symlink() for p in sources))
                rows = [(p.relative_to(root).as_posix(), True) for p in sources]
            else:
                recursive = pattern.endswith(("/**", "/"))
                relative = pattern[1:-3] if pattern.endswith("/**") else pattern[1:].rstrip("/")
                self.assertTrue(pattern.startswith("/") and relative, pattern)
                self.assertTrue(all(c in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-/"
                                    for c in relative), pattern)
                self.assertTrue(all(part not in ("", ".", "..") for part in relative.split("/")), pattern)
                rows = [(relative, recursive)]
            for relative, recursive in rows:
                source, destination = root / relative, sparse / relative
                self.assertFalse(source.is_symlink(), relative)
                destination.parent.mkdir(parents=True, exist_ok=True)
                if recursive:
                    self.assertTrue(source.is_dir(), relative)
                    shutil.copytree(source, destination, dirs_exist_ok=True)
                else:
                    self.assertTrue(source.is_file(), relative)
                    shutil.copyfile(source, destination)

    def check_real_main(self, sparse):
        import contextlib
        import uuid
        path = sparse / "hosted/scripts/test-identity-network.py"
        name = "identity_sparse_control_" + uuid.uuid4().hex
        spec = importlib.util.spec_from_file_location(name, path)
        subject = importlib.util.module_from_spec(spec)
        sys.modules[name] = subject
        try:
            spec.loader.exec_module(subject)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(0, subject.main(["--check-source"]))
            observed = json.loads(output.getvalue())
            self.assertEqual(278, observed["source_count"])
            self.assertEqual(self.DIGEST, observed["source_digest_sha256"])
            self.assertEqual(self.PIN, observed["selection_sha256"])
            self.assertFalse(observed["runtime_or_GA_accepted"])
            return observed
        finally:
            sys.modules.pop(name, None)

    def project_consumer(self, workflow_path, job):
        root = COLLECTOR_PATH.resolve().parents[2]
        raw = (root / "verification/identity-network-current-source-v18/selection.json").read_bytes()
        self.assertEqual(self.PIN, hashlib.sha256(raw).hexdigest())
        patterns = self.patterns((root / workflow_path).read_text(), job)
        self.assertNotIn(self.FAMILY, patterns)
        with tempfile.TemporaryDirectory(prefix="identity-controls-") as directory:
            sparse = Path(directory)
            self.materialize(root, sparse, patterns)
            # The controls themselves read both actual workflow definitions.
            for workflow in ("identity-network.yml", "verify.yml"):
                self.assertEqual((root / ".github/workflows" / workflow).read_bytes(),
                                 (sparse / ".github/workflows" / workflow).read_bytes())
            self.check_real_main(sparse)

    def test_identity_sparse_checkout_admits_real_current_source(self):
        self.project_consumer(".github/workflows/identity-network.yml", "identity-network")

    def test_services_sparse_checkout_admits_real_current_source(self):
        self.project_consumer(".github/workflows/verify.yml", "services")

    def test_services_original_missing_v6_fails_real_import(self):
        root = COLLECTOR_PATH.resolve().parents[2]
        patterns = self.patterns((root / ".github/workflows/verify.yml").read_text(), "services")
        self.assertNotIn(self.FAMILY, patterns)
        with tempfile.TemporaryDirectory(prefix="identity-controls-") as directory:
            sparse = Path(directory)
            self.materialize(root, sparse, [p for p in patterns if not any("identity-network-current-source-v" + str(v) + "/" in p for v in range(6, 11))])
            with self.assertRaisesRegex(FileNotFoundError, "identity-network-current-source-v6/selection.json"):
                self.check_real_main(sparse)

    def test_installed_consumer_missing_v9_refuses_real_import(self):
        root = COLLECTOR_PATH.resolve().parents[2]
        for workflow, job in (("identity-network.yml", "identity-network"), ("verify.yml", "services")):
            patterns = self.patterns((root / ".github/workflows" / workflow).read_text(), job)
            with self.subTest(workflow=workflow), tempfile.TemporaryDirectory(prefix="identity-controls-") as directory:
                sparse = Path(directory)
                self.materialize(root, sparse, patterns)
                self.check_real_main(sparse)
                (sparse / collector.CATALOG_JOIN_SOURCE_BASE / "selection.json").unlink()
                with self.assertRaisesRegex(FileNotFoundError, "identity-network-current-source-v13/selection.json"):
                    self.check_real_main(sparse)

    def test_family_copies_future_metadata_sidecars_in_one_component(self):
        with tempfile.TemporaryDirectory(prefix="identity-controls-") as directory:
            root, sparse = Path(directory) / "input", Path(directory) / "output"
            for relative in ("verification/identity-network-current-source-v13/selection.json",
                             "verification/identity-network-current-source-v999/authority/nested.json",
                             "verification/identity-network-current-source-v999/current-authority.json",
                             "verification/unrelated/identity-network-current-source-v999/selection.json"):
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"inert sidecar")
            self.materialize(root, sparse, [self.FAMILY])
            self.assertEqual(b"inert sidecar", (sparse / "verification/identity-network-current-source-v999/authority/nested.json").read_bytes())
            self.assertEqual(b"inert sidecar", (sparse / "verification/identity-network-current-source-v999/current-authority.json").read_bytes())
            self.assertFalse((sparse / "verification/unrelated").exists())

    def test_projection_refuses_unsupported_wildmatch_and_aliases(self):
        with tempfile.TemporaryDirectory(prefix="identity-controls-") as directory:
            root = Path(directory)
            for pattern in ("!/hosted/", "/verification/*/**", "/verification/identity-network-current-source-v?/**",
                            "/verification/identity-network-current-source-v[67]/**", "/hosted/../escape/", "/hosted//bad/"):
                with self.subTest(pattern=pattern), self.assertRaises(AssertionError):
                    self.materialize(root, root / "output", [pattern])

    def test_future_checkout_metadata_does_not_select_or_replace_authority(self):
        root = COLLECTOR_PATH.resolve().parents[2]
        patterns = self.patterns((root / ".github/workflows/verify.yml").read_text(), "services")
        with tempfile.TemporaryDirectory(prefix="identity-controls-") as directory:
            sparse = Path(directory)
            self.materialize(root, sparse, patterns)
            future = sparse / "verification/identity-network-current-source-v999/selection.json"
            future.parent.mkdir(parents=True)
            future.write_bytes(b'{"selected":{"source_count":999}}')
            self.check_real_main(sparse)
            selected = sparse / "verification/identity-network-current-source-v13/selection.json"
            selected.write_bytes(selected.read_bytes() + b" ")
            with self.assertRaisesRegex(ValueError, "selection pin mismatch"):
                self.check_real_main(sparse)
            selected.unlink()
            with self.assertRaisesRegex(FileNotFoundError, "identity-network-current-source-v13/selection.json"):
                self.check_real_main(sparse)




class OwnedEvidenceSourceControls(unittest.TestCase):
    def test_exact_v11_single_runner_delta_and_inverse(self):
        root = COLLECTOR_PATH.resolve().parents[2]
        metadata = {collector.OWNED_EVIDENCE_SOURCE_BASE + name: (root / collector.OWNED_EVIDENCE_SOURCE_BASE / name).read_bytes() for name in ("selection.json", "selected-source-manifest.json")}
        value = collector.validate_owned_evidence_source_metadata(metadata)
        self.assertEqual({"hosted/scripts/test-local.py"}, set(value["exact_delta"]))
        inverse = dict(collector.OWNED_EVIDENCE_MANIFEST)
        for path, change in value["exact_delta"].items():
            inverse[path] = change["before"]
        self.assertEqual(collector.BROWSER_BUILD_MANIFEST, inverse)
        self.assertEqual(collector.BROWSER_BUILD_SOURCE_DIGEST, canonical_digest(inverse))
        self.assertEqual(243, collector.OWNED_EVIDENCE_SOURCE_COUNT)
        self.assertEqual(set(collector.BROWSER_BUILD_MANIFEST), set(collector.OWNED_EVIDENCE_MANIFEST))

    def test_all_v11_rows_and_caller_replacement_refuse(self):
        for path in collector.OWNED_EVIDENCE_MANIFEST:
            changed = copy.deepcopy(collector.OWNED_EVIDENCE_MANIFEST)
            changed[path]["sha256"] = "0" * 64
            with self.subTest(path=path), self.assertRaises(collector.CollectorError):
                collector.validate_owned_evidence_source_manifest(changed)
        for changed in ({}, collector.BROWSER_BUILD_MANIFEST, {**collector.OWNED_EVIDENCE_MANIFEST, "hosted/foreign": {"bytes":0,"sha256":"0"*64}}):
            with self.assertRaises(collector.CollectorError):
                collector.validate_owned_evidence_source_manifest(changed, expected_digest=canonical_digest(changed), expected_count=len(changed))

    def test_v11_missing_changed_extra_metadata_refuse(self):
        root = COLLECTOR_PATH.resolve().parents[2]
        metadata = {collector.OWNED_EVIDENCE_SOURCE_BASE + name: (root / collector.OWNED_EVIDENCE_SOURCE_BASE / name).read_bytes() for name in ("selection.json", "selected-source-manifest.json")}
        for path in metadata:
            for mode in ("change", "missing"):
                changed = dict(metadata)
                if mode == "change": changed[path] += b" "
                else: changed.pop(path)
                with self.subTest(path=path, mode=mode), self.assertRaises(collector.CollectorError):
                    collector.validate_owned_evidence_source_metadata(changed)
        with self.assertRaises(collector.CollectorError):
            collector.validate_owned_evidence_source_metadata({**metadata, "foreign": b"{}"})


class HostedCompilerSourceControls(unittest.TestCase):
    patterns = WorkflowSparseSourceControls.patterns
    materialize = WorkflowSparseSourceControls.materialize
    check_real_main = WorkflowSparseSourceControls.check_real_main
    FAMILY = WorkflowSparseSourceControls.FAMILY
    PIN = WorkflowSparseSourceControls.PIN
    DIGEST = WorkflowSparseSourceControls.DIGEST
    # Inherited sparse controls run on the live successor as well.
    def test_exact_v12_four_additions_and_inverse(self):
        root = COLLECTOR_PATH.resolve().parents[2]
        metadata = {collector.HOSTED_COMPILER_SOURCE_BASE + name: (root / collector.HOSTED_COMPILER_SOURCE_BASE / name).read_bytes() for name in ("selection.json", "selected-source-manifest.json")}
        value = collector.validate_hosted_compiler_source_metadata(metadata)
        self.assertEqual(247, collector.HOSTED_COMPILER_SOURCE_COUNT)
        self.assertEqual(set(collector.HOSTED_COMPILER_INPUTS), set(value["exact_delta"]))
        inverse = dict(collector.HOSTED_COMPILER_MANIFEST)
        for path, change in value["exact_delta"].items():
            self.assertIsNone(change["before"])
            inverse.pop(path)
        self.assertEqual(collector.OWNED_EVIDENCE_MANIFEST, inverse)
        self.assertEqual(collector.OWNED_EVIDENCE_SOURCE_DIGEST, canonical_digest(inverse))

    def test_v12_every_row_and_caller_authority_refuse(self):
        for path in collector.HOSTED_COMPILER_MANIFEST:
            changed = copy.deepcopy(collector.HOSTED_COMPILER_MANIFEST)
            changed[path]["sha256"] = "0" * 64
            with self.subTest(path=path), self.assertRaises(collector.CollectorError):
                collector.validate_hosted_compiler_source_manifest(changed)
        with self.assertRaises(collector.CollectorError):
            collector.validate_hosted_compiler_source_manifest(collector.OWNED_EVIDENCE_MANIFEST, expected_digest=collector.OWNED_EVIDENCE_SOURCE_DIGEST, expected_count=243)

    def test_v12_missing_module_refuses_actual_source_cli(self):
        root = COLLECTOR_PATH.resolve().parents[2]
        patterns = self.patterns((root / ".github/workflows/identity-network.yml").read_text(), "identity-network")
        for path in collector.HOSTED_COMPILER_INPUTS:
            with self.subTest(path=path), tempfile.TemporaryDirectory(prefix="identity-controls-") as directory:
                sparse = Path(directory)
                self.materialize(root, sparse, patterns)
                (sparse / path).unlink()
                with self.assertRaises(FileNotFoundError):
                    self.check_real_main(sparse)

    def test_v12_missing_changed_extra_metadata_refuse(self):
        root = COLLECTOR_PATH.resolve().parents[2]
        metadata = {collector.HOSTED_COMPILER_SOURCE_BASE + name: (root / collector.HOSTED_COMPILER_SOURCE_BASE / name).read_bytes() for name in ("selection.json", "selected-source-manifest.json")}
        for path in metadata:
            for mode in ("change", "missing"):
                changed = dict(metadata)
                if mode == "change": changed[path] += b" "
                else: changed.pop(path)
                with self.subTest(path=path, mode=mode), self.assertRaises(collector.CollectorError):
                    collector.validate_hosted_compiler_source_metadata(changed)
        with self.assertRaises(collector.CollectorError):
            collector.validate_hosted_compiler_source_metadata({**metadata, "foreign": b"{}"})

    def test_v12_frozen_predecessor_rows_exact(self):
        self.assertEqual(set(collector.OWNED_EVIDENCE_MANIFEST) | set(collector.HOSTED_COMPILER_INPUTS), set(collector.HOSTED_COMPILER_MANIFEST))
        for path, value in collector.OWNED_EVIDENCE_MANIFEST.items():
            self.assertEqual(value, collector.HOSTED_COMPILER_MANIFEST[path])


class CatalogJoinSourceControls(unittest.TestCase):
    def metadata(self):
        root = COLLECTOR_PATH.resolve().parents[2]
        return {collector.CATALOG_JOIN_SOURCE_BASE + n: (root / collector.CATALOG_JOIN_SOURCE_BASE / n).read_bytes() for n in ("selection.json", "selected-source-manifest.json")}

    def test_v13_exact_typed_successor_and_inverse(self):
        selected = collector.validate_catalog_join_source_metadata(self.metadata())
        self.assertEqual(259, collector.CATALOG_JOIN_SOURCE_COUNT)
        inverse = copy.deepcopy(collector.CATALOG_JOIN_MANIFEST)
        for path, change in selected["exact_delta"].items():
            if change["before"] is None: inverse.pop(path)
            else: inverse[path] = change["before"]
        self.assertEqual(collector.HOSTED_COMPILER_MANIFEST, inverse)
        self.assertEqual(collector.HOSTED_COMPILER_SOURCE_DIGEST, canonical_digest(inverse))
        for path, value in collector.HOSTED_COMPILER_MANIFEST.items():
            if path not in selected["exact_delta"]: self.assertEqual(value, collector.CATALOG_JOIN_MANIFEST[path])

    def test_v13_every_wrong_missing_extra_row_and_digest_refuses(self):
        for path in collector.CATALOG_JOIN_MANIFEST:
            for mode in ("changed", "missing"):
                value = copy.deepcopy(collector.CATALOG_JOIN_MANIFEST)
                if mode == "changed": value[path]["sha256"] = "0" * 64
                else: value.pop(path)
                with self.subTest(path=path, mode=mode), self.assertRaises(collector.CollectorError):
                    collector.validate_catalog_join_source_manifest(value)
        value = {**collector.CATALOG_JOIN_MANIFEST, "hosted/foreign": {"bytes":0,"sha256":"0"*64}}
        with self.assertRaises(collector.CollectorError): collector.validate_catalog_join_source_manifest(value)
        with self.assertRaises(collector.CollectorError): collector.validate_catalog_join_source_manifest(value, expected_digest=canonical_digest(value), expected_count=len(value))
        with self.assertRaises(collector.CollectorError): collector.validate_catalog_join_source_manifest(collector.HOSTED_COMPILER_MANIFEST)

    def test_v13_metadata_missing_changed_extra_and_forged_inverse_refuse(self):
        metadata = self.metadata()
        for path in metadata:
            for mode in ("change", "missing"):
                value = dict(metadata)
                if mode == "change": value[path] += b" "
                else: value.pop(path)
                with self.subTest(path=path, mode=mode), self.assertRaises(collector.CollectorError): collector.validate_catalog_join_source_metadata(value)
        with self.assertRaises(collector.CollectorError): collector.validate_catalog_join_source_metadata({**metadata,"foreign":b"{}"})
        # Bypass only the outer selection pin to reach the independent delta/inverse contract.
        path = collector.CATALOG_JOIN_SOURCE_BASE + "selection.json"
        value = json.loads(metadata[path]); changed = next(p for p,c in value["exact_delta"].items() if c["before"] is not None)
        value["exact_delta"][changed]["before"]["sha256"] = "0" * 64
        forged = json.dumps(value,sort_keys=True).encode()
        with mock.patch.object(collector, "CATALOG_JOIN_SELECTION_SHA256", hashlib.sha256(forged).hexdigest()):
            with self.assertRaises(collector.CollectorError): collector.validate_catalog_join_source_metadata({**metadata,path:forged})

    def test_v13_all_three_exact_sparse_consumers_and_missing_driver_refuse(self):
        helper = WorkflowSparseSourceControls()
        root = COLLECTOR_PATH.resolve().parents[2]
        for workflow, job in (("hosted.yml","phoenix"),("identity-network.yml","identity-network"),("verify.yml","services")):
            patterns = helper.patterns((root / ".github/workflows" / workflow).read_text(),job)
            self.assertNotIn(helper.FAMILY,patterns)
            with self.subTest(workflow=workflow), tempfile.TemporaryDirectory(prefix="identity-controls-") as directory:
                sparse=Path(directory); helper.materialize(root,sparse,patterns); helper.check_real_main(sparse)
                (sparse / "hosted/test/support/browser_build_catalog_client.mjs").unlink()
                with self.assertRaises(FileNotFoundError): helper.check_real_main(sparse)

class ProviderHTTPSSourceControls(unittest.TestCase):
    def test_v14_exact_four_additions_inverse_and_twelve_compiler_inputs(self):
        selected=collector.PROVIDER_HTTPS_MANIFEST
        self.assertEqual(263,len(selected))
        self.assertEqual(collector.CATALOG_JOIN_MANIFEST,{p:e for p,e in selected.items() if p not in collector.PROVIDER_HTTPS_DELTA})
        expected=('console/src/api/browser-session-client.ts','console/src/api/cookie-build-catalog-client.ts','console/src/api/cookie-build-client.ts','console/src/api/cookie-workspace-client.ts','console/src/api/workspace-client.ts','console/src/api/workspace-transport.ts','console/src/domain/build-catalog.ts','console/src/domain/build-overview.ts','console/src/domain/build-read.ts','console/src/domain/workspace-directory.ts','console/src/state/browser-session-controller.ts','console/src/state/workspace-controller.ts')
        self.assertEqual(expected,tuple(sorted(p for p in selected if p.endswith('.ts'))))
        for p in expected:self.assertEqual(collector.CATALOG_JOIN_MANIFEST[p],selected[p])
        root=COLLECTOR_PATH.resolve().parents[2]
        metadata={collector.PROVIDER_HTTPS_SOURCE_BASE+n:(root/collector.PROVIDER_HTTPS_SOURCE_BASE/n).read_bytes() for n in ('selection.json','selected-source-manifest.json')}
        value=collector.validate_provider_https_source_metadata(metadata)
        self.assertEqual(4,len(value['exact_delta']))
        self.assertTrue(all(c['before'] is None for c in value['exact_delta'].values()))

    def test_v14_actual_cli_entrypoint_executes_and_stale_provider_refuses(self):
        import contextlib,runpy
        root=COLLECTOR_PATH.resolve().parents[2]
        output=io.StringIO()
        with mock.patch.object(sys,'argv',[str(COLLECTOR_PATH),'--check-source']),contextlib.redirect_stdout(output):
            with self.assertRaises(SystemExit) as exited:runpy.run_path(str(COLLECTOR_PATH),run_name='__main__')
        self.assertEqual(0,exited.exception.code)
        observed=json.loads(output.getvalue())
        self.assertEqual(278,observed['source_count'])
        self.assertEqual(collector.CONFIGURED_STARTUP_SOURCE_DIGEST,observed['source_digest_sha256'])
        self.assertEqual(collector.CONFIGURED_STARTUP_SELECTION_SHA256,observed['selection_sha256'])
        path=next(iter(collector.PROVIDER_HTTPS_DELTA));target=root/path;original=target.read_bytes()
        try:
            target.write_bytes(original+b'\n')
            with self.assertRaises(collector.CollectorError):collector.main(['--check-source'])
        finally:target.write_bytes(original)

    def test_v14_each_new_file_required_by_all_actual_sparse_consumers(self):
        helper=WorkflowSparseSourceControls();root=COLLECTOR_PATH.resolve().parents[2]
        for workflow,job in [('hosted.yml','phoenix'),('identity-network.yml','identity-network'),('verify.yml','services')]:
            patterns=helper.patterns((root/'.github/workflows'/workflow).read_text(),job)
            self.assertIn('/'+collector.PROVIDER_HTTPS_SOURCE_BASE+'selection.json',patterns)
            self.assertIn('/'+collector.PROVIDER_HTTPS_SOURCE_BASE+'selected-source-manifest.json',patterns)
            with self.subTest(workflow=workflow),tempfile.TemporaryDirectory(prefix='identity-controls-') as directory:
                sparse=Path(directory);helper.materialize(root,sparse,patterns);helper.check_real_main(sparse)
                for p in collector.PROVIDER_HTTPS_DELTA:
                    target=sparse/p;data=target.read_bytes();target.unlink()
                    try:
                        with self.assertRaises(FileNotFoundError):helper.check_real_main(sparse)
                    finally:target.write_bytes(data)

    def test_v14_stale_missing_extra_manifest_and_caller_authority_refuse(self):
        for p in collector.PROVIDER_HTTPS_DELTA:
            for missing in (True,False):
                value=copy.deepcopy(collector.PROVIDER_HTTPS_MANIFEST)
                if missing:value.pop(p)
                else:value[p]['sha256']='0'*64
                with self.subTest(path=p,missing=missing),self.assertRaises(collector.CollectorError):collector.validate_provider_https_source_manifest(value)
        value={**collector.PROVIDER_HTTPS_MANIFEST,'hosted/future.ex':{'bytes':0,'sha256':'0'*64}}
        with self.assertRaises(collector.CollectorError):collector.validate_provider_https_source_manifest(value,canonical_digest(value),264)
        with self.assertRaises(collector.CollectorError):collector.validate_provider_https_source_manifest(collector.CATALOG_JOIN_MANIFEST)


class OrdinaryBrowserSourceControls(unittest.TestCase):
    def metadata(self):
        root=COLLECTOR_PATH.resolve().parents[2]
        return {collector.ORDINARY_BROWSER_SOURCE_BASE+n:(root/collector.ORDINARY_BROWSER_SOURCE_BASE/n).read_bytes() for n in ('selection.json','selected-source-manifest.json')}

    def test_v15_exact_graph_inverse_and_protected_inputs(self):
        value=collector.validate_ordinary_browser_source_metadata(self.metadata())
        self.assertEqual(272,len(collector.ORDINARY_BROWSER_MANIFEST))
        self.assertEqual(24,len(value['exact_delta']))
        self.assertEqual(9,sum(c['before'] is None for c in value['exact_delta'].values()))
        inverse=dict(collector.ORDINARY_BROWSER_MANIFEST)
        for p,c in value['exact_delta'].items():
            if c['before'] is None:inverse.pop(p)
            else:inverse[p]=c['before']
        self.assertEqual(collector.PROVIDER_HTTPS_MANIFEST,inverse)
        self.assertEqual(collector.PROVIDER_HTTPS_SOURCE_DIGEST,canonical_digest(inverse))
        for p in collector.PROVIDER_HTTPS_MANIFEST:
            if p.endswith('.ts') or p in collector.PROVIDER_HTTPS_DELTA or p.startswith('hosted/priv/repo/migrations/'):
                self.assertEqual(collector.PROVIDER_HTTPS_MANIFEST[p],collector.ORDINARY_BROWSER_MANIFEST[p])
        self.assertFalse(value['runtime_or_GA_accepted'])

    def test_v15_every_graph_row_and_caller_authority_refuse(self):
        for p in collector.ORDINARY_BROWSER_DELTA:
            for missing in (True,False):
                value=copy.deepcopy(collector.ORDINARY_BROWSER_MANIFEST)
                if missing:value.pop(p)
                else:value[p]['sha256']='0'*64
                with self.subTest(path=p,missing=missing),self.assertRaises(collector.CollectorError):collector.validate_ordinary_browser_source_manifest(value)
        value={**collector.ORDINARY_BROWSER_MANIFEST,'hosted/future.ex':{'bytes':0,'sha256':'0'*64}}
        with self.assertRaises(collector.CollectorError):collector.validate_ordinary_browser_source_manifest(value,canonical_digest(value),273)
        with self.assertRaises(collector.CollectorError):collector.validate_ordinary_browser_source_manifest(collector.PROVIDER_HTTPS_MANIFEST)

    def test_v15_metadata_pin_membership_and_inverse_authority_refuse(self):
        metadata=self.metadata()
        for p in metadata:
            for missing in (True,False):
                value=dict(metadata)
                if missing:value.pop(p)
                else:value[p]+=b' '
                with self.subTest(path=p,missing=missing),self.assertRaises(collector.CollectorError):collector.validate_ordinary_browser_source_metadata(value)
        with self.assertRaises(collector.CollectorError):collector.validate_ordinary_browser_source_metadata({**metadata,'foreign':b'{}'})
        p=collector.ORDINARY_BROWSER_SOURCE_BASE+'selection.json';v=json.loads(metadata[p]);v['predecessor']['source_count']=262
        forged=json.dumps(v,sort_keys=True).encode()
        with mock.patch.object(collector,'ORDINARY_BROWSER_SELECTION_SHA256',hashlib.sha256(forged).hexdigest()):
            with self.assertRaises(collector.CollectorError):collector.validate_ordinary_browser_source_metadata({**metadata,p:forged})

    def test_v15_all_actual_sparse_consumers_require_both_exact_metadata_files(self):
        helper=WorkflowSparseSourceControls();root=COLLECTOR_PATH.resolve().parents[2]
        for workflow,job in [('hosted.yml','phoenix'),('identity-network.yml','identity-network'),('verify.yml','services')]:
            patterns=helper.patterns((root/'.github/workflows'/workflow).read_text(),job)
            self.assertNotIn(helper.FAMILY,patterns)
            for n in ('selection.json','selected-source-manifest.json'):
                self.assertIn('/'+collector.ORDINARY_BROWSER_SOURCE_BASE+n,patterns)
            with self.subTest(workflow=workflow),tempfile.TemporaryDirectory(prefix='identity-controls-') as directory:
                sparse=Path(directory);helper.materialize(root,sparse,patterns);helper.check_real_main(sparse)
                for n in ('selection.json','selected-source-manifest.json'):
                    target=sparse/collector.ORDINARY_BROWSER_SOURCE_BASE/n;body=target.read_bytes();target.unlink()
                    try:
                        with self.assertRaises(FileNotFoundError):helper.check_real_main(sparse)
                    finally:target.write_bytes(body)

class SupervisedProviderSourceControls(unittest.TestCase):
    def metadata(self):
        root = COLLECTOR_PATH.resolve().parents[2]
        return {collector.SUPERVISED_PROVIDER_SOURCE_BASE+n:(root/collector.SUPERVISED_PROVIDER_SOURCE_BASE/n).read_bytes() for n in ('selection.json','selected-source-manifest.json')}

    def test_v16_exact_delta_and_complete_legacy_inverse(self):
        value = collector.validate_supervised_provider_source_metadata(self.metadata())
        self.assertEqual(275,len(collector.SUPERVISED_PROVIDER_MANIFEST))
        self.assertEqual(4,len(value['exact_delta']))
        self.assertEqual(3,sum(c['before'] is None for c in value['exact_delta'].values()))
        inverse = dict(collector.SUPERVISED_PROVIDER_MANIFEST)
        for p,c in value['exact_delta'].items():
            if c['before'] is None: inverse.pop(p)
            else: inverse[p] = c['before']
        self.assertEqual(collector.ORDINARY_BROWSER_MANIFEST,inverse)
        self.assertEqual('7541ccd6dc3369acac10dbfa881914eaf76e0c092a7ceaba142fc26ce00c169e',canonical_digest(inverse))
        self.assertFalse(value['runtime_or_GA_accepted'])
        provider = 'hosted/lib/mixer_hosted/browser_auth/provider_owner.ex'
        self.assertEqual('f4d130a1242820c5419870e5446bb4283d771bb2ba23bc760b1f6870096fd779',value['exact_delta'][provider]['after']['sha256'])
        for p,r in collector.ORDINARY_BROWSER_MANIFEST.items():
            if p != provider: self.assertEqual(r,collector.SUPERVISED_PROVIDER_MANIFEST[p])

    def test_v16_forged_metadata_wrong_predecessor_and_false_runtime_refuse(self):
        metadata = self.metadata()
        for path in metadata:
            with self.assertRaises(collector.CollectorError): collector.validate_supervised_provider_source_metadata({**metadata,path:metadata[path]+b' '})
            with self.assertRaises(collector.CollectorError): collector.validate_supervised_provider_source_metadata({p:b for p,b in metadata.items() if p!=path})
        with self.assertRaises(collector.CollectorError): collector.validate_supervised_provider_source_metadata({**metadata,'foreign':b'{}'})
        path = collector.SUPERVISED_PROVIDER_SOURCE_BASE+'selection.json'
        for field in ('predecessor','exact_delta','runtime_or_GA_accepted'):
            value = json.loads(metadata[path])
            if field=='predecessor': value[field]['source_count']=271
            elif field=='exact_delta': value[field]={}
            else: value[field]=True
            body=json.dumps(value,sort_keys=True).encode()
            with mock.patch.object(collector,'SUPERVISED_PROVIDER_SELECTION_SHA256',hashlib.sha256(body).hexdigest()):
                with self.assertRaises(collector.CollectorError): collector.validate_supervised_provider_source_metadata({**metadata,path:body})

    def test_v16_missing_changed_provider_and_constructors_refuse(self):
        for path in collector.SUPERVISED_PROVIDER_DELTA:
            for missing in (True,False):
                value=copy.deepcopy(collector.SUPERVISED_PROVIDER_MANIFEST)
                if missing: value.pop(path)
                else: value[path]['sha256']='0'*64
                with self.subTest(path=path,missing=missing),self.assertRaises(collector.CollectorError): collector.validate_supervised_provider_source_manifest(value)
        stale=dict(collector.SUPERVISED_PROVIDER_MANIFEST)
        p='hosted/lib/mixer_hosted/browser_auth/provider_owner.ex'
        stale[p]=collector.ORDINARY_BROWSER_MANIFEST[p]
        with self.assertRaises(collector.CollectorError): collector.validate_supervised_provider_source_manifest(stale)
        with self.assertRaises(collector.CollectorError): collector.validate_supervised_provider_source_manifest(stale,canonical_digest(stale),275)

    def test_v16_sparse_consumers_require_exact_new_metadata(self):
        helper=WorkflowSparseSourceControls();root=COLLECTOR_PATH.resolve().parents[2]
        for workflow,job in [('hosted.yml','phoenix'),('identity-network.yml','identity-network'),('verify.yml','services')]:
            patterns=helper.patterns((root/'.github/workflows'/workflow).read_text(),job)
            for name in ('selection.json','selected-source-manifest.json'):
                self.assertIn('/'+collector.SUPERVISED_PROVIDER_SOURCE_BASE+name,patterns)
            with self.subTest(workflow=workflow),tempfile.TemporaryDirectory(prefix='identity-v16-') as directory:
                sparse=Path(directory);helper.materialize(root,sparse,patterns);helper.check_real_main(sparse)
                for name in ('selection.json','selected-source-manifest.json'):
                    target=sparse/collector.SUPERVISED_PROVIDER_SOURCE_BASE/name;body=target.read_bytes();target.unlink()
                    try:
                        with self.assertRaises(FileNotFoundError): helper.check_real_main(sparse)
                    finally: target.write_bytes(body)



class ProviderIOSourceControls(unittest.TestCase):
    def metadata(self):
        root = COLLECTOR_PATH.resolve().parents[2]
        return {collector.PROVIDER_IO_SOURCE_BASE+n: (root/collector.PROVIDER_IO_SOURCE_BASE/n).read_bytes()
                for n in ('selection.json', 'selected-source-manifest.json')}

    def test_v17_four_row_delta_and_complete_v16_inverse(self):
        value = collector.validate_provider_io_source_metadata(self.metadata())
        self.assertEqual(277, len(collector.PROVIDER_IO_MANIFEST))
        self.assertEqual(4, len(value['exact_delta']))
        self.assertEqual(2, sum(c['before'] is None for c in value['exact_delta'].values()))
        inverse = dict(collector.PROVIDER_IO_MANIFEST)
        for path, change in value['exact_delta'].items():
            if change['before'] is None: inverse.pop(path)
            else: inverse[path] = change['before']
        self.assertEqual(collector.SUPERVISED_PROVIDER_MANIFEST, inverse)
        self.assertEqual('758ae1c973ec4b58ea0158b5566d6ac81cb1cad6a54762d3e5a23a2ff99896a8', canonical_digest(inverse))
        for path, expected in collector.SUPERVISED_PROVIDER_MANIFEST.items():
            if path not in value['exact_delta']: self.assertEqual(expected, collector.PROVIDER_IO_MANIFEST[path])
        self.assertEqual('c9aa46dfee58f17368f4089d10b27e1b1eb592ecb1df245ece445dca95313192', collector.PROVIDER_IO_MANIFEST['hosted/lib/mixer_hosted/browser_auth/provider_owner.ex']['sha256'])
        self.assertEqual('02fb29c723d7394148a170a40dd39db86f15d007d0777b9f31f938a6032c79c4', collector.PROVIDER_IO_MANIFEST['hosted/lib/mixer_hosted/browser_auth/provider_https.ex']['sha256'])
        self.assertFalse(value['runtime_or_GA_accepted'])

    def test_v17_metadata_pin_membership_predecessor_delta_and_false_runtime_refuse(self):
        metadata = self.metadata()
        for path in metadata:
            with self.assertRaises(collector.CollectorError): collector.validate_provider_io_source_metadata({**metadata, path: metadata[path]+b' '})
            with self.assertRaises(collector.CollectorError): collector.validate_provider_io_source_metadata({p:b for p,b in metadata.items() if p != path})
        with self.assertRaises(collector.CollectorError): collector.validate_provider_io_source_metadata({**metadata, 'foreign': b'{}'})
        path = collector.PROVIDER_IO_SOURCE_BASE+'selection.json'
        for field in ('predecessor', 'exact_delta', 'runtime_or_GA_accepted'):
            value = json.loads(metadata[path])
            if field == 'predecessor': value[field]['source_count'] = 274
            elif field == 'exact_delta': value[field] = {}
            else: value[field] = True
            body = json.dumps(value, sort_keys=True).encode()
            with mock.patch.object(collector, 'PROVIDER_IO_SELECTION_SHA256', hashlib.sha256(body).hexdigest()):
                with self.assertRaises(collector.CollectorError): collector.validate_provider_io_source_metadata({**metadata, path: body})

    def test_v17_missing_stale_superseded_and_extra_sources_refuse(self):
        for path in collector.PROVIDER_IO_DELTA:
            for missing in (True, False):
                value = copy.deepcopy(collector.PROVIDER_IO_MANIFEST)
                if missing: value.pop(path)
                else: value[path]['sha256'] = '0'*64
                with self.subTest(path=path, missing=missing), self.assertRaises(collector.CollectorError): collector.validate_provider_io_source_manifest(value)
        stale = copy.deepcopy(collector.PROVIDER_IO_MANIFEST)
        stale['hosted/lib/mixer_hosted/browser_auth/provider_https.ex']['sha256'] = '60e6bc274a7d05eb1eee4b63feb4cb2f50a695ecd03dad191b73b464686e147c'
        with self.assertRaises(collector.CollectorError): collector.validate_provider_io_source_manifest(stale)
        extra = {**collector.PROVIDER_IO_MANIFEST, 'hosted/future.ex': {'bytes': 0, 'sha256': '0'*64}}
        with self.assertRaises(collector.CollectorError): collector.validate_provider_io_source_manifest(extra, canonical_digest(extra), 278)
        with self.assertRaises(collector.CollectorError): collector.validate_provider_io_source_manifest(collector.SUPERVISED_PROVIDER_MANIFEST)
        for count in (True, 277.0, 275):
            with self.assertRaises(collector.CollectorError): collector.validate_provider_io_source_manifest(collector.PROVIDER_IO_MANIFEST, expected_count=count)

    def test_v17_sparse_consumers_require_metadata_module_and_controls(self):
        helper = WorkflowSparseSourceControls(); root = COLLECTOR_PATH.resolve().parents[2]
        for workflow, job in [('hosted.yml','phoenix'), ('identity-network.yml','identity-network'), ('verify.yml','services')]:
            patterns = helper.patterns((root/'.github/workflows'/workflow).read_text(), job)
            for name in ('selection.json', 'selected-source-manifest.json'):
                self.assertIn('/'+collector.PROVIDER_IO_SOURCE_BASE+name, patterns)
            with self.subTest(workflow=workflow), tempfile.TemporaryDirectory(prefix='identity-v17-') as directory:
                sparse = Path(directory); helper.materialize(root, sparse, patterns); helper.check_real_main(sparse)
                paths = [collector.PROVIDER_IO_SOURCE_BASE+n for n in ('selection.json','selected-source-manifest.json')]
                paths += ['hosted/lib/mixer_hosted/browser_auth/startup_secrets.ex', 'hosted/test/mixer_hosted/browser_auth/startup_secrets_test.exs']
                for path in paths:
                    target = sparse/path; body = target.read_bytes(); target.unlink()
                    try:
                        with self.assertRaises(FileNotFoundError): helper.check_real_main(sparse)
                    finally: target.write_bytes(body)

    def test_v17_production_constructor_job_uses_exact_script_and_test_inputs(self):
        root = COLLECTOR_PATH.resolve().parents[2]
        workflow = (root/'.github/workflows/hosted.yml').read_text()
        command = 'hosted/scripts/check-startup-secrets.exs hosted/deps/jason/lib'
        self.assertEqual(1, workflow.count(command))
        driver = (root/'hosted/scripts/check-startup-secrets.exs').read_text()
        self.assertIn('Mix.env(:prod)', driver)
        self.assertIn('hosted/lib/mixer_hosted/browser_auth/startup_secrets.ex', driver)
        self.assertIn('hosted/test/mixer_hosted/browser_auth/startup_secrets_test.exs', driver)
        self.assertIn('result.total != 8', driver)
        self.assertIn('result.skipped != 0', driver)



class ConfiguredStartupSourceControls(unittest.TestCase):
    def metadata(self):
        root = COLLECTOR_PATH.resolve().parents[2]
        return {collector.CONFIGURED_STARTUP_SOURCE_BASE+n: (root/collector.CONFIGURED_STARTUP_SOURCE_BASE/n).read_bytes()
                for n in ('selection.json', 'selected-source-manifest.json')}

    def test_v18_six_row_delta_and_complete_v17_inverse(self):
        value = collector.validate_configured_startup_source_metadata(self.metadata())
        self.assertEqual(278, len(collector.CONFIGURED_STARTUP_MANIFEST))
        self.assertEqual(6, len(value['exact_delta']))
        self.assertEqual(272, sum(v == collector.CONFIGURED_STARTUP_MANIFEST[p] for p, v in collector.PROVIDER_IO_MANIFEST.items()))
        self.assertEqual({'hosted/lib/mixer_hosted/browser_auth/supervisor.ex', 'hosted/test/mixer_hosted/browser_auth/provider_trust_config_test.exs', 'hosted/test/mixer_hosted/browser_auth/provider_owner_lifecycle_test.exs', 'hosted/test/mixer_hosted/browser_auth/ordinary_console_catalog_navigation_cookie_pg_join_test.exs', 'hosted/lib/mixer_hosted/browser_auth/installation.ex', 'hosted/scripts/check-configured-startup.exs'}, set(value['exact_delta']))
        self.assertEqual(1, sum(c['before'] is None for c in value['exact_delta'].values()))
        inverse = dict(collector.CONFIGURED_STARTUP_MANIFEST)
        for path, change in value['exact_delta'].items():
            if change['before'] is None: inverse.pop(path)
            else: inverse[path] = change['before']
        self.assertEqual(collector.PROVIDER_IO_MANIFEST, inverse)
        self.assertEqual('6021237e9cdf0dcc0cdf25ef841e754c93591723045031d06fa7a572e5d34661', canonical_digest(inverse))
        for path, expected in collector.PROVIDER_IO_MANIFEST.items():
            if path not in value['exact_delta']: self.assertEqual(expected, collector.CONFIGURED_STARTUP_MANIFEST[path])
        self.assertEqual('c9aa46dfee58f17368f4089d10b27e1b1eb592ecb1df245ece445dca95313192', collector.CONFIGURED_STARTUP_MANIFEST['hosted/lib/mixer_hosted/browser_auth/provider_owner.ex']['sha256'])
        self.assertEqual('02fb29c723d7394148a170a40dd39db86f15d007d0777b9f31f938a6032c79c4', collector.CONFIGURED_STARTUP_MANIFEST['hosted/lib/mixer_hosted/browser_auth/provider_https.ex']['sha256'])
        self.assertFalse(value['runtime_or_GA_accepted'])

    def test_v18_metadata_pin_membership_predecessor_delta_and_false_runtime_refuse(self):
        metadata = self.metadata()
        for path in metadata:
            with self.assertRaises(collector.CollectorError): collector.validate_configured_startup_source_metadata({**metadata, path: metadata[path]+b' '})
            with self.assertRaises(collector.CollectorError): collector.validate_configured_startup_source_metadata({p:b for p,b in metadata.items() if p != path})
        with self.assertRaises(collector.CollectorError): collector.validate_configured_startup_source_metadata({**metadata, 'foreign': b'{}'})
        path = collector.CONFIGURED_STARTUP_SOURCE_BASE+'selection.json'
        for field in ('predecessor', 'exact_delta', 'runtime_or_GA_accepted'):
            value = json.loads(metadata[path])
            if field == 'predecessor': value[field]['source_count'] = 274
            elif field == 'exact_delta': value[field] = {}
            else: value[field] = True
            body = json.dumps(value, sort_keys=True).encode()
            with mock.patch.object(collector, 'CONFIGURED_STARTUP_SELECTION_SHA256', hashlib.sha256(body).hexdigest()):
                with self.assertRaises(collector.CollectorError): collector.validate_configured_startup_source_metadata({**metadata, path: body})

    def test_v18_missing_stale_superseded_and_extra_sources_refuse(self):
        for path in collector.CONFIGURED_STARTUP_DELTA:
            for missing in (True, False):
                value = copy.deepcopy(collector.CONFIGURED_STARTUP_MANIFEST)
                if missing: value.pop(path)
                else: value[path]['sha256'] = '0'*64
                with self.subTest(path=path, missing=missing), self.assertRaises(collector.CollectorError): collector.validate_configured_startup_source_manifest(value)
        stale = copy.deepcopy(collector.CONFIGURED_STARTUP_MANIFEST)
        stale['hosted/lib/mixer_hosted/browser_auth/provider_https.ex']['sha256'] = '60e6bc274a7d05eb1eee4b63feb4cb2f50a695ecd03dad191b73b464686e147c'
        with self.assertRaises(collector.CollectorError): collector.validate_configured_startup_source_manifest(stale)
        extra = {**collector.CONFIGURED_STARTUP_MANIFEST, 'hosted/future.ex': {'bytes': 0, 'sha256': '0'*64}}
        with self.assertRaises(collector.CollectorError): collector.validate_configured_startup_source_manifest(extra, canonical_digest(extra), 278)
        with self.assertRaises(collector.CollectorError): collector.validate_configured_startup_source_manifest(collector.PROVIDER_IO_MANIFEST)
        for count in (True, 278.0, 277):
            with self.assertRaises(collector.CollectorError): collector.validate_configured_startup_source_manifest(collector.CONFIGURED_STARTUP_MANIFEST, expected_count=count)

    def test_v18_sparse_consumers_require_metadata_module_and_controls(self):
        helper = WorkflowSparseSourceControls(); root = COLLECTOR_PATH.resolve().parents[2]
        for workflow, job in [('hosted.yml','phoenix'), ('identity-network.yml','identity-network'), ('verify.yml','services')]:
            patterns = helper.patterns((root/'.github/workflows'/workflow).read_text(), job)
            for name in ('selection.json', 'selected-source-manifest.json'):
                self.assertIn('/'+collector.CONFIGURED_STARTUP_SOURCE_BASE+name, patterns)
            with self.subTest(workflow=workflow), tempfile.TemporaryDirectory(prefix='identity-v18-') as directory:
                sparse = Path(directory); helper.materialize(root, sparse, patterns); helper.check_real_main(sparse)
                paths = [collector.CONFIGURED_STARTUP_SOURCE_BASE+n for n in ('selection.json','selected-source-manifest.json')]
                paths += ['hosted/lib/mixer_hosted/browser_auth/installation.ex', 'hosted/lib/mixer_hosted/browser_auth/supervisor.ex', 'hosted/scripts/check-configured-startup.exs']
                for path in paths:
                    target = sparse/path; body = target.read_bytes(); target.unlink()
                    try:
                        with self.assertRaises(FileNotFoundError): helper.check_real_main(sparse)
                    finally: target.write_bytes(body)

    def test_v18_production_constructor_job_uses_exact_script_and_test_inputs(self):
        root = COLLECTOR_PATH.resolve().parents[2]
        workflow = (root/'.github/workflows/hosted.yml').read_text()
        command = 'hosted/scripts/check-startup-secrets.exs hosted/deps/jason/lib'
        self.assertEqual(1, workflow.count(command))
        driver = (root/'hosted/scripts/check-startup-secrets.exs').read_text()
        self.assertIn('Mix.env(:prod)', driver)
        self.assertIn('hosted/lib/mixer_hosted/browser_auth/startup_secrets.ex', driver)
        self.assertIn('hosted/test/mixer_hosted/browser_auth/startup_secrets_test.exs', driver)
        self.assertIn('result.total != 8', driver)
        self.assertIn('result.skipped != 0', driver)



    def test_v18_configured_composition_driver_is_durable_and_workflow_bound(self):
        root = COLLECTOR_PATH.resolve().parents[2]
        path = 'hosted/scripts/check-configured-startup.exs'
        body = (root/path).read_bytes()
        self.assertEqual(collector.CONFIGURED_STARTUP_MANIFEST[path], collector._file_row(body))
        workflow = (root/'.github/workflows/hosted.yml').read_text()
        self.assertEqual(1, workflow.count(path+' hosted/deps/jason/lib'))
        self.assertIn(b'Mix.env(:prod)', body)
        self.assertIn(b'result.total != 15', body)
        self.assertIn(b'database_admission_proved: false', body)
        self.assertIn(b'fake_leaves:', body)
        self.assertEqual(7, body.count(b'  test "'))
        self.assertEqual('c9148d2e7547b6ee7eb3cae9851ebfabfb061f855fafcb364b143ec51b699e7e', collector.CONFIGURED_STARTUP_MANIFEST['hosted/lib/mixer_hosted/browser_auth/installation.ex']['sha256'])
        self.assertEqual('0be221930726bdc9b266de3ea4b703ebb4a74617dcd2b9fe51a806127c16fe50', collector.CONFIGURED_STARTUP_MANIFEST['hosted/lib/mixer_hosted/browser_auth/supervisor.ex']['sha256'])



if __name__ == "__main__":
    signal.alarm(50)
    unittest.main(verbosity=2)
