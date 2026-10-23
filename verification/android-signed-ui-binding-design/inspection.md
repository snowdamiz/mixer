# Design inspection receipt

Run `python3 verification/android-signed-ui-binding-design/collect_observations.py`
from the repository root to refresh the selected-source manifest and installed
host-tool inventory. This collector inspects inputs and versions only. Its exact
argv, exit codes, output hashes, revision, proposal hash and source-manifest digest
are in `receipt.json`; it checks that the 27 selected source files do not change
during collection. Concurrent files outside that manifest are not this lane's
ownership or validation scope.

The initial default `javac -version` invocation failed because the macOS launcher
has no selected Java runtime. The receipt preserves this failure explicitly and
separately records installed `/opt/homebrew/opt/openjdk/bin/javac -version`
(`javac 27`). No Java build was requested or attempted. No runtime was installed
or environment setting changed. `javac-version.log` preserves the initial failure;
`javac-default-version.log` records its reproduction by the collector.

The proposal identifies three necessary changes beyond a new Android model:

- Count a presentation obligation from open, so pre-bind failure/close cannot
  release outer capacity while native resources survive.
- Replace the internal raw presentation Task receipt with a typed join which
  really awaits `Task.value`, then joins native retirement/fence progress.
- Add one fixed numeric process progress notification to the existing C transport,
  so its last no-helper return-fence callback can wake an already joined close
  owner without polling or an owner-retaining callback cycle.

The proposed facade-owned weak wrapper lease also distinguishes attempt retirement
for existing fallback from final facade retirement. All old input/attachment/probe
tokens revoke; a new attempt receives fresh tokens. A final close after old endpoint
reclaim may need one sequential terminal-only lifetime, never concurrent presentation
Tasks or an alternative cleanup executor. Root must explicitly accept this policy.

The proposal's ownership/waiter/progress rules have not been implemented or tested.
The source observations are evidence of the inspected gap, not executable proof of
the proposed solution. All binding acceptance rows remain pending. Existing C
transport/independent-review evidence is referenced context; it was not rerun by
this lane. No physical device discovery/query/run, emulator run, app publication,
commit or push occurred. The existing non-Apple unsupported stub is unchanged.
