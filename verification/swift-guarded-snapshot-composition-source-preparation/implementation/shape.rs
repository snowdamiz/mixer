
// Fixed O(1) actual Buffer lengths for preguard bounds; this is not authority.
impl ValidatedSwiftReactor {
 pub(crate) fn snapshot_counts_v1(&self)->[usize;9] {
  let m=&self.metadata;
  [self.source.len(),m.signatures.len(),m.parameters.len(),m.imports.len(),
   m.functions.len(),m.globals.len(),m.exports.len(),m.data.len(),m.elements.len()]
 }
}
