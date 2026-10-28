from pathlib import Path
import json,pprint
p=Path('hosted/scripts/test-identity-network.py');s=p.read_text();v=json.loads(Path('verification/identity-network-image-amendment-v2/metadata/execution-amendment.json').read_bytes())
s=s.replace('47823fe3c64997a1976bd159507dee5be9f2153c7a69d137d8fb8ba40a9b0ed8','b447fe5919c4e73d86aee4da707570127de2c35ecdae5a7b90b0163eb9bc436c').replace('dd6e4ed475f2ff7649d559b6ad02101dff641b9b2679666542487e6f30f76da4','0e35cd6dcc1685b16745def4fe0217fc60e5d703c95a5cddbfd2409381c63b6d').replace('b11f314c7a5f39b43fc8cca00650bc93316b138f8e95a1d4d5b662ce60f8619f','dcac91f5cae0a2495f79448a76098975edc18db0ce96a1e769106244a0cf8061')
s=s.replace('\nCAPS = ','\nREBAR_TRANSFER = '+pprint.pformat(v['bootstrap_transfer'],sort_dicts=True)+'\nCAPS = ',1)
s=s.replace('''"mount_observation", "runtime_basis", "proof_files"}''','''"mount_observation", "bootstrap_transfer", "runtime_basis", "proof_files"}''')
s=s.replace('''    basis = value["runtime_basis"]''','''    require(canonical_digest(value["bootstrap_transfer"]) == canonical_digest(REBAR_TRANSFER) and REBAR_TRANSFER["sha512"] == BOOTSTRAP["rebar"]["sha512"], "execution amendment bootstrap transfer mismatch")
    basis = value["runtime_basis"]''')
needle='def validate_mount_observation(role, observed):'
transfer='''def validate_rebar_transfer(observed, download):
    require(isinstance(observed, dict) and set(observed) == {"source", "destination", "download_bytes", "copied_bytes", "target_bytes", "sha512", "exclusive_create", "closed_before_hash", "owned_download_removed"}, "actual Rebar transfer result missing")
    require(observed["source"] == REBAR_TRANSFER["source"] and observed["destination"] == REBAR_TRANSFER["destination"], "actual Rebar transfer paths mismatch")
    for key in ("download_bytes", "copied_bytes", "target_bytes"):
        require(type(observed[key]) is int and 0 < observed[key] <= REBAR_TRANSFER["max_bytes"], "actual Rebar transfer byte bound")
    require(observed["download_bytes"] == observed["copied_bytes"] == observed["target_bytes"] and observed["sha512"] == BOOTSTRAP["rebar"]["sha512"], "actual Rebar transfer short copy or checksum mismatch")
    require(all(observed[key] is True for key in ("exclusive_create", "closed_before_hash", "owned_download_removed")), "actual Rebar transfer incomplete or not exclusive")
    require(isinstance(download, dict) and type(download.get("bytes")) is int and download["bytes"] == observed["download_bytes"] and download.get("sha512") == observed["sha512"] and download.get("url") == BOOTSTRAP["rebar"]["url"], "actual Rebar transfer not joined to verified download")
    return observed


'''
assert needle in s;s=s.replace(needle,transfer+needle)
old='''    File.rename!("/workspace/downloads/rebar3", "/workspace/tooling/rebar3")
    File.chmod!("/workspace/tooling/rebar3", 0o755)'''
new='''    source = "/workspace/downloads/rebar3"
    target = "/workspace/tooling/rebar3"
    %{type: :regular, size: source_bytes} = File.stat!(source)
    true = source_bytes > 0 and source_bytes <= 16_777_216
    rebar_bytes = File.read!(source)
    ^source_bytes = byte_size(rebar_bytes)
    "REBAR_SHA" = Base.encode16(:crypto.hash(:sha512, rebar_bytes), case: :lower)
    false = File.exists?(target)
    {:ok, target_io} = File.open(target, [:write, :binary, :exclusive])
    try do
      :ok = IO.binwrite(target_io, rebar_bytes)
    after
      :ok = File.close(target_io)
    end
    %{type: :regular, size: ^source_bytes} = File.stat!(target)
    target_sha = Base.encode16(:crypto.hash(:sha512, File.read!(target)), case: :lower)
    "REBAR_SHA" = target_sha
    :ok = File.rm(source)
    false = File.exists?(source)
    transfer = %{"source" => source, "destination" => target, "download_bytes" => source_bytes, "copied_bytes" => byte_size(rebar_bytes), "target_bytes" => File.stat!(target).size, "sha512" => target_sha, "exclusive_create" => true, "closed_before_hash" => true, "owned_download_removed" => true}
    File.chmod!("/workspace/tooling/rebar3", 0o755)'''
assert old in s;s=s.replace(old,new)
s=s.replace('''"exact_rebar_path" => System.fetch_env!("MIX_REBAR3")}''','''"exact_rebar_path" => System.fetch_env!("MIX_REBAR3"), "rebar_transfer" => transfer}''')
s=s.replace('''        write_json(self.output / "bootstrap-observed.json", json_marker(bootstrap))''','''        bootstrap_result = json_marker(bootstrap)
        validate_rebar_transfer(bootstrap_result.get("rebar_transfer"), bootstrap_result.get("rebar"))
        write_json(self.output / "bootstrap-observed.json", bootstrap_result)''')
p.write_text(s)
p=Path('hosted/scripts/test_identity_network_collector.py');s=p.read_text();s=s.replace('47823fe3c64997a1976bd159507dee5be9f2153c7a69d137d8fb8ba40a9b0ed8','b447fe5919c4e73d86aee4da707570127de2c35ecdae5a7b90b0163eb9bc436c').replace('dd6e4ed475f2ff7649d559b6ad02101dff641b9b2679666542487e6f30f76da4','0e35cd6dcc1685b16745def4fe0217fc60e5d703c95a5cddbfd2409381c63b6d')
needle='class ActualMountControls(unittest.TestCase):'
tests='''class RebarTransferControls(unittest.TestCase):
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


'''
assert needle in s;s=s.replace(needle,tests+needle);p.write_text(s)
