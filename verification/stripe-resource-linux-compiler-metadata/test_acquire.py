import unittest
import acquire


class AcquisitionControls(unittest.TestCase):
    def test_selected_six_urls_accept(self):
        self.assertEqual(len(acquire.ALLOWED), 6)
        for url in acquire.ALLOWED:
            acquire.allowed(url)

    def test_other_origin_architecture_package_and_query_refuse(self):
        for url in ("http://ports.ubuntu.com/ubuntu-ports/dists/noble/InRelease",
                "https://example.com/InRelease", acquire.ORIGIN + "pool/main/g/gcc/foo.deb",
                acquire.ORIGIN + "dists/noble/main/binary-amd64/Packages.xz",
                acquire.ORIGIN + "dists/noble/InRelease?anything"):
            with self.assertRaises(ValueError):
                acquire.allowed(url)

    def test_individual_and_aggregate_limit_refuse(self):
        acquire.within_bounds(1048576, 1048576, True)
        for args in ((1048577, 1048577, True), (33554433, 1, False)):
            with self.assertRaises(ValueError):
                acquire.within_bounds(*args)

    def test_redirect_refuses(self):
        with self.assertRaises(ValueError):
            acquire.NoRedirect().redirect_request(None, None, 302, "", None, acquire.ORIGIN)
