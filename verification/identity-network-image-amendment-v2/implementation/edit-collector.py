from pathlib import Path
import json,pprint
p=Path('hosted/scripts/test-identity-network.py');s=p.read_text();contract=json.loads(Path('verification/identity-network-image-amendment-v2/metadata/execution-amendment.json').read_bytes())
needle='SOURCE_REVIEW_PACKET = '
pos=s.index('\n',s.index(needle))
s=s[:pos+1]+'''EXECUTION_BASE = "verification/identity-network-image-amendment-v2/metadata/"
EXECUTION_SHA256 = "47823fe3c64997a1976bd159507dee5be9f2153c7a69d137d8fb8ba40a9b0ed8"
EXECUTION_PACKET = "dd6e4ed475f2ff7649d559b6ad02101dff641b9b2679666542487e6f30f76da4"
'''+s[pos+1:]
start=s.index('TMPFS = {');end=s.index('\nCAPS = ',start)
s=s[:start]+'OLD_TMPFS = '+pprint.pformat(contract['old_tmpfs'],sort_dicts=True)+'\nTMPFS = '+pprint.pformat(contract['new_tmpfs'],sort_dicts=True)+'\nMOUNT_POLICY = '+pprint.pformat(contract['mount_observation'],sort_dicts=True)+s[end:]
needle='def validate_prerequisites(observed, expected):'
functions='''def validate_execution_manifest(body):
    packet = json.loads(body)
    require(isinstance(packet, dict) and set(packet) == {"schema", "files", "tree_digest_sha256"} and type(packet["schema"]) is int and packet["schema"] == 1, "execution amendment packet shape")
    files = packet["files"]
    require(isinstance(files, dict) and len(files) == 16 and packet["tree_digest_sha256"] == EXECUTION_PACKET and canonical_digest(files) == EXECUTION_PACKET, "execution amendment packet seal mismatch")
    for path, row in files.items():
        name = PurePosixPath(path)
        require(not name.is_absolute() and ".." not in name.parts and str(name) == path and "\\\\" not in path and path != "packet-manifest.json", "unsafe execution amendment path")
        require(isinstance(row, dict) and set(row) == {"bytes", "sha256"} and type(row["bytes"]) is int and 0 <= row["bytes"] <= MAX_COMMAND_BYTES and bool(re.fullmatch("[0-9a-f]{64}", row["sha256"])), "execution amendment row shape")
    return files


def validate_execution_contract(value, image_amendment):
    require(isinstance(value, dict) and set(value) == {"schema", "operation", "base_contract", "prior_amendment", "old_tmpfs", "new_tmpfs", "workspace_partition", "preserved", "mount_observation", "runtime_basis", "proof_files"} and type(value["schema"]) is int and value["schema"] == 1 and value["operation"] == "carve-bounded-executable-tooling-tmpfs", "execution amendment is not the closed tooling carve")
    require(value["base_contract"] == image_amendment["predecessor"] and value["prior_amendment"] == {"path": AMENDMENT_BASE, "amendment_sha256": AMENDMENT_SHA256, "packet_tree_digest_sha256": AMENDMENT_PACKET}, "execution amendment predecessor mismatch")
    require(canonical_digest(value["old_tmpfs"]) == canonical_digest(OLD_TMPFS) and canonical_digest(value["new_tmpfs"]) == canonical_digest(TMPFS), "execution amendment tmpfs table mismatch")
    partition = {"total_bytes": 1073741824, "workspace_bytes": 1006632960, "tooling_bytes": 67108864, "roles": ["prepare", "test"], "tooling_path": "/workspace/tooling"}
    require(canonical_digest(value["workspace_partition"]) == canonical_digest(partition) and partition["workspace_bytes"] + partition["tooling_bytes"] == partition["total_bytes"], "execution amendment workspace carve mismatch")
    preserved = {"test_image": image_amendment["test_image"], "prerequisites": image_amendment["prerequisites"], "product_pg_bootstrap_contract": image_amendment["preserved"], "resources": RESOURCES, "capabilities": {role: sorted(caps) for role, caps in CAPS.items()}}
    require(canonical_digest(value["preserved"]) == canonical_digest(preserved), "execution amendment changed an invariant")
    require(canonical_digest(value["mount_observation"]) == canonical_digest(MOUNT_POLICY), "execution amendment mount observation policy mismatch")
    basis = value["runtime_basis"]
    require(basis["run_id"] == 40740023326 and basis["artifact_id"] == 12837649788 and basis["delivery_revision"] == "cc350d3303ca71c5d57e87846f6a61304b658fa7" and basis["artifact_tree_digest_sha256"] == "616274ea3bccd45a7b506a0b71de1016b004cbe55e9ca5f3da9fb2cfb9d394bf" and basis["artifact_zip_sha256"] == "932f877ed0fc8cf8ad9457e0ba1b4888ff7bd5a58762b86975f6e887f9673231" and basis["failed_command"] == 22 and basis["source_supported_noexec_inference"] is True and basis["actual_prior_mountinfo"] is False, "execution amendment prior runtime basis mismatch")
    return value


def validate_execution_metadata(metadata):
    require(isinstance(metadata, dict) and EXECUTION_BASE + "packet-manifest.json" in metadata, "missing execution amendment seal")
    files = validate_execution_manifest(metadata[EXECUTION_BASE + "packet-manifest.json"])
    selected_paths = {EXECUTION_BASE + path for path in files} | {EXECUTION_BASE + "packet-manifest.json"}
    require({path for path in metadata if path.startswith(EXECUTION_BASE)} == selected_paths, "missing or extra execution amendment metadata")
    image_amendment = validate_selected_metadata({path: body for path, body in metadata.items() if not path.startswith(EXECUTION_BASE)})
    for path, expected in files.items():
        require(isinstance(metadata[EXECUTION_BASE + path], bytes) and expected == _file_row(metadata[EXECUTION_BASE + path]), "execution amendment metadata hash mismatch")
    body = metadata[EXECUTION_BASE + "execution-amendment.json"]
    require(hashlib.sha256(body).hexdigest() == EXECUTION_SHA256, "selected execution amendment drift")
    value = validate_execution_contract(json.loads(body), image_amendment)
    require(value["proof_files"] == {path: row for path, row in files.items() if path != "execution-amendment.json"}, "execution amendment proof membership mismatch")
    for name in ("image-amendment.json", "packet-manifest.json"):
        require(metadata[EXECUTION_BASE + "proof/prior-v1/" + name] == metadata[AMENDMENT_BASE + name], "execution amendment prior raw proof mismatch")
    proof = EXECUTION_BASE + "proof/runtime/selected/artifact/"
    artifact = json.loads(metadata[proof + "artifact-manifest.json"])
    require(artifact["tree_digest_sha256"] == value["runtime_basis"]["artifact_tree_digest_sha256"] and canonical_digest(artifact["files"]) == artifact["tree_digest_sha256"], "prior failed artifact seal mismatch")
    for name in ("prepare-prerequisites.json", "logs/0022.json", "logs/0022.stderr", "bootstrap-plan.json"):
        require(artifact["files"][name] == _file_row(metadata[proof + name]), "prior failed artifact proof drift")
    reference = value["runtime_basis"]["prerequisite_receipt_reference"]
    require(reference == {"original_path": "verification/github-delivery-blocker-campaign/network-review/selected/artifact/prepare-prerequisites.json", "packet_path": "proof/runtime/selected/artifact/prepare-prerequisites.json", **_file_row(metadata[proof + "prepare-prerequisites.json"])}, "prior actual prerequisite reference mismatch")
    validate_prerequisites(json.loads(metadata[proof + "prepare-prerequisites.json"]), image_amendment["prerequisites"])
    failure = json.loads(metadata[proof + "logs/0022.json"])
    require(failure["exit_code"] == 1 and failure["stdout_complete"] is False and failure["stderr_complete"] is False and failure["timed_out"] is False and b":eacces" in metadata[proof + "logs/0022.stderr"], "prior failed command facts changed")
    return value


def validate_mount_observation(role, observed):
    require(role in {"prepare", "test"} and isinstance(observed, dict) and set(observed) == {"role", "source", "read_bytes", "read_sha256", "selected_lines", "path_modes"}, "actual mount observation missing or malformed")
    require(observed["role"] == role and observed["source"] == MOUNT_POLICY["source"] and type(observed["read_bytes"]) is int and 0 < observed["read_bytes"] <= MOUNT_POLICY["max_bytes"] and isinstance(observed["read_sha256"], str) and bool(re.fullmatch("[0-9a-f]{64}", observed["read_sha256"])), "actual mount observation source/bound mismatch")
    paths = MOUNT_POLICY["roles"][role]
    lines = observed["selected_lines"]
    require(isinstance(lines, list) and len(lines) == len(paths), "actual selected mounts missing or extra descendants")
    require(canonical_digest(observed["path_modes"]) == canonical_digest({path: MOUNT_POLICY["modes"][path] for path in paths}), "actual selected mount mode mismatch")
    entries = {}
    for line in lines:
        require(isinstance(line, str) and 0 < len(line.encode()) <= MOUNT_POLICY["max_selected_line_bytes"] and not any(char in line for char in "\\n\\r\\t") and line.count(" - ") == 1, "actual mountinfo line malformed")
        left, right = line.split(" - ")
        fields, filesystem = left.split(), right.split()
        require(len(fields) >= 6 and len(filesystem) == 3 and all(re.fullmatch("[0-9]+", fields[index]) and int(fields[index]) > 0 for index in (0, 1)) and bool(re.fullmatch("[0-9]+:[0-9]+", fields[2])) and fields[3] == "/", "actual mountinfo identity malformed")
        path = fields[4]
        require(path in paths and path not in entries and filesystem[:2] == ["tmpfs", "tmpfs"], "actual mountpoint absent, duplicate, descendant or non-tmpfs")
        flags, super_flags = fields[5].split(","), filesystem[2].split(",")
        require(len(set(flags)) == len(flags) and len(set(super_flags)) == len(super_flags) and all(flags) and all(super_flags), "duplicate or empty actual mount options")
        combined = set(flags) | set(super_flags)
        require({"rw", "nosuid", "nodev"} <= set(flags) and not ({"ro", "suid", "dev"} & combined) and "rw" in super_flags, "actual mount security flags mismatch")
        require(("noexec" not in combined) if path == "/workspace/tooling" else ("noexec" in flags and "exec" not in combined), "actual mount execution policy mismatch")
        sizes = [option.removeprefix("size=") for option in super_flags if option.startswith("size=")]
        require(len(sizes) == 1 and bool(re.fullmatch(r"[0-9]+[kKmMgG]?", sizes[0])), "actual tmpfs size missing or ambiguous")
        text = sizes[0]
        scale = {"k": 1024, "m": 1048576, "g": 1073741824}
        size = int(text[:-1]) * scale[text[-1].lower()] if text[-1].isalpha() else int(text)
        expected = next(option.removeprefix("size=") for option in TMPFS[role][path].split(",") if option.startswith("size="))
        require(size == int(expected), "actual tmpfs size mismatch")
        entries[path] = {"id": fields[0], "parent": fields[1]}
    require(set(entries) == set(paths) and entries["/workspace/tooling"]["parent"] == entries["/workspace"]["id"] and len({entry["id"] for entry in entries.values()}) == len(entries), "actual selected mount hierarchy mismatch")
    require(observed["read_bytes"] >= sum(len(line.encode()) + 1 for line in lines), "actual mount observation byte count inconsistent")
    return observed


'''
assert needle in s;s=s.replace(needle,functions+needle)
helper='''MOUNTS_EXS = r\'\'\'
[role] = System.argv()
paths = case role do
  "prepare" -> ["/workspace", "/workspace/tooling", "/tmp"]
  "test" -> ["/workspace", "/workspace/tooling", "/tmp", "/run"]
end
source = "/proc/self/mountinfo"
{:ok, io} = File.open(source, [:read, :binary])
bytes = try do
  data = IO.binread(io, 65_537)
  true = is_binary(data) and byte_size(data) > 0 and byte_size(data) <= 65_536
  data
finally
  :ok = File.close(io)
end
lines = String.split(bytes, "\\n", trim: true)
true = length(lines) <= 1024
selected = Enum.filter(lines, fn line ->
  [_id, _parent, _device, _root, path, _flags | _] = String.split(line)
  Enum.any?(paths, fn selected_path -> path == selected_path or String.starts_with?(path, selected_path <> "/") end)
end)
true = length(selected) <= 32 and Enum.all?(selected, &(byte_size(&1) <= 4096))
modes = Map.new(paths, fn path ->
  %{type: :directory, mode: mode} = File.stat!(path)
  {path, Bitwise.band(mode, 0o7777)}
end)
result = %{"role" => role, "source" => source, "read_bytes" => byte_size(bytes), "read_sha256" => Base.encode16(:crypto.hash(:sha256, bytes), case: :lower), "selected_lines" => selected, "path_modes" => modes}
IO.puts("IDENTITY_JSON=" <> IO.iodata_to_binary(:json.encode(result)))
\'\'\'


'''
assert 'PREREQUISITES_EXS = r' in s;s=s.replace('PREREQUISITES_EXS = r',helper+'PREREQUISITES_EXS = r',1)
# Elixir uses `after` for try cleanup, never Python's finally.
s=s.replace('  data\nfinally\n  :ok = File.close(io)','  data\nafter\n  :ok = File.close(io)')
s=s.replace('"collector-prerequisites.exs", "collector-bootstrap.exs", "collector-manifest.exs", "collector-netns.exs", "collector-observer.exs", "frozen-manifest.json"','"collector-prerequisites.exs", "collector-bootstrap.exs", "collector-manifest.exs", "collector-netns.exs", "collector-observer.exs", "collector-mounts.exs", "frozen-manifest.json"')
s=s.replace('"collector-observer.exs": OBSERVER_EXS.encode(), "frozen-manifest.json"','"collector-observer.exs": OBSERVER_EXS.encode(), "collector-mounts.exs": MOUNTS_EXS.encode(), "frozen-manifest.json"')
# The complete previous metadata namespace is still validated first.
s=s.replace('''        amendment = validate_selected_metadata(metadata)
        self.prerequisites''','''        amendment = validate_selected_metadata(metadata)
        execution_manifest = self.git_blobs([EXECUTION_BASE + "packet-manifest.json"])
        execution_files = validate_execution_manifest(execution_manifest[EXECUTION_BASE + "packet-manifest.json"])
        metadata.update(execution_manifest)
        metadata.update(self.git_blobs([EXECUTION_BASE + path for path in execution_files]))
        validate_execution_metadata(metadata)
        self.prerequisites''')
