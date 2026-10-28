# JOSE missing-module cause and timestamp correction

The failed run is `40766689512`, source `8888d8e2c8431ee311c68e94a1abbb280f84802a`.
It reached both unchanged production-path test methods and failed both at RSA
fixture-key generation because `:jose_jwk` was unavailable. It passed zero product
methods. The later missing DNS receipt export is a consequence, not the cause.
Original evidence remains in `../github-delivery-source-pair-and-rebar/ci-review/network/`.

The prepared archive has 1,232 regular files, all at mtime zero. Its byte-exact
locked JOSE 1.11.13 sources include 113 Erlang modules, including `jose_jwk`,
`jose_jwt` and `jose_jwe`; this is not missing source or a different dependency
version. The observed BEAM map contains only 16 Erlang JOSE modules. The local
`hosted/deps/jose` tree is version 1.11.12 and was excluded as causal evidence.

Official [Mix 1.20.4 Erlang compilation](https://github.com/elixir-lang/elixir/blob/v1.20.4/lib/mix/lib/mix/tasks/compile.erlang.ex)
uses `Mix.Utils.stale?` on a source and its included headers. The
[timestamp comparison](https://github.com/elixir-lang/elixir/blob/v1.20.4/lib/mix/lib/mix/utils.ex)
requires a source time strictly greater than the target time; a missing target
has time zero. Thus every archive-only zero-time source/header is incorrectly
treated as up to date with its absent BEAM. Source analysis predicts exactly the
16 observed compiled modules: each reaches `public_key/include/public_key.hrl`
outside the archive. That match strongly supports the epoch-zero cause; the
historical artifact does not separately record those OTP headers' actual mtimes.

The [dependency compilation task](https://github.com/elixir-lang/elixir/blob/v1.20.4/lib/mix/lib/mix/tasks/deps.compile.ex)
passes `--no-warnings-as-errors`, while [dependency context](https://github.com/elixir-lang/elixir/blob/v1.20.4/lib/mix/lib/mix/dep.ex)
defaults to `:prod`, where locked JOSE's project omits Erlang warnings-as-errors.
This explains the successful exit despite undefined-module warnings.
`mix deps.compile --force` is not a viable correction: it clears the dependency
build directory but does not forward `--force` to the nested compile task, so
the same zero-time comparison remains. `mix compile --force` in the hosted
project likewise does not directly force every dependency's Erlang compiler.

Root selected the smallest correction: the preparation tar export uses fixed
mtime `1`, and host archive admission requires that exact integer on every entry.
The initial source-only tar remains at zero because the preparation export
normalizes all entries. No product/dependency bytes, versions, compile commands,
resource bounds, mounts, capabilities or test methods change. Future archives
with epoch zero, mixed timestamps, negative or fractional times fail admission.

`python3 -B verification/identity-network-jose-compile-investigation/verify.py`
passed 129 pure controls in less than one second on this host. All original
126 test method ASTs match the failed-run source byte-for-byte in structure;
three new methods cover timestamp boundaries. A Python audit hook denies all
child-process and socket actions; none were attempted. The verification also
reheaders the actual failed archive in memory, changing only mtime/checksum
fields, and proves all 1,232 payload bytes/digests stay equal. Current admission
accepts that candidate and rejects the original epoch-zero archive. The frozen
177-file product digest and both protected hashes remain exact. `git diff --check`
passed on the three assigned canonical paths.

This is source and pure Python evidence only. No Elixir/compiler/container/native
runtime, UI, capture, custody or held process probe ran. Successful JOSE compilation
and both unchanged test methods remain pending a fresh isolated CI attempt and
independent artifact review. No commit, push, dispatch or global status edit was
performed by this lane. The investigation launched no persistent resources;
candidate bytes stayed in memory and the unit suite cleaned its temporary files.
