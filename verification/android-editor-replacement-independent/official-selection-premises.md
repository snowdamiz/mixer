The pinned Android16_r1 ArrowKeyMovementMethod.initialize(TextView, Spannable)
calls Selection.setSelection(text, 0), at lines 363–364. Its SHA256 is
01ef827182e07b3b4b973babb6a049ee9c9329f99fe080214f617008d0d4b3c2.
Selection.setSelection(text, index) delegates start=index/end=index at 154–155;
the pinned Selection.java SHA256 is
7bcc05df6b80c5209e9041cb17bd8f7516126c82b9ca6bdae89df9e066772ecd.
URLs and retrieval receipts are in official/collection.json. These official
Apache-2.0 platform references are verification oracles only, never product code
or executed Android implementations. No new general-purpose dependency is added.

The already-pinned EditText default movement method is ArrowKeyMovementMethod;
TextView setter calls its movement initialization after installing Enew but before
text watchers. ACTION_SET_TEXT then sets selection to text length only for a
nonempty value after setText returns. Under that exact default native path empty
selection is 0, while nonempty selection ends at text.length(). The controls still
require both early movement and late action-selection hooks for nonempty text;
they do not substitute an authored selection algorithm for platform super.

Official TextView ACTION_SET_TEXT checks enabled/EDITABLE, not hasFocus.
Canonical NativeField accessibility entry likewise used existing current input
and window facts without a field-focus requirement. Root confirmed this source
parity must be retained for ordinary unfocused ACTION_SET_TEXT; only adapter/
creator routes keep their existing separate focus policies.

The immutable baseline host Spanned leaf omits SPAN_INCLUSIVE_INCLUSIVE. Official
SDK37 javap proves its exact value is 18; sdk-spanned-constants.txt and its receipt
retain the command/output. The prepared source uses a named test constant with
that exact value and asserts it survives Annotation snapshotting.
