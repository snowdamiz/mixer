# Private ordinary Android staged C bridge

The checklist engine now exports the existing registry's prepare, commit and
abort decisions through `mixer_android_v2.h`. These functions share its original
create/destroy registry. They forward to the accepted SPI without a second state
machine, output cache or token allocator. The older exchange ABI is unchanged.

Prepare returns caller-owned packet bytes and a nonzero token while retaining
the candidate engine. Modifying or releasing those packet bytes does not modify
the engine. Failure to retain or deliver the packet downstream must abort the
token. A matching commit is allowed only after gated native attachment and final
validation; ambiguous commit outcome requires session/presentation retirement.
One pending token blocks legacy exchange as well as another prepare. Destroy
invalidates the token. The header documents bounds, valid nonoverlapping foreign
pointers, statuses, retry behavior and the engine's value-semantics requirement.

This slice adds private exports to the ordinary checklist library only. JNI,
generated application entry points, Activity coordination and actual native
attachment are separate follow-on work. It does not enable V2 opt-in, change the
signed path, or provide general-purpose rollback for reference state or external
effects. Final hardware and launch qualification remain open.

Actual C clients pass 77 assertions per fresh host Debug and Release library.
They cover deferral, abort and retry, stale/foreign/destroyed tokens, byte-buffer
ownership, metadata and size bounds, Unicode events, and exactly-once commit.
C++17 clients compile/link the same header and invoke both decision exports.
Official Swift 6.3.3 links the arm64 API28 library with all three C exports.

The original collector completed every build and runtime command, then failed
while searching multiple unrelated NDK installations for the symbol inspector.
The completion receipt uses the Swift SDK's bundled NDK r27d to inspect the
unchanged retained library. The original failed receipt remains intact. See
`verification/android-engine-v2-c-bridge/inspection-completion/receipt.json` and
`verification/android-engine-v2-c-bridge/acceptance.json`. This is host execution
and Android compilation evidence, with no native screen execution claim.
