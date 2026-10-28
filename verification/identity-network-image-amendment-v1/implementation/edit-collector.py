from pathlib import Path
p=Path('hosted/scripts/test-identity-network.py');s=p.read_text()
s=s.replace('CONTRACT_PACKET = "a3a806d83e285213df4c0e951282686dcfcfa81701e8005040d5172b3300050d"','''CONTRACT_PACKET = "a3a806d83e285213df4c0e951282686dcfcfa81701e8005040d5172b3300050d"
CONTRACT_PACKET_SHA256 = "88e7b446e1470de0e1c54d770248ef6627a9bfb5623118d182a8dbd8b12c6c46"
CONTRACT_BASE = "verification/identity-production-network-contract/"
AMENDMENT_BASE = "verification/identity-network-image-amendment-v1/metadata/"
AMENDMENT_SHA256 = "6a2ec88721d89a28e40961f834b856598ba0f6f14d88708906cf3931e0e33afa"
AMENDMENT_PACKET = "9ddc12c8277b120dcd8ef7577dd9da03d245b8502802db85399a6f1104bcbdc8"
SOURCE_REVIEW_PACKET = "261023b77cb55255f666959f367330783a354174252ed23b71145566f87ba597"
OLD_TEST_IMAGE = {
    "ref": "hexpm/elixir@sha256:3571d320ec0656c38c76b4c362a8e0c0fd6f9b58cec6448a08e43a82940d4e43",
    "index": "sha256:52ec0f335b9084bcfc0ce3a29b4c0288dc2fc2a07658ff809dc7d07589212cde",
    "config": "sha256:6631543fddfe053ddbd30435318916667d5da87b5f5ec0644893d146a539370e",
    "platform": "linux/amd64",
}''')
s=s.replace('"ref": "hexpm/elixir@sha256:3571d320ec0656c38c76b4c362a8e0c0fd6f9b58cec6448a08e43a82940d4e43",\n        "config": "sha256:6631543fddfe053ddbd30435318916667d5da87b5f5ec0644893d146a539370e",','"ref": "hexpm/elixir@sha256:ed110657152803079f311913be4effe02874e2c714a1b5a38891873b7f2a16c5",\n        "config": "sha256:857e84a618d1f76390220fbff2e7d54d588aea4f772ab1e60dacfe3fa02602cc",')
needle='def validate_source_manifest(manifest, expected_digest=FROZEN_PRODUCT_DIGEST, expected_count=177):'
functions='''def _file_row(body):
    return {"bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()}


def validate_amendment_manifest(body):
    """The compiled root admits this one finite packet, never an overlay."""
    packet = json.loads(body)
    require(isinstance(packet, dict) and set(packet) == {"schema", "files", "tree_digest_sha256"} and type(packet["schema"]) is int and packet["schema"] == 1, "amendment packet shape")
    files = packet["files"]
    require(isinstance(files, dict) and len(files) == 78 and packet["tree_digest_sha256"] == AMENDMENT_PACKET and canonical_digest(files) == AMENDMENT_PACKET, "amendment packet seal mismatch")
    for path, row in files.items():
        name = PurePosixPath(path)
        require(not name.is_absolute() and ".." not in name.parts and str(name) == path and "\\\\" not in path and path != "packet-manifest.json", "unsafe amendment metadata path")
        require(isinstance(row, dict) and set(row) == {"bytes", "sha256"} and type(row["bytes"]) is int and 0 <= row["bytes"] <= MAX_COMMAND_BYTES and bool(re.fullmatch("[0-9a-f]{64}", row["sha256"])), "amendment metadata row shape")
    return files


def predecessor_metadata_paths():
    paths = [CONTRACT_BASE + "contract.json", CONTRACT_BASE + "packet-manifest.json"]
    for label in ("elixir", "postgres"):
        paths += [CONTRACT_BASE + "inputs/registry/" + label + suffix for suffix in ("-index.json", "-amd64-manifest.json", "-amd64-config.json")]
    return paths


def validate_selected_metadata(metadata):
    """Validate both immutable namespaces before any image/runtime operation."""
    require(isinstance(metadata, dict) and all(isinstance(body, bytes) for body in metadata.values()), "missing selected metadata")
    manifest_path = AMENDMENT_BASE + "packet-manifest.json"
    require(manifest_path in metadata, "missing amendment seal")
    files = validate_amendment_manifest(metadata[manifest_path])
    expected_paths = set(predecessor_metadata_paths()) | {manifest_path} | {AMENDMENT_BASE + path for path in files}
    require(set(metadata) == expected_paths, "missing or extra selected metadata")
    old_packet_body = metadata[CONTRACT_BASE + "packet-manifest.json"]
    require(hashlib.sha256(old_packet_body).hexdigest() == CONTRACT_PACKET_SHA256, "predecessor packet bytes mismatch")
    old_packet = json.loads(old_packet_body)
    require(old_packet["tree_digest_sha256"] == CONTRACT_PACKET and canonical_digest(old_packet["files"]) == CONTRACT_PACKET, "contract packet seal mismatch")
    require(hashlib.sha256(metadata[CONTRACT_BASE + "contract.json"]).hexdigest() == CONTRACT_SHA256, "selected predecessor contract drift")
    for path in predecessor_metadata_paths():
        if path != CONTRACT_BASE + "packet-manifest.json":
            require(old_packet["files"][path.removeprefix(CONTRACT_BASE)] == _file_row(metadata[path]), "frozen predecessor metadata hash mismatch")
    for path, expected in files.items():
        require(expected == _file_row(metadata[AMENDMENT_BASE + path]), "frozen amendment metadata hash mismatch")
    amendment_body = metadata[AMENDMENT_BASE + "image-amendment.json"]
    require(hashlib.sha256(amendment_body).hexdigest() == AMENDMENT_SHA256, "selected amendment drift")
    amendment = json.loads(amendment_body)
    require(set(amendment) == {"schema", "operation", "predecessor", "old_test_image", "test_image", "preserved", "prerequisites", "source_review"} and amendment["schema"] == 1 and amendment["operation"] == "replace-test-image-only", "amendment is not the closed image-only change")
    require(amendment["predecessor"] == {"contract_sha256": CONTRACT_SHA256, "packet_manifest_sha256": CONTRACT_PACKET_SHA256, "packet_tree_digest_sha256": CONTRACT_PACKET} and amendment["old_test_image"] == OLD_TEST_IMAGE, "amendment predecessor mismatch")
    new = {**IMAGES["test"], "index": "sha256:1ae099301985ddf8a723ad50cc25e37dd854497aec12cebf984c195570b0d83e", "platform": "linux/amd64", "tag": "hexpm/elixir:1.20.4-erlang-29.1.1-debian-bookworm-20261005-slim"}
    require(amendment["test_image"] == new, "amendment selected image mismatch")
    preserved = {"product_commit": PRODUCT_COMMIT, "product_files": 177, "product_digest": FROZEN_PRODUCT_DIGEST, "lock_sha256": FROZEN_LOCK_SHA256, "postgres": {**IMAGES["pg"], "index": "sha256:cb20a02549a06de2f9b115b934f44ba43593e11663163e1f18d13facb4750de4", "platform": "linux/amd64"}, "bootstrap": BOOTSTRAP, "test_roots": TEST_ROOTS, "contract_boundaries": "all-other-predecessor-contract-fields-unchanged"}
    require(canonical_digest(amendment["preserved"]) == canonical_digest(preserved), "amendment changed a preserved contract")
    review = amendment["source_review"]
    review_base = AMENDMENT_BASE + "source-review/"
    review_body = metadata[review_base + "packet-manifest.json"]
    require(review["relative_namespace"] == "source-review/" and hashlib.sha256(review_body).hexdigest() == review["packet_manifest_sha256"], "source review packet bytes mismatch")
    review_packet = json.loads(review_body)
    require(review["packet_tree_digest_sha256"] == SOURCE_REVIEW_PACKET and review_packet["tree_digest_sha256"] == SOURCE_REVIEW_PACKET and canonical_digest(review_packet["files"]) == SOURCE_REVIEW_PACKET, "source review seal mismatch")
    require({path.removeprefix(review_base) for path in metadata if path.startswith(review_base)} == set(review_packet["files"]) | {"packet-manifest.json"}, "source review membership mismatch")
    for path, expected in review_packet["files"].items():
        require(expected == _file_row(metadata[review_base + path]), "source review file drift")
    for base, label, image in ((CONTRACT_BASE, "elixir", OLD_TEST_IMAGE), (CONTRACT_BASE, "postgres", preserved["postgres"]), (AMENDMENT_BASE, "elixir", new)):
        blobs = {suffix: metadata[base + "inputs/registry/" + label + suffix + ".json"] for suffix in ("-index", "-amd64-manifest", "-amd64-config")}
        for suffix, expected in (("-index", image["index"]), ("-amd64-manifest", image["ref"].split("@")[1]), ("-amd64-config", image["config"])):
            require("sha256:" + hashlib.sha256(blobs[suffix]).hexdigest() == expected, "static image metadata pin mismatch")
        index, manifest, config = (json.loads(blobs[suffix]) for suffix in ("-index", "-amd64-manifest", "-amd64-config"))
        candidates = [entry for entry in index["manifests"] if entry.get("platform") == {"architecture": "amd64", "os": "linux"}]
        require(len(candidates) == 1 and candidates[0]["digest"] == image["ref"].split("@")[1] and manifest["config"]["digest"] == image["config"] and config["os"] == "linux" and config["architecture"] == "amd64", "image index/child/config relation mismatch")
    capabilities = json.loads(metadata[review_base + "analysis/capabilities.json"])
    tools = amendment["prerequisites"]["tools"]
    expected_tools = {row["requested"]: {key: row["object"][key] for key in ("bytes", "sha256")} for row in capabilities["required_objects"] if row["requested"] in tools}
    require(len(tools) == 7 and tools == expected_tools, "prerequisite source tool binding mismatch")
    ca = amendment["prerequisites"]["ca"]
    require({key: ca[key] for key in ("path", "bytes", "sha256")} == {key: capabilities["ca_bundle"][key] for key in ("path", "bytes", "sha256")} and ca["der_sha256"] == sorted(row["der_sha256"] for row in capabilities["ca_bundle"]["certificates"]), "prerequisite CA source binding mismatch")
    return amendment


def validate_prerequisites(observed, expected):
    require(isinstance(observed, dict), "actual prerequisite result missing")
    required = {"elixir", "otp_patch", "mix", "openssl", "crypto", "crypto_libraries", "tools", "versions", "ca"}
    require(set(observed) == required, "actual prerequisite result incomplete")
    require(observed["elixir"] == expected["elixir"] and observed["otp_patch"] == expected["otp_patch"], "actual VM prerequisite version mismatch")
    require(isinstance(observed["mix"], str) and "Mix 1.20.4" in observed["mix"] and len(observed["mix"]) < 65536, "actual Mix version missing")
    require(isinstance(observed["openssl"], str) and observed["openssl"].startswith(expected["openssl_version_prefix"]) and len(observed["openssl"]) < 65536, "actual OpenSSL version mismatch")
    require(isinstance(observed["crypto"], str) and 0 < len(observed["crypto"]) < 65536, "actual crypto identity missing")
    libraries = observed["crypto_libraries"]
    require(isinstance(libraries, list) and len(libraries) == 1, "actual crypto library identity missing")
    library = libraries[0]
    require(isinstance(library, dict) and set(library) == {"name", "number", "version"} and library["name"] == expected["crypto_library"]["name"] and type(library["number"]) is int and library["number"] > 0 and isinstance(library["version"], str) and library["version"].startswith(expected["crypto_library"]["version_prefix"]) and len(library["version"]) < 65536, "actual crypto library version mismatch")
    require(canonical_digest(observed["tools"]) == canonical_digest(expected["tools"]), "actual executable bytes differ from source inventory")
    versions = observed["versions"]
    require(isinstance(versions, dict) and set(versions) == {"/usr/bin/tar"} and isinstance(versions["/usr/bin/tar"], str) and versions["/usr/bin/tar"].startswith("tar (GNU tar) 1.34") and len(versions["/usr/bin/tar"]) < 65536, "actual tar version missing")
    ca = observed["ca"]
    expected_ca = expected["ca"]
    require(isinstance(ca, dict) and set(ca) == {"path", "bytes", "sha256", "load", "loaded_count", "loaded_der_sha256"}, "actual CA observation missing")
    require(canonical_digest({key: ca[key] for key in ("path", "bytes", "sha256")}) == canonical_digest({key: expected_ca[key] for key in ("path", "bytes", "sha256")}), "actual CA bundle mismatch")
    require(ca["load"] == "explicit-selected-bundle" and type(ca["loaded_count"]) is int and ca["loaded_count"] > 0 and ca["loaded_count"] == len(expected_ca["der_sha256"]) and ca["loaded_der_sha256"] == expected_ca["der_sha256"], "actual loaded OS roots missing or differ from selected bundle")
    return observed


'''
assert needle in s;s=s.replace(needle,functions+needle)
start=s.index('PREREQUISITES_EXS = r');end=s.index('\nMANIFEST_EXS = r',start)
s=s[:start]+'''PREREQUISITES_EXS = r\'\'\'
emit = fn value -> IO.puts("IDENTITY_JSON=" <> IO.iodata_to_binary(:json.encode(value))) end
hash = fn path -> :crypto.hash(:sha256, File.read!(path)) |> Base.encode16(case: :lower) end
tools = ["/usr/bin/env", "/usr/bin/tar", "/usr/bin/openssl", "/usr/local/bin/elixir", "/usr/local/bin/mix", "/usr/local/bin/erl", "/usr/local/bin/escript"]
rows = Map.new(tools, fn path ->
  %{type: :regular, mode: mode, size: size} = File.stat!(path)
  true = Bitwise.band(mode, 0o111) != 0
  {path, %{"sha256" => hash.(path), "bytes" => size}}
end)
"/usr/bin/openssl" = System.find_executable("openssl")
"1.20.4" = System.version()
"29" = to_string(:erlang.system_info(:otp_release))
otp_path = Path.join([to_string(:code.root_dir()), "releases", "29", "OTP_VERSION"])
"29.1.1" = File.read!(otp_path) |> String.trim()
{mix, 0} = System.cmd("/usr/local/bin/mix", ["--version"], stderr_to_stdout: true)
true = String.contains?(mix, "Mix 1.20.4")
{openssl, 0} = System.cmd("/usr/bin/openssl", ["version", "-a"], stderr_to_stdout: true)
true = String.starts_with?(openssl, "OpenSSL 3.0.22 ")
{tar, 0} = System.cmd("/usr/bin/tar", ["--version"], stderr_to_stdout: true)
true = byte_size(tar) < 65536 and String.starts_with?(tar, "tar (GNU tar) 1.34")
{:ok, _} = Application.ensure_all_started(:ssl)
ca_path = "/etc/ssl/certs/ca-certificates.crt"
%{type: :regular, size: 224449} = File.stat!(ca_path)
"714d457d580922dbf1d0be8bd35ba236a842b50b0072ae791582a19adef772a5" = hash.(ca_path)
:ok = :public_key.cacerts_load(ca_path)
roots = :public_key.cacerts_get()
true = is_list(roots) and length(roots) > 0
root_hashes = Enum.map(roots, fn {:cert, der, _decoded} -> :crypto.hash(:sha256, der) |> Base.encode16(case: :lower) end) |> Enum.sort()
bundle_hashes = Enum.map(:public_key.pem_decode(File.read!(ca_path)), fn {:Certificate, der, :not_encrypted} -> :crypto.hash(:sha256, der) |> Base.encode16(case: :lower) end) |> Enum.sort()
true = root_hashes == bundle_hashes
libraries = Enum.map(:crypto.info_lib(), fn {name, number, version} -> %{"name" => to_string(name), "number" => number, "version" => to_string(version)} end)
[%{"name" => "OpenSSL", "number" => number, "version" => crypto_version}] = libraries
true = is_integer(number) and number > 0 and String.starts_with?(crypto_version, "OpenSSL 3.0.22 ")
ca = %{"path" => ca_path, "bytes" => 224449, "sha256" => hash.(ca_path), "load" => "explicit-selected-bundle", "loaded_count" => length(roots), "loaded_der_sha256" => root_hashes}
versions = %{"/usr/bin/tar" => tar}
emit.(%{"elixir" => System.version(), "otp_patch" => File.read!(otp_path) |> String.trim(), "mix" => mix, "openssl" => openssl, "crypto" => inspect(:crypto.info_lib()), "crypto_libraries" => libraries, "tools" => rows, "versions" => versions, "ca" => ca})
\'\'\'
''' +s[end:]
old='''    {:ok, _} = Application.ensure_all_started(:ssl)
    for path <- ["/workspace/home", "/workspace/tooling/mix", "/workspace/tooling/hex", "/workspace/cache", "/workspace/downloads", "/workspace/evidence"], do: File.mkdir_p!(path)'''
