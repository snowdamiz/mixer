from pathlib import Path
p=Path('hosted/scripts/test_identity_network_collector.py');s=p.read_text()
s=s.replace('ELIXIR_REF = "hexpm/elixir@sha256:3571d320ec0656c38c76b4c362a8e0c0fd6f9b58cec6448a08e43a82940d4e43"','ELIXIR_REF = "hexpm/elixir@sha256:ed110657152803079f311913be4effe02874e2c714a1b5a38891873b7f2a16c5"')
s=s.replace('ELIXIR_CONFIG = "sha256:6631543fddfe053ddbd30435318916667d5da87b5f5ec0644893d146a539370e"','ELIXIR_CONFIG = "sha256:857e84a618d1f76390220fbff2e7d54d588aea4f772ab1e60dacfe3fa02602cc"')
needle='class ArchiveControls(unittest.TestCase):'
addition='''def exact_metadata():
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
              "openssl": "OpenSSL 3.0.22 CONTROL-PLACEHOLDER-DATE\\nplatform: debian-amd64\\n",
              "crypto": "pure-control-fixture-not-a-runtime-result",
              "crypto_libraries": [{"name": "OpenSSL", "number": 805306720, "version": "OpenSSL 3.0.22 CONTROL-PLACEHOLDER-DATE"}],
              "tools": copy.deepcopy(expected["tools"]), "versions": {"/usr/bin/tar": "tar (GNU tar) 1.34\\n"},
              "ca": {key: expected["ca"][key] for key in ("path", "bytes", "sha256")}}
    actual["ca"].update(load="explicit-selected-bundle", loaded_count=150, loaded_der_sha256=copy.deepcopy(expected["ca"]["der_sha256"]))
    return actual, expected


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


'''
assert needle in s;s=s.replace(needle,addition+needle);p.write_text(s)
