# Two additive passive-return wrappers

The released 672-member v3 packet verifies. Against the selected v2 inputs,
the only changed Java file is BaseInputConnection.java. Its delta is exactly two
outer return-expression wrappers: getHandler() records the single constructed
Handler reference with descriptor ()Landroid/os/Handler;, and filtered
requestCursorUpdates(II) records the original done(...,true) boolean with (II)Z.
The existing 58 methods/64 wrapped expressions, other leaves, NativeOutcomeProbe,
product sources and original tests remain byte-identical.

Four bounded fresh commands pass: actual Java/Javac versions, isolated full
source compilation and 74 independent targeted assertions. They cover exact
normal value/reference and descriptors, original event/count/ordinary-hook then
qualification-hook ordering, fresh getter allocation once per call, ordinary
and fatal exceptions through both original and qualification hooks, and failed
observation preserving the original return/exception while refusing evidence.
getHandler keeps its original entry-only event shape; filtered cursor updates
keeps entry and beforeReturn. No new native hook is invented.

Both emitted methods contain exactly one returned observer invocation. All
sixteen product sources and 209 emitted product classes retain exact context
1b71af17048675296435ca74af284d54f93f2506b9c406517a452a3ce816dbdd.
The retained producer replay of all 61 original commands and 68 total commands
remains separate from these four fresh independent commands; it was not needlessly
repeated here after the unchanged v2 suite already passed independently.

This supports selection of the two host-leaf instrumentation additions only.
The product adapter's getHandler() still returns null without reading state on
any thread. It never calls this BaseInputConnection leaf: the leaf's Handler
result cannot qualify that distinct scalar product body. Final producer attempt
latching, immutable mutable-content snapshots, complete-frame proof, all exact
state-case joins and selected interpreter/execution closure remain required.
No full matrix, default integration, native, OTA or GA credit is granted.

All children completed and owned scratch was removed. No native/UI/capture or
process inventory ran. The leased JDK remains with the producer for later work.
