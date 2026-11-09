The candidate adds one SDK-owned public class, `dev.mixer.android.AndroidUINativeSurface`, with nested immutable `Frame` and `Events` types. It uses the existing Swift AndroidUIFrame contract: exact owner bytes, native packet bytes, and appearance descriptor bytes. It never decodes or re-encodes those values.

```java
AndroidUINativeSurface surface = new AndroidUINativeSurface(activity, root,
    AndroidUIProfile.MEASURED_MULTILINE_RETIREMENT_V3,
    (owner, envelope) -> enqueue(owner, envelope));
surface.activate(ownerBytes);
surface.install(new AndroidUINativeSurface.Frame(ownerBytes, packet, appearance));
surface.onResume(); // Activity lifecycle forwards to the real owner
surface.onPause();
surface.onStop();
surface.revoke(ownerBytes); // same-owner repeat is harmless
surface.close();           // terminal; allocate a new facade for a new lifetime
```

All methods require the Android main thread. Only V3 is accepted, explicitly; API level never selects a profile. Activation rejects a second owner. Installation returns only after the existing native owner's synchronous validation and attachment. Events carry copies of the original owner and immutable envelope into an app queue. No public engine owner, lifecycle core, coordinator, observer, renderer, or cleanup ledger is exposed. `gateInput()` gates commands in flight; `isCurrent()` reports whether the existing native presentation is current. Close retains its native owner and any cleanup uncertainty; it does not retry cleanup automatically.

FieldLog's app JNI methods and Activity move to `dev.fieldlog.android`. The app transports native event bytes as base64 inside its own platform-JSON command, and Swift decodes the original bytes directly as UIEventEnvelope. The Swift public protocol, capabilities, profile and engine C ABI remain unchanged. Root reviews this contract after the implementation/build; native runtime acceptance remains pending.

Frame construction checks owner 1–64 bytes, packet 1–1,048,576 bytes and appearance 1–65,536 bytes before cloning any arrays. The existing native codecs remain authoritative for all content validation.
