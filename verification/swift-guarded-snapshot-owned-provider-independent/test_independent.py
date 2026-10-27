"""Fresh independent finite controls. Pure bytes only; no Rust/runtime evidence."""
from pathlib import Path
import dataclasses,importlib.util,json,struct,sys,unittest
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];P=ROOT/'verification/swift-guarded-snapshot-owned-binding-provider'
sys.path.insert(0,str(P))
import input_model as m
spec=importlib.util.spec_from_file_location('retained_provider_test_fixture',P/'test_input_model.py');f=importlib.util.module_from_spec(spec);spec.loader.exec_module(f)
def changed_word(b,offset,n):
 c=bytearray(b);struct.pack_into('<Q',c,offset,n);return bytes(c)
def replace_bytes(b,offset,value):return b[:offset]+value+b[offset+len(value):]
def changed_identity(values,role,data):return tuple(m.Identity(x.role,data,m.digest(data)) if x.role==role else x for x in values)
def correlated(values,nonce,file_identity):return m.check_correspondence(values,expected_session=values[2].sha256,expected_nonce=nonce,source_file_identity=file_identity)
def rebound_build(values,build):
 values=changed_identity(values,'build',build)
 return changed_identity(values,'session',replace_bytes(values[2].data,176,m.digest(build)))
