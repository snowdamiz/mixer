from pathlib import Path
p=Path('hosted/scripts/test_identity_network_collector.py')
s=p.read_text()
marker='\n\nclass BudgetAndCommandControls(unittest.TestCase):'
assert s.count(marker)==1
addition=r'''

class GeneratedCompilerOutputControls(unittest.TestCase):
    PATH = "hosted/deps/telemetry/_build/prod/lib/.rebar3/rebar_compiler_erl/source.dag"
    PARENTS = ["/workspace", "/workspace/hosted", "/workspace/hosted/deps", "/workspace/hosted/deps/telemetry", "/workspace/hosted/deps/telemetry/_build", "/workspace/hosted/deps/telemetry/_build/prod", "/workspace/hosted/deps/telemetry/_build/prod/lib", "/workspace/hosted/deps/telemetry/_build/prod/lib/.rebar3", "/workspace/hosted/deps/telemetry/_build/prod/lib/.rebar3/rebar_compiler_erl"]

    def row(self, body=b"opaque inert DAG fixture\x00\x80\xff"):
        return {"bytes": len(body), "sha256": hashlib.sha256(body).hexdigest(),
                "type": "regular", "links": 1, "uid": 0, "gid": 0, "mode": 0o644,
                "parents": {path: {"type": "directory", "uid": 0, "gid": 0, "mode": 0o755} for path in self.PARENTS}}

    def fixture(self, body=b"opaque inert DAG fixture\x00\x80\xff"):
        # Input anchors are independently written from the locked sealed archive.
        prepared = {"source": copy.deepcopy(collector.FROZEN_MANIFEST), "deps": {
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
'''
p.write_text(s.replace(marker,addition+marker))