s=s.replace('''image_source_review_packet_sha256=SOURCE_REVIEW_PACKET)''','''image_source_review_packet_sha256=SOURCE_REVIEW_PACKET, execution_amendment_sha256=EXECUTION_SHA256, execution_amendment_packet_sha256=EXECUTION_PACKET)''')
needle='''    def collect(self):'''
method='''    def observe_mounts(self, owned):
        require(owned.role in {"prepare", "test"}, "mount observation role refused")
        output, _, _ = self.execute(owned, ["/usr/local/bin/elixir", "/workspace/collector-mounts.exs", owned.role], 15, limit=65536)
        observed = validate_mount_observation(owned.role, json_marker(output))
        write_json(self.output / (owned.role + "-mount-policy.json"), observed)
        return observed

'''
assert needle in s;s=s.replace(needle,method+needle)
s=s.replace('''        self.copy_in(prepare, source_tar({**product, **helpers}))
        prerequisite_output''','''        self.copy_in(prepare, source_tar({**product, **helpers}))
        self.observe_mounts(prepare)
        prerequisite_output''')
s=s.replace('''        self.copy_in(test, prepared)
        self.execute(test''','''        self.copy_in(test, prepared)
        self.observe_mounts(test)
        self.execute(test''')
s=s.replace('''"prerequisites_observed": True, "assertions_before_flag": True''','''"prerequisites_observed": True, "mount_policy_observed": True, "assertions_before_flag": True''')
p.write_text(s)