class IndependentControls(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.values,cls.nonce,cls.file=f.bundle();cls.paths=(b'source-\xff',b'build',b'session',b'rows',b'snapshot')
 def test_all_false_authority_flags_survive_consistent_synthetic_bundle(self):
  result=correlated(self.values,self.nonce,self.file)
  self.assertEqual(result['status'],m.STATUS)
  for key in ('actual_binary_embedded_values_observed','launcher_or_file_custody_authenticated','review_authenticated','operational_grant'):self.assertIs(result[key],False)
  for key in ('authenticated_owner','operational_grant'):self.assertIs(m.describe_candidate(self.values,self.paths,self.paths)[key],False)
 def test_review_preimage_has_no_fabricated_authentication(self):
  for data in (b'arbitrary-new-review',b'{}',b'untrusted-release-label'):
   values=changed_identity(self.values,'review',data)
   self.assertIs(correlated(values,self.nonce,self.file)['review_authenticated'],False)
 def test_compiler_and_output_rebinding_remains_unqualified(self):
  values=changed_identity(self.values,'compiler',b'fresh synthetic compiler bytes')
  values=changed_identity(values,'executable',b'fresh synthetic output bytes')
  build=replace_bytes(values[1].data,280,values[4].sha256)
  build=replace_bytes(build,312,values[3].sha256);build=changed_word(build,80,len(values[3].data))
  values=rebound_build(values,build)
  values=changed_identity(values,'session',replace_bytes(values[2].data,208,values[3].sha256))
  r=correlated(values,self.nonce,self.file)
  self.assertFalse(r['actual_binary_embedded_values_observed']);self.assertFalse(r['launcher_or_file_custody_authenticated'])
 def test_every_build_digest_slot_rejected_after_valid_session_rebinding(self):
  for offset in range(152,344,32):
   build=f.flip(self.values[1].data,offset);values=rebound_build(self.values,build)
   with self.subTest(offset=offset),self.assertRaises(m.InvalidInput):correlated(values,self.nonce,self.file)
 def test_all_build_reserved_bytes_refuse_after_rebinding(self):
  for offset in (*range(88+len(b'aarch64-apple-darwin'),152),*range(344,512)):
   values=rebound_build(self.values,f.flip(self.values[1].data,offset))
   with self.subTest(offset=offset),self.assertRaises(m.InvalidInput):correlated(values,self.nonce,self.file)
 def test_all_session_reserved_bytes_refuse_with_updated_expected_digest(self):
  for offset in range(368,512):
   values=changed_identity(self.values,'session',f.flip(self.values[2].data,offset))
   with self.subTest(offset=offset),self.assertRaises(m.InvalidInput):correlated(values,self.nonce,self.file)
 def test_session_digest_slots_refuse_with_updated_expected_digest(self):
  for offset in range(240,368,32):
   values=changed_identity(self.values,'session',f.flip(self.values[2].data,offset))
   with self.subTest(offset=offset),self.assertRaises(m.InvalidInput):correlated(values,self.nonce,self.file)
 def test_cwd_raw_boundary_and_digest_correspondence(self):
  original=self.values[2].data;parts=m.parse_record(original,session=True)['parts']
  for cwd,allowed in ((b'/'+b'x'*4094,True),(b'/'+b'x'*4095,False),(b'\xffrelative',False),(b'/\xff',True),(b'/\0',False)):
   session=changed_word(original,64,len(cwd));session=changed_word(session,24,512+sum(map(len,parts[:3]))+len(cwd));session=replace_bytes(session,336,m.digest(cwd));session=session[:512]+b''.join(parts[:3])+cwd
   values=changed_identity(self.values,'session',session)
   if allowed:self.assertFalse(correlated(values,self.nonce,self.file)['operational_grant'])
   else:
    with self.assertRaises(m.InvalidInput):correlated(values,self.nonce,self.file)
 def test_selected_source_claim_and_data_do_not_get_oracle_credit(self):
  source=self.values[0]
  bad=dataclasses.replace(source,data=f.flip(source.data,1946))
  values=(bad,)+self.values[1:]
  with self.assertRaises(m.InvalidInput):m.describe_candidate(values,self.paths,self.paths)
  # Rust retains these labels and checks only length/selected claim; no Rust
  # invocation or hash-authentication receipt is inferred from this Python test.
 def test_paths_all_positions_and_no_alias_discount(self):
  for i in range(5):
   for native,retained in ((b'',b''),(b'a\0',b'a\0'),(b'/actual',b'/retained')):
    ns=self.paths[:i]+(native,)+self.paths[i+1:];rs=self.paths[:i]+(retained,)+self.paths[i+1:]
    with self.subTest(i=i,native=native),self.assertRaises(m.InvalidInput):m.describe_candidate(self.values,ns,rs)
  aliased=(b'\xffsame',)*5;r=m.describe_candidate(self.values,aliased,aliased)
  self.assertEqual(r['input_backing_bytes'],sum(len(v.data) for v in self.values)+10*len(aliased[0]))
  self.assertEqual(r['native_path_bytes'],tuple(map(len,aliased)))
 def test_checked_sum_exhaustive_small_limits_and_u64_edges(self):
  for limit in range(1,65):
   for a in range(1,limit+1):
    for b in (1,limit,limit-a,limit-a+1):
     if 0<b<=limit and a+b<=limit:self.assertEqual(m.checked_sum((a,b),limit),a+b)
     else:
      with self.assertRaises(m.InvalidInput):m.checked_sum((a,b),limit)
  self.assertEqual(m.checked_sum((m.U64_MAX-7,7)),m.U64_MAX)
  with self.assertRaises(m.InvalidInput):m.checked_sum((m.U64_MAX-7,8))
 def test_compile_slot_order_and_runtime_exclusions_are_distinct(self):
  r=correlated(self.values,self.nonce,self.file);slots=m.parse_record(self.values[1].data)['digests']
  expected=tuple(slots[i].hex() for i in (0,1,2,4,3))
  self.assertEqual(r['embedded_identity_digests'],expected);self.assertNotEqual(slots[3],slots[4])
  for key in m.COMPILE_KEYS:self.assertEqual(m.unpack_list(f.pack_list([key+b'=x']),environment=True),(key+b'=x',))
  for key in m.SESSION_KEYS:
   with self.assertRaises(m.InvalidInput):m.unpack_list(f.pack_list([key+b'=x']),environment=True)
 def test_malformed_section_extents_cannot_wrap_or_leave_tail(self):
  for role,session,offsets in (('build',False,(48,56,64,72)),('session',True,(40,48,56,64))):
   original=next(x.data for x in self.values if x.role==role)
   for offset in offsets:
    for n in (0,m.U64_MAX,1<<63):
     with self.subTest(role=role,offset=offset,n=n),self.assertRaises(m.InvalidInput):m.parse_record(changed_word(original,offset,n),session=session)
 def test_product_constraints_preserve_all17_and_never_select_policy(self):
  fields={name:7 for name in m.PRODUCT_FIELDS};fields.update(execution_work=1_000_000_000,combined_bytes=268_435_456)
  self.assertEqual(m.check_product_budget(fields),'shape-only-policy-selection-pending')
  for name in m.PRODUCT_FIELDS:
   for value in (False,-1,m.U64_MAX+1):
    with self.subTest(name=name,value=value),self.assertRaises(m.InvalidInput):m.check_product_budget(fields|{name:value})
if __name__=='__main__':unittest.main(verbosity=2)
