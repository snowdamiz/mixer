# Live ordinary owner source roster

Root authorized this additional scope after the two-file fixture correction was
sealed. The parent packet remains a record of that earlier scope.

`native/android/tests/private-owner-host-roster.json` starts with the immutable
`required-host-roster.json` bytes. Its only semantic change adds the production
`NativeEditorConnectionV2.java` source to closure B. The historical roster stays
unchanged.

`run-private-owner-host.py` reads the live roster once and binds those exact bytes
in its frozen inputs, source map, and source-stability postflight. Compilation and
host assertions remain pending fresh ordinary CI. No local subject test, compiler,
Git, network, process discovery, native runtime, capture, or UI operation runs here.
