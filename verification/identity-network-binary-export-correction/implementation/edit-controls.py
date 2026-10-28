from pathlib import Path
p=Path('hosted/scripts/test_identity_network_collector.py');s=p.read_text();needle='class RebarTransferControls(unittest.TestCase):'
addition='''class BootstrapExportControls(unittest.TestCase):
    def test_high_byte_nul_and_all_256_values_pass_only_exact_size_and_hash(self):
        for body in (b"\\x00", b"\\x80\\xff\\x00", bytes(range(256)), bytes(range(256)) * 257):
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


''';assert needle in s;s=s.replace(needle,addition+needle)
needle='class BudgetAndCommandControls(unittest.TestCase):'
methods='''    def _binary_copy_subject(self, directory, payload, *, code=0, stderr=b""):
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
            for payload in (b"\\x00", b"\\x80\\xff\\x00", bytes(range(256)), bytes(range(256)) * 257):
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
        payload = b"\\x00\\x80\\xff"
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
            subject = self._binary_copy_subject(directory, b"\\x00\\xff")
            subject.copy_file_out(owned("prepare"), "/workspace/downloads/hex.ez", 4096)
            with self.assertRaisesRegex(collector.CollectorError, "already retained"):
                subject.copy_file_out(owned("prepare"), "/workspace/downloads/hex.ez", 4096)
            self.assertEqual(1, subject.command_number)
            self.assertEqual(b"\\x00\\xff", (subject.output / "bootstrap-exports/hex-actual.bin").read_bytes())
        with tempfile.TemporaryDirectory(prefix="identity-controls-") as directory:
            subject = self._binary_copy_subject(directory, b"control")
            with self.assertRaisesRegex(collector.CollectorError, "public bootstrap export cap"):
                subject.copy_file_out(owned("prepare"), "/workspace/tooling/rebar3", 16777217)
            self.assertEqual(0, subject.command_number)


''';assert needle in s;s=s.replace(needle,methods+needle);p.write_text(s)