new='''    {:ok, _} = Application.ensure_all_started(:ssl)
    ca_path = "/etc/ssl/certs/ca-certificates.crt"
    %{type: :regular, size: 224449} = File.stat!(ca_path)
    "714d457d580922dbf1d0be8bd35ba236a842b50b0072ae791582a19adef772a5" = Base.encode16(:crypto.hash(:sha256, File.read!(ca_path)), case: :lower)
    :ok = :public_key.cacerts_load(ca_path)
    true = length(:public_key.cacerts_get()) > 0
    for path <- ["/workspace/home", "/workspace/tooling/mix", "/workspace/tooling/hex", "/workspace/cache", "/workspace/downloads", "/workspace/evidence"], do: File.mkdir_p!(path)'''
assert old in s;s=s.replace(old,new)
start=s.index('        packet_base = "verification/identity-production-network-contract/"');end=s.index('        write_json(self.output / "host.json"',start)
s=s[:start]+'''        amendment_manifest = self.git_blobs([AMENDMENT_BASE + "packet-manifest.json"])
        amendment_files = validate_amendment_manifest(amendment_manifest[AMENDMENT_BASE + "packet-manifest.json"])
        metadata = {**amendment_manifest, **self.git_blobs(predecessor_metadata_paths() + [AMENDMENT_BASE + path for path in amendment_files])}
        amendment = validate_selected_metadata(metadata)
        self.prerequisites = amendment["prerequisites"]
        self.state["source"].update(predecessor_contract_sha256=CONTRACT_SHA256, predecessor_packet_sha256=CONTRACT_PACKET, image_amendment_sha256=AMENDMENT_SHA256, image_amendment_packet_sha256=AMENDMENT_PACKET, image_source_review_packet_sha256=SOURCE_REVIEW_PACKET)
        self.persist()
        (self.output / "selected-contract-metadata.tar").write_bytes(source_tar(metadata))
''' +s[end:]
s=s.replace('''        prerequisite_output, _, _ = self.execute(prepare, ["/usr/local/bin/elixir", "/workspace/collector-prerequisites.exs"])
        write_json(self.output / "bootstrap-plan.json"''','''        prerequisite_output, _, _ = self.execute(prepare, ["/usr/local/bin/elixir", "/workspace/collector-prerequisites.exs"])
        write_json(self.output / "prepare-prerequisites.json", validate_prerequisites(json_marker(prerequisite_output), self.prerequisites))
        write_json(self.output / "bootstrap-plan.json"''')
s=s.replace('        write_json(self.output / "prepare-prerequisites.json", json_marker(prerequisite_output))\n','')
s=s.replace('write_json(self.output / "test-prerequisites.json", json_marker(actual_prerequisites))','write_json(self.output / "test-prerequisites.json", validate_prerequisites(json_marker(actual_prerequisites), self.prerequisites))')
p.write_text(s)
