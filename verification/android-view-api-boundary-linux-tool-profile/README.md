# Exact Linux Temurin17 data profile

This packet supplies a practical candidate for the focused Ubuntu24.04 hosted
Android admission. It authorizes no execution, installation or dispatch. No
local Java/JVM/compiler, product, Node oracle, native/UI/capture or phone runtime
ran. Existing process and native holds remain untouched.

The official Eclipse Adoptium release is
[jdk-17.0.21+9](https://github.com/adoptium/temurin17-binaries/releases/tag/jdk-17.0.21%2B9).
GitHub release421004792 identifies archive asset666563450:
`OpenJDK17U-jdk_x64_linux_hotspot_17.0.21_9.tar.gz`,193,594,705 bytes,
SHA256 `8b9b611d917e3dfd8419d3566b5949226f69b052fed7e109c1368add1dfe8711`.
The published `.sha256.txt` asset666564714 contains the same digest and filename.
`release-metadata.json` preserves only the selected official release metadata;
the bytes also match its published asset digest. The release itself is mutable,
so identity comes from the exact archive digest rather than the tag alone.

`runtime-members.json` is a sorted, unique list of74 `{path,bytes,sha256}` rows
relative to `/usr/lib/jvm/temurin-17-jdk-amd64`. It includes `bin/java`,
`bin/javac`, `release`, every ordinary `conf/**` file and every ordinary
`lib/**` file except the explicitly excluded `lib/src.zip` and
`lib/security/cacerts`. Its198,674,633 bytes include `lib/modules`, `lib/ct.sym`,
`lib/jrt-fs.jar`, `lib/jvm.cfg`, both shared-class archives, all bundled native
libraries, JLI and JVM, runtime/provider/security policy, timezone and font data.
Every selected archive member is ordinary; no runtime symlink is inferred.
The complete archive inventory records543 entries including its root and208
bounded links. It is provenance, not a required whole Debian-tree identity.

All three current Android-owner receipts from Engine40831237081 at the
parent-supplied context5b6fc4f5 agree with the official archive's exact launcher
bytes: java16,320 bytes SHA256
`a2195ae9f8a91b82f53df7e1d1b9a650937ebbabbf67d0240c6378b4fbd9990b`,
javac16,368 bytes SHA256
`1f0ccaede1af2ff0d3cbc6eda708080fa073237bb53a7b2340bbccc378db523f`.
This proves a useful current provider match for the launchers. The hosted
`lib/modules`, libraries and configuration have not been observed; they must
match every selected expected row before any future child starts, and remain
matched before and after each command. No first-observed digest can replace an
expected runtime digest. The collector should also reject added names within
`conf/**` and `lib/**`, apart from the two explicit exclusions. An unexpected
runtime/config symlink needs separate review, not automatic target hashing.

The official installer Debian rules blob
[`9cedbd89476c0b34f82ced5acbe40f026b1044eb`](https://api.github.com/repos/adoptium/installer/git/blobs/9cedbd89476c0b34f82ced5acbe40f026b1044eb)
documents a checksum-verified tar repack with stripping disabled, replacement of
`lib/security/cacerts` by the literal link `/etc/ssl/certs/adoptium/cacerts`,
and an added root `src.zip` link. The retained rules name17.0.13+11. They support
the packaging pattern but do not prove the exact17.0.21+9 Debian package or
hosted topology. There is no documented `conf` relocation in these rules.
`packaging-sources.json` retains exact official blob identities and source text
as inert data; no packaging script was executed.

The CA trust file is an explicit provider-owned boundary for this offline
focused test, rather than a silently learned tool digest. No certificate,
TLS/network, or signing result is qualified. Other `bin/**` tools, `jmods`,
headers, legal/docs and source files are outside the selected command lookup
scope. They are fully inventoried as archive provenance but not required to
match the installed package.

`elf-dynamic-boundary.json` parses every selected ELF64 member's `PT_INTERP`,
`DT_NEEDED`, `DT_RPATH` and `DT_RUNPATH` as data. The launchers request
`/lib64/ld-linux-x86-64.so.2` and bind JLI through
`$ORIGIN:$ORIGIN/../lib`. Nonbundled loader/libc/libm/pthread/dl/rt plus X/audio
libraries remain part of the selected Ubuntu provider image. No `ldd`, loader,
system-library probe or process inspection ran. This is not a fully hermetic
system-library closure, and `DT_NEEDED` does not enumerate optional `dlopen`
providers. Root must explicitly accept and record the system-image boundary;
JVM loader override environment variables and Java option injection must stay
absent from the existing allowlisted child environment.

The acquisition and analysis are separate commands:

```
python3 verification/android-view-api-boundary-linux-tool-profile/acquire_data.py
python3 verification/android-view-api-boundary-linux-tool-profile/analyze_archive.py
```

Acquisition has a256MiB per-consumer cap and60-second deadline, no blind retry,
and no signed transport URLs in saved output. The initial archive transfer
completed but its EOF bookkeeping raised `AttributeError`; that failure is
retained. The exact complete local bytes were then hashed and adopted without
redownloading. The connector's checksum-asset404 is also retained. Raw archives
and metadata assets stay under ignored `local/`; no executable tree was extracted.

The analysis installs process/session/group/signal/timer/wait/socket guards
before loading archive parsers. It verifies the compressed digest, then validates
all paths, duplicate names, entry kinds, link scope/cycles/targets, ordinary
ancestors,4,096-entry and256MiB single-file caps and768MiB actual/declared
decompression caps before member payload reads. It streams member hashes and
compares hosted launcher receipts without executing downloaded content.
`derivation-receipt.json` records Python/tool version, command, source digest,
archive/output digests, checks and zero active-operation attempts. The companion
independent lane confirmed all74 rows map exactly to ordinary archive members
and checked profile/receipt/ELF-union consistency using guarded data checks.

This packet closes the missing expected Linux JDK-file identities. Actual
provider admission, SDK37/D8 compatibility, the focused hosted test, native
runtime and final product/GA acceptance remain separate evidence.
