"""Prepared guarded data controls. Never imports product/compiler/custody subjects."""
import sys
sys.dont_write_bytecode = True
if not (sys.flags.isolated == 1 and sys.flags.no_site == 1):
    raise RuntimeError("Run with -I -B -S")
def guard(event,args):
    if event.startswith(("subprocess","socket","ctypes")) or event in ("os.system","os.posix_spawn","os.fork","os.kill","os.killpg","os.exec"):
        raise RuntimeError("Pure controls denied " + event)
    if event == "import" and args[0].split(".")[0] not in sys.stdlib_module_names:
        raise RuntimeError("Non-stdlib import denied " + args[0])
sys.addaudithook(guard)
import ast
import hashlib
import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zlib
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("pair7_floor_data_controls",HERE/"java_api_floor.py")
floor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(floor)

def synthetic_dex(owner="demo/Example",descriptor=None):
    name = (descriptor or ("L"+owner+";")).encode("ascii")
    data = bytearray(152)
    data[:8] = b"dex\n035\0"
    struct.pack_into("<II",data,56,1,112)
    struct.pack_into("<II",data,64,1,116)
    struct.pack_into("<II",data,96,1,120)
    struct.pack_into("<I",data,112,152)
    struct.pack_into("<I",data,116,0)
    struct.pack_into("<I",data,120,0)
    data.extend(bytes([len(name)])+name+b"\0")
    struct.pack_into("<III",data,32,len(data),112,0x12345678)
    struct.pack_into("<II",data,104,len(data)-152,152)
    data[12:32] = hashlib.sha1(data[32:]).digest()
    struct.pack_into("<I",data,8,zlib.adler32(data[12:]))
    return bytes(data)

class PureControls(unittest.TestCase):
    def inspect(self,data,xml="<api/>",owner="demo/Example",classes=True):
        with tempfile.TemporaryDirectory(prefix="pair7-data-only-") as directory:
            root = Path(directory)
            (root/"classes.dex").write_bytes(data)
            (root/"api.xml").write_text(xml)
            rows = [{"path":owner+".class"}] if classes else []
            return floor.inspect(root/"classes.dex",root/"api.xml",rows)
    def test_all_python_sources_parse_without_execution(self):
        for name in ("bind_snapshot_source.py","compile_pair7.py","java_api_floor.py","test_source_controls.py"):
            ast.parse((HERE/name).read_text(),filename=name)
    def test_synthetic_header_and_present_class_are_finite_data_only(self):
        result = self.inspect(synthetic_dex())
        self.assertTrue(result["accepted"])
        self.assertFalse(result["runtime_accepted"])
    def test_empty_emitted_map_refuses(self):
        with self.assertRaises(ValueError): self.inspect(synthetic_dex(),classes=False)
    def test_missing_emitted_class_refuses(self):
        with self.assertRaises(ValueError): self.inspect(synthetic_dex(),owner="demo/Missing")
    def test_bad_checksum_refuses(self):
        data = bytearray(synthetic_dex()); data[-1] ^= 1
        with self.assertRaises(ValueError): self.inspect(bytes(data))
    def test_truncated_dex_refuses(self):
        with self.assertRaises(ValueError): self.inspect(synthetic_dex()[:110])
    def test_unknown_java_type_remains_refused(self):
        result = self.inspect(synthetic_dex("java/lang/Unknown"),owner="java/lang/Unknown")
        self.assertFalse(result["accepted"])
        self.assertEqual(len(result["unresolved"]),1)
    def test_later_java_type_remains_refused(self):
        result = self.inspect(synthetic_dex("java/lang/Later"),'<api><class name="java/lang/Later" since="36"/></api>',owner="java/lang/Later")
        self.assertFalse(result["accepted"])
        self.assertEqual(result["above28"][0]["api"],36)
    def test_record_reference_refuses(self):
        with self.assertRaises(ValueError): self.inspect(synthetic_dex("java/lang/Record"),'<api><class name="java/lang/Record" since="36"/></api>',owner="java/lang/Record")
    def test_java_array_element_type_is_in_closure(self):
        with tempfile.TemporaryDirectory(prefix="pair7-array-data-") as directory:
            path = Path(directory)/"array.dex"
            path.write_bytes(synthetic_dex(descriptor="[[Ljava/lang/Later;"))
            self.assertEqual(floor.dex_refs(path)["types"],["java/lang/Later"])
    def test_inherited_member_floor_preserves_later_boundary(self):
        root = ET.fromstring('<api><class name="child" since="1"><extends name="parent" since="1"/></class><class name="parent" since="1"><method name="m()V" since="31"/></class></api>')
        classes = {row.get("name"):row for row in root}
        self.assertEqual(floor.api_lookup(classes,"child","m()V","method"),{"declared_owner":"parent","api":31})
if __name__ == "__main__":
    unittest.main(verbosity=2)
