# Private attempt signal latch

One internal fixed observer stores the first local/bridge cause, immutable first
bridge facts, exact generation, and sticky effects intent. Commit-entry checks
serialize with terminal capture; a later stop cannot roll back entered filesystem
work. A single buffered notification is a hint, with the snapshot authoritative.

Six actual test functions run in standalone mode against retained dependencies
in debug, release and Swift TSan. They cover first-cause precedence, stale/closed
commit rejection, sticky intent, 128 concurrent notifications and 128 stop/commit
races per mode. The same source's XCTest branch separately typechecks. The first
standalone typecheck missed Xcode's test-framework search path; adding that path
passed without changing production or test sources. Source-only independent
review found no actionable producer issue.

The future coordinator must own exactly one counted iterator, avoid strong owner
references across its suspended next(), record local stop before native cancel,
and explicitly finish/join on every unwind before store close. This component
creates no Task or execution authority; full consumer ownership and durable
effects/health composition remain to be tested.
