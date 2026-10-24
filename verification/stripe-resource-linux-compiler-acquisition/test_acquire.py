"""Offline transport/file failure controls; never sends an HTTPS request."""
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest

import acquire


class Response:
    status = 200

    def __init__(self, data, url, content_length, error_after_first=False):
        self.data, self.url = io.BytesIO(data), url
        self.headers = {"Content-Length": str(content_length)}
        self.error_after_first = error_after_first
        self.reads = 0

    def __enter__(self):
        return self

    def __exit__(self, *unused):
        return False

    def geturl(self):
        return self.url

    def read(self, maximum):
        self.reads += 1
        if self.error_after_first and self.reads > 1:
            raise InterruptedError("injected interrupted body")
        return self.data.read(maximum)


class Opener:
    def __init__(self, response, error=None):
        self.response, self.error, self.calls = response, error, []

    def open(self, request, timeout):
        self.calls.append((request.full_url, timeout))
        if self.error:
            raise self.error
        return self.response


class AcquisitionControls(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.output = self.base/"owned"
        acquire.new_private_directory(self.output)
        self.data = b"bounded exact archive fixture"
        filename = "pool/main/f/fixture/fixture_1~ubuntu1_arm64.deb"
        self.package = {"filename": filename, "url": acquire.ORIGIN+filename,
                        "bytes": len(self.data), "sha256": hashlib.sha256(self.data).hexdigest()}
        self.allowed = {self.package["url"]: self.package}
        self.record = {}
        self.budget = {"observedBytes": 0, "retainedBytes": 0, "deadline": 200}

    def tearDown(self):
        self.temp.cleanup()

    def transfer(self, data=None, length=None, response_url=None, error=None, error_after_first=False):
        response = Response(self.data if data is None else data, self.package["url"] if response_url is None else response_url,
                            self.package["bytes"] if length is None else length, error_after_first)
        opener = Opener(response, error)
        self.last_opener = opener
        result = acquire.transfer(self.package, opener, self.output, self.allowed, self.budget, self.record, now=lambda: 100)
        self.assertEqual(len(opener.calls), 1)
        return result

    def assert_clean_failure(self):
        self.assertTrue(self.record["partialCleanup"])
        self.assertEqual(list(self.output.iterdir()), [])

    def test_exact_locked_set_and_authority_bytes(self):
        self.assertEqual(acquire.sha(acquire.SELECTION), acquire.SELECTION_SHA)
        self.assertEqual(acquire.sha(acquire.LOCK), acquire.LOCK_SHA)
        allowed = acquire.checked_lock(json.loads(acquire.LOCK.read_text()))
        self.assertEqual(len(allowed), 36)
        self.assertEqual(sum(item["bytes"] for item in allowed.values()), 50997408)

    def test_private_directory_and_exclusive_regular_success(self):
        result = self.transfer()
        self.assertEqual(result.read_bytes(), self.data)
        self.assertEqual(stat.S_IMODE(self.output.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE(result.stat().st_mode), 0o600)
        self.assertTrue(stat.S_ISREG(result.lstat().st_mode))
        self.assertEqual(result.stat().st_nlink, 1)
        self.assertTrue(self.record["partialCleanup"])
        self.assertEqual(self.record["status"], "signed-size-and-SHA256-verified")

    def test_tampered_same_size_bytes_rejected_and_removed(self):
        with self.assertRaises(ValueError):
            self.transfer(b"x"+self.data[1:])
        self.assert_clean_failure()

    def test_short_oversize_and_wrong_content_length_clean_up(self):
        for data, length in ((self.data[:-1], len(self.data)), (self.data+b"x", len(self.data)), (self.data, len(self.data)+1)):
            with self.subTest(data=data, length=length):
                self.record = {}
                with self.assertRaises(ValueError):
                    self.transfer(data=data, length=length)
                self.assert_clean_failure()

    def test_unselected_origin_query_fragment_and_traversal_refuse(self):
        for url in (self.package["url"]+"?x", self.package["url"]+"#x", self.package["url"].replace("https:", "http:"),
                    self.package["url"].replace("ports.ubuntu.com", "other.invalid")):
            with self.assertRaises(ValueError):
                acquire.checked_url(url, self.allowed)
        for filename in ("pool/main/../x.deb", "pool/main//x.deb", "/pool/main/x.deb", "pool/main/x%2f..deb", "pool/main/x\\y.deb"):
            package = dict(self.package, filename=filename, url=acquire.ORIGIN+filename)
            with self.assertRaises(ValueError):
                acquire.checked_url(package["url"], {package["url"]: package})

    def test_redirect_handler_refuses_every_redirect(self):
        for status in (301, 302, 303, 307, 308):
            with self.assertRaises(ValueError):
                acquire.NoRedirect().redirect_request(None, None, status, "", None, self.package["url"])

    def test_changed_response_url_refuses_and_cleans_up(self):
        with self.assertRaises(ValueError):
            self.transfer(response_url="https://other.invalid/fixture.deb")
        self.assert_clean_failure()

    def test_header_open_error_and_interrupted_body_clean_up_no_retry(self):
        with self.assertRaises(OSError):
            self.transfer(error=OSError("injected HTTPS failure"))
        self.assertEqual(len(self.last_opener.calls), 1)
        self.assert_clean_failure()
        self.record = {}
        with self.assertRaises(InterruptedError):
            self.transfer(error_after_first=True)
        self.assertEqual(len(self.last_opener.calls), 1)
        self.assert_clean_failure()

    def test_deadline_during_body_removes_partial(self):
        for expired in (131, 201):
            with self.subTest(expired=expired):
                clock = [100]
                response = Response(self.data, self.package["url"], len(self.data))
                original = response.read
                def delayed_read(maximum):
                    data = original(maximum)
                    clock[0] = expired
                    return data
                response.read = delayed_read
                opener = Opener(response)
                self.record = {}
                with self.assertRaises(TimeoutError):
                    acquire.transfer(self.package, opener, self.output, self.allowed, self.budget,
                                     self.record, now=lambda: clock[0])
                self.assertEqual(len(opener.calls), 1)
                self.assert_clean_failure()

    def test_existing_file_and_symlink_never_overwritten(self):
        partial = self.output/(Path(self.package["filename"]).name+".partial")
        outside = self.base/"outside"
        outside.write_bytes(b"preserve")
        partial.symlink_to(outside)
        with self.assertRaises(FileExistsError):
            self.transfer()
        self.assertEqual(outside.read_bytes(), b"preserve")
        self.assertTrue(partial.is_symlink())
        partial.unlink()
        partial.write_bytes(b"preserve-regular")
        with self.assertRaises(FileExistsError):
            self.transfer()
        self.assertEqual(partial.read_bytes(), b"preserve-regular")

    def test_final_collision_never_replaces_file_and_partial_removed(self):
        final = self.output/Path(self.package["filename"]).name
        final.write_bytes(b"preserve-final")
        with self.assertRaises(FileExistsError):
            self.transfer()
        self.assertEqual(final.read_bytes(), b"preserve-final")
        self.assertTrue(self.record["partialCleanup"])
        self.assertEqual(list(self.output.iterdir()), [final])

    def test_cleanup_identity_mismatch_preserves_replacement(self):
        path = self.output/"partial"
        fd, identity = acquire.exclusive_partial(path)
        os.close(fd)
        replacement = self.output/"replacement"
        replacement.write_bytes(b"preserve replacement")
        path.unlink()
        replacement.rename(path)
        with self.assertRaises(ValueError):
            acquire.remove_owned_partial(path, identity)
        self.assertEqual(path.read_bytes(), b"preserve replacement")

    def test_cumulative_and_per_request_deadlines(self):
        with self.assertRaises(TimeoutError):
            acquire.remaining_time(99, lambda: 100)
        with self.assertRaises(TimeoutError):
            acquire.request_time(200, 60, lambda: 100)
        with self.assertRaises(TimeoutError):
            acquire.request_time(99, 99, lambda: 100)
        self.assertEqual(acquire.remaining_time(110, lambda: 100), 10)
        self.budget["deadline"] = 99
        with self.assertRaises(TimeoutError):
            self.transfer()
        self.assertEqual(list(self.output.iterdir()), [])

    def test_aggregate_transfer_and_storage_caps_refuse_before_file(self):
        self.budget["observedBytes"] = acquire.TOTAL_LIMIT
        with self.assertRaises(ValueError):
            self.transfer()
        self.budget["observedBytes"] = 0
        self.budget["retainedBytes"] = acquire.STORAGE_LIMIT
        with self.assertRaises(ValueError):
            self.transfer()
        self.assertEqual(list(self.output.iterdir()), [])

    def test_existing_private_directory_not_reused(self):
        with self.assertRaises(FileExistsError):
            acquire.new_private_directory(self.output)


if __name__ == "__main__":
    unittest.main()
