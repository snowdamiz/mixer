# Focused CI fixture-cleanup correction review

R01 is closed in the released source. No blocking findings remain; recommend
root release of one exact bounded run of plan
d1d909dee7aa0d93ad78f113689f0aa6db02f760a656f566c627977c35698b22,
under freeze
5ce0557d8cae549b7257a2d0ddfd59f73c4bd59d463fa20377e0038dfd64172e.

The new guard runs after confirmed owned child/group cleanup and before any
artifact reads. It uses lstat to require an ordinary phase directory, requires
exactly the eight artifact names plus command.json/stdout.txt, and requires every
entry to be an ordinary file. Extra OpenSSL invocation artifacts, other extras,
missing files, directories, symlinks and FIFO/special files fail. The validator
does not delete or repair rejected output; the outer failure path retains the
phase directory and records the error. Deadline checks cover inventory and type
checks. This closes the actual-filesystem-to-artifact-map gap.

The controls source and sealed report were read without replay: one exact
ten-file positive case and seven refusals cover openssl-05.json, an arbitrary
extra, a missing artifact, a required-file symlink, directory, FIFO, and a symlink
phase root. They confirm rejected evidence remains intact before removing their
own synthetic temporary tree. These are producer offline filesystem checks,
not product/runtime evidence.

Independent custody passed all 225 new members, 224 prepared pins, 25 canonical
pins and 980 tool pins, and preserved all 221 old packet members. The only
changed copied nonplan file is runner.py, matching the exact recorded diff.
Its other changes are prepared-2/candidate-2 path literals. Bootstrap, seven-test
selection, 29/7/22 counts, corrected helper/K07g, eighteen accepted product
sources, support, artifact schemas, OpenSSL shim, tools, dependencies, deadlines
and cleanup behavior are unchanged from review-1. No additional product tests
or process audits were introduced.

No producer code, compiler, formatter, OpenSSL, TLS or test/runtime was replayed;
only read-only custody checks and Python source parsing ran. Root must issue the
exact release, then retain fresh targeted terminal/cleanup evidence. A targeted
seven-case pass does not qualify the full KeyOwnerTest/Phoenix suite. The remote
six-failure record remains preserved; native/UI/capture/devices, production and
GA remain outside this boundary.
