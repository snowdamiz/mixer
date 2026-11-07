# Exact compiled qualification interface v1

Canonical destinations proposed for root-selected integration: `native/android/tests/editor-boundaries/qualified-map.json`, `check_qualified_matrix.py`, `classfile.py`, `reference-obligations.json`, and `run_qualified_matrix.py`. This sealed packet supplies the checker and reference closure; the complete qualified map and producer remain pending.

Default host runner must execute its fresh full selected matrix and then call:

```
python3 check_qualified_matrix.py --map qualified-map.json --source-root <explicit-product-java-directory> --classes <fresh-B-emitted-class-directory> --matrix <fresh-matrix.json> --output <receipt.json>
```

Exit 0 requires exact selected-source/class context and every reviewed active required state. Exit 2 refuses missing, stale, incomplete or foreign evidence. No default skip or core-only success is permitted. An explicitly requested `--skip-matrix` is a separately labeled interim core receipt only.

`schema=mixer.android.compiled-boundaries.v1`, `source_pair=mixer.android-source-pair.5`, and `qualification_status=qualified` are required. `product_sources` is the exact16 basename to `{bytes,sha256}` map. `exact_input_connection_descriptors` equals the pinned exact38 set. `historical_dispositions` has all189 unique IDs with `status`, `reason`, and reviewed `boundary_ids`. `v1_baselines` lists five separate active positive IDs. Every context has `context_id`, `qualification_status`, exact product `class_map`, and active `boundaries`.

Context ID is SHA256 of canonical JSON (`sort_keys=true,separators=(',',':')`) containing `{source_map:<exact16>,class_map:<relative-class-path:{bytes,sha256}>}`. Product classes are identified from actual SourceFile attributes against the exact16 inputs. A different compiler or debug flags needs a separately qualified context; no line-only remap or toolchain fallback is accepted.

Each boundary has unique `id`, `subjects`, exact `caller`, `required_states`, and `evidence_kind=executable-host-qualified`. Caller fields are `class` (JVM slash owner), `class_sha256`, `source_sha256`, `method`, JVM `descriptor`, instruction-boundary `bci`, `opcode` mnemonic and exact `callee={owner,name,descriptor}` (dynamic sites additionally retain their bootstrap index). Constructors and overloads are separate sites. Pure source/bytecode/native-pending subjects remain outside executable boundaries with explicit pending scope; they never get executed credit.

A fresh matrix uses `schema=mixer.android.compiled-boundary-results.v1`, matching `context_id`, `product_sources`, exact `class_map`, `status=passed` and rows. Each row has `boundary_id`, `state`, `status=passed`, `evidence_kind=executed-host`, positive `hit`, exact `caller`, actual `receiver_identity`, `original_authority`, full `production_frames`, `native_event_jni_sequence`, `cleanup_fatal_disposition`, and equal structured `expected`/`observed`. No unknown, missing or duplicate state row is permitted. Unsupported successor authority claims refuse.

The checker proves evidence integrity and closure, not behavioral truth by itself. Root review of the selected semantic map, actual assertions, native-pending exclusions, complete raw outcomes and separate device/OTA/GA gates remains mandatory. `unqualified-example.json` intentionally refuses. Exact OpenJDK25.0.4.1 `--release17 -g` is the current inventory context; host migration compiler/debug flags are being coordinated before final context selection.
