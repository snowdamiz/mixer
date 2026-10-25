# Bearer pipeline cold compilation

Phoenix CI `40197780896` at `c0334a99` failed while compiling the production
router. Plug calls `BearerIdentity.init/1` at compile time; its former
`Code.ensure_loaded?/1` check could reject a valid sibling verifier that was
still compiling. Earlier standalone transport runs happened to finish that
module first and did not prove cold parallel order independence.

The plug now uses `Code.ensure_compiled/1` for its trusted verifier and clock,
then retains the same module/export validation. Missing modules, invalid
configuration and missing functions still fail closed; HTTP inputs do not
choose dependencies and no identity/authorization behavior was relaxed.

A regression test gates real verifier/clock compiler workers until a real
Plug pipeline starts initialization. The old implementation fails before those
workers are released; the repaired one waits and compiles with zero warnings.
The test bounds concurrency explicitly and cleans temporary files/modules.

`verification/hosted-bearer-cold-compile/run-1` preserves the reproduced product
failure; `run-2` preserves a test assertion corrected for Elixir 1.20 diagnostic
shape. `run-3` passes all 64 selected bearer, artifact transport and cold-compile
tests. `acceptance.json` binds current inputs. No full application or frozen
lane was compiled locally. Exact pushed CI remains separate evidence; no
native, provider, deployment, live console or GA qualification is claimed.
