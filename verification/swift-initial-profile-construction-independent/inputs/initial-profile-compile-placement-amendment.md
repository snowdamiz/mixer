# Selected compile-only fixture placement

The initial-profile implementation selection remains unchanged for the exact
140-file product distribution and eleven named host support inputs. Rust child
modules can access ancestor private fields, so the two external privacy cases
must be compiled as a sibling of `initial_profile_v1`.

For only `guard_literal_from_sibling.rs` and
`external_selection_literal.rs`, append this exact text to the owned compiler
scratch copy of `src/experimental_swift_reactor/cache.rs`:

```rust

#[cfg(test)] mod initial_profile_external_contract { include!(env!("MIXER_INITIAL_PROFILE_COMPILE_CASE")); }
```

The exact bytes have one leading and one trailing newline. For the other
declared fixture cases, append this exact text to the scratch copy of
`src/experimental_swift_reactor/cache/initial_profile_v1/compile_contracts.rs`:

```rust

include!(env!("MIXER_INITIAL_PROFILE_COMPILE_CASE"));
```

The environment variable may select only one of the ten declared, independently
hashed compiler fixtures. No generated glue, new input path or additional
production bridge is selected. Record the original distribution and each actual
140-path compiler variant, exact append delta, fixture bytes, environment, argv,
compiler identity, diagnostics and cleanup. The original distribution stays
unchanged by these test-only variants.

Use the declared positive fixture to establish valid compilation at both
placement sites; any needed fixed configuration is an explicit recorded argv
choice. The two privacy failures must identify the intended private type or
field, not a missing file, malformed injection, unresolved import or unrelated
error. The descendant cases must likewise fail for their intended borrow/type
operation. Positive and negative compiler observations support only the named
privacy/lifetime facts. They do not replace actual constructor, owner, failure,
resource-accounting or cleanup evidence.
