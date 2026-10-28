from pathlib import Path
p=Path('hosted/scripts/test_identity_network_collector.py');s=p.read_text()
s=s.replace('''        tmpfs["/workspace"] = "rw,nosuid,nodev,size=1073741824,mode=0755"''','''        tmpfs["/tmp"] = "rw,nosuid,nodev,noexec,size=67108864,mode=1777"
        tmpfs["/workspace"] = "rw,nosuid,nodev,noexec,size=1006632960,mode=0755"
        tmpfs["/workspace/tooling"] = "rw,nosuid,nodev,exec,size=67108864,mode=0755"''')
s=s.replace('''            "collector-observer.exs": b"observer fixture",''','''            "collector-observer.exs": b"observer fixture",
            "collector-mounts.exs": b"mounts fixture",''')
s=s.replace('''NETNS_EXS="netns fixture", OBSERVER_EXS="observer fixture"):''','''NETNS_EXS="netns fixture", OBSERVER_EXS="observer fixture", MOUNTS_EXS="mounts fixture"):''')
needle='class ImageAmendmentControls(unittest.TestCase):'
helpers='''def exact_execution_metadata():
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


'''
assert needle in s;s=s.replace(needle,helpers+needle)
needle='class PrerequisiteControls(unittest.TestCase):'
controls='''class ExecutionAmendmentControls(unittest.TestCase):
    def test_closed_execution_contract_binds_prior_actual_prerequisites_and_same_image(self):
        self.assertEqual("47823fe3c64997a1976bd159507dee5be9f2153c7a69d137d8fb8ba40a9b0ed8", collector.EXECUTION_SHA256)
        self.assertEqual("dd6e4ed475f2ff7649d559b6ad02101dff641b9b2679666542487e6f30f76da4", collector.EXECUTION_PACKET)
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


'''
assert needle in s;s=s.replace(needle,controls+needle)
# V1's direct prerequisite gate is retained; the new independent mount gate is
# explicitly represented before it in this orchestration fixture.
s=s.replace('''subject, calls = self._amendment_preflight_subject(directory, exact_metadata())''','''subject, calls = self._amendment_preflight_subject(directory, exact_execution_metadata())''')
s=s.replace('''mock.patch.object(subject, "docker"), mock.patch.object(subject, "copy_in"), \\
                    mock.patch.object(subject, "execute", return_value=(b"IDENTITY_JSON={}\\n", b"", 0)) as execute:''','''mock.patch.object(subject, "docker"), mock.patch.object(subject, "copy_in"), \\
                    mock.patch.object(subject, "observe_mounts", return_value=exact_mounts("prepare")), \\
                    mock.patch.object(subject, "execute", return_value=(b"IDENTITY_JSON={}\\n", b"", 0)) as execute:''')
needle='class BudgetAndCommandControls(unittest.TestCase):'
wiring='''    def test_collect_requires_v2_execution_seal_before_any_image_operation(self):
        metadata = exact_execution_metadata()
        metadata.pop("verification/identity-network-image-amendment-v2/metadata/packet-manifest.json")
        with tempfile.TemporaryDirectory(prefix="identity-controls-") as directory:
            subject, calls = self._amendment_preflight_subject(directory, metadata)
            with mock.patch.dict("os.environ", {"GITHUB_ACTIONS": "true", "RUNNER_OS": "Linux", "RUNNER_ARCH": "X64"}, clear=True), \\
                    mock.patch.object(collector.os, "uname", return_value=collector.os.uname_result(("Linux", "control", "0", "0", "x86_64"))), \\
                    mock.patch.object(collector, "validate_source_manifest", return_value=collector.FROZEN_MANIFEST), \\
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
                output = b"IDENTITY_JSON=" + json.dumps(value).encode() + b"\\n"
                with mock.patch.object(subject, "execute", return_value=(output, b"", 0)) as execute:
                    self.assertEqual(value, subject.observe_mounts(owned(role)))
                execute.assert_called_once_with(owned(role), ["/usr/local/bin/elixir", "/workspace/collector-mounts.exs", role], 15, limit=65536)
                self.assertEqual(value, json.loads((subject.output / (role + "-mount-policy.json")).read_bytes()))
                with mock.patch.object(subject, "execute", return_value=(b"IDENTITY_JSON={}\\n", b"", 0)):
                    with self.assertRaises(collector.CollectorError):
                        subject.observe_mounts(owned(role))


'''
assert needle in s;s=s.replace(needle,wiring+needle);p.write_text(s)
