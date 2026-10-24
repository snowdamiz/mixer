# Private construction producer evidence

`receipt.json` binds the frozen VM tree, tool versions, commands and output
hashes. `source-manifest.json` and `frozen-source.tar.gz` preserve its exact
inputs. `layout-map.json` contains measured production/unit Debug/Release
size/alignment/field offsets; `call-map.json` attributes the candidate inventory
fields and explicitly identifies unresolved whole Option/Result/closure roles.
This candidate is **not accounting or executor implementation acceptance**.

Both profiles pass fourteen construction-only tests, seven preexisting executor
layout tests, six library feature combinations, and two Clippy configurations.
Full all-features library collection runs 151 tests per profile; this does not
replace the root's broader integration matrix or turn historical ignored tests
into passes. The constructor remains inaccessible to an external Rust caller.

The first derived metadata probe failed to compile because it used undeclared
generic lifetimes and skipped two multiline tuple field declarations. Its
probe/overlay and failed output are retained. The second metadata-only pass
substituted static lifetimes and measured all field declarations; it passed
without changes to the engine freeze or repeating engine qualification.

All runs use independently owned same-ABI synthetic fixtures. No full target,
interpreter, initialize/invoke, physical device, signing/store, published
FieldLog or GA qualification occurred. Nine cancellation samples and eight
work-prefix samples are bounded construction evidence, not complete full
executor interruption coverage.
